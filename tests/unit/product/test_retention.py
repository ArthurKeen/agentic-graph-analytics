"""Unit tests for retention policy configuration and sweep (PRD FR-54).

FR-54 says only "admins can configure retention" without defining the
mechanism. These tests pin the design chosen here: an explicit per-workspace
policy plus an on-demand sweep that is DRY RUN BY DEFAULT and that never
deletes compliance artifacts (approved requirement versions, published report
snapshots, runs behind a published report).
"""

from datetime import timedelta

import pytest

from graph_analytics_ai.product import (
    ProductService,
    ReportStatus,
    RequirementVersionStatus,
    WorkflowMode,
    create_report_manifest,
    create_requirement_version,
    create_source_document,
    create_workflow_run,
    create_workspace,
)
from graph_analytics_ai.product.exceptions import ValidationError
from graph_analytics_ai.product.models import DocumentStorageMode, current_timestamp

from test_service import FakeProductRepository


class _RetentionRepository(FakeProductRepository):
    """Adds retention CRUD plus the delete hook the sweep uses."""

    def __init__(self):
        super().__init__()
        self._policy = None
        self.deleted = []

    def get_retention_policy(self, workspace_id):
        return self._policy

    def create_retention_policy(self, policy):
        self._policy = policy
        return policy.retention_policy_id

    def update_retention_policy(self, policy):
        self._policy = policy
        return policy.retention_policy_id

    def list_report_manifests(self, workspace_id):
        return [r for r in self.reports.values() if r.workspace_id == workspace_id]

    def list_workflow_runs(self, workspace_id):
        return [
            r for r in self.workflow_runs.values() if r.workspace_id == workspace_id
        ]

    def list_audit_events(self, workspace_id, limit=100):
        return self.audit_events[:limit]

    def delete_document_by_key(self, collection_name, key):
        self.deleted.append((collection_name, key))
        return True


def _aged(days: int):
    return current_timestamp() - timedelta(days=days)


def _workspace(repository):
    workspace = create_workspace(customer_name="C", project_name="P", environment="dev")
    repository.workspaces[workspace.workspace_id] = workspace
    return workspace


def test_unset_policy_reports_keep_everything():
    repository = _RetentionRepository()
    workspace = _workspace(repository)

    policy = ProductService(repository).get_retention_policy(workspace.workspace_id)

    assert policy["configured"] is False
    assert policy["enabled"] is False
    assert policy["run_retention_days"] == 0


def test_set_retention_policy_is_audited_and_rejects_negative_windows():
    repository = _RetentionRepository()
    workspace = _workspace(repository)
    service = ProductService(repository)

    saved = service.set_retention_policy(
        workspace.workspace_id,
        enabled=True,
        run_retention_days=30,
        actor="admin@example.com",
    )

    assert saved["enabled"] is True
    assert saved["run_retention_days"] == 30
    assert any(e.action == "set_retention_policy" for e in repository.audit_events)

    with pytest.raises(ValidationError):
        service.set_retention_policy(workspace.workspace_id, run_retention_days=-1)


def test_sweep_is_dry_run_by_default_and_deletes_nothing():
    """Deleting data must be an explicit choice, never a default."""

    repository = _RetentionRepository()
    workspace = _workspace(repository)
    service = ProductService(repository)
    service.set_retention_policy(
        workspace.workspace_id, enabled=True, run_retention_days=7
    )

    run = create_workflow_run(
        workspace_id=workspace.workspace_id, workflow_mode=WorkflowMode.AGENTIC
    )
    run.created_at = _aged(30)
    repository.workflow_runs[run.run_id] = run

    result = service.apply_retention_policy(workspace.workspace_id)

    assert result["deleted"] is False
    assert result["counts"]["runs"] == 1
    assert repository.deleted == []


def test_sweep_deletes_only_when_explicitly_asked():
    repository = _RetentionRepository()
    workspace = _workspace(repository)
    service = ProductService(repository)
    service.set_retention_policy(
        workspace.workspace_id, enabled=True, run_retention_days=7
    )

    run = create_workflow_run(
        workspace_id=workspace.workspace_id, workflow_mode=WorkflowMode.AGENTIC
    )
    run.created_at = _aged(30)
    repository.workflow_runs[run.run_id] = run

    result = service.apply_retention_policy(workspace.workspace_id, dry_run=False)

    assert result["deleted"] is True
    assert result["removed"] == 1
    assert repository.deleted == [("aga_workflow_runs", run.run_id)]
    assert any(e.action == "apply_retention_policy" for e in repository.audit_events)


def test_disabled_policy_sweeps_nothing():
    repository = _RetentionRepository()
    workspace = _workspace(repository)
    service = ProductService(repository)
    service.set_retention_policy(
        workspace.workspace_id, enabled=False, run_retention_days=1
    )
    run = create_workflow_run(
        workspace_id=workspace.workspace_id, workflow_mode=WorkflowMode.AGENTIC
    )
    run.created_at = _aged(365)
    repository.workflow_runs[run.run_id] = run

    result = service.apply_retention_policy(workspace.workspace_id, dry_run=False)

    assert result["counts"] == {} or result["counts"].get("runs", 0) == 0
    assert repository.deleted == []
    assert "disabled" in result["reason"].lower()


def test_approved_requirement_versions_are_never_swept():
    """Compliance artifacts survive retention regardless of age."""

    repository = _RetentionRepository()
    workspace = _workspace(repository)
    service = ProductService(repository)
    service.set_retention_policy(
        workspace.workspace_id, enabled=True, draft_retention_days=1
    )

    approved = create_requirement_version(
        workspace_id=workspace.workspace_id,
        version=1,
        status=RequirementVersionStatus.APPROVED,
    )
    approved.created_at = _aged(999)
    draft = create_requirement_version(
        workspace_id=workspace.workspace_id,
        version=2,
        status=RequirementVersionStatus.DRAFT,
    )
    draft.created_at = _aged(999)
    repository.requirement_versions.extend([approved, draft])

    result = service.apply_retention_policy(workspace.workspace_id)

    swept = {item["id"] for item in result["candidates"]["drafts"]}
    assert draft.requirement_version_id in swept
    assert approved.requirement_version_id not in swept


def test_published_reports_and_their_runs_are_protected():
    repository = _RetentionRepository()
    workspace = _workspace(repository)
    service = ProductService(repository)
    service.set_retention_policy(
        workspace.workspace_id,
        enabled=True,
        run_retention_days=1,
        report_snapshot_retention_days=1,
    )

    run = create_workflow_run(
        workspace_id=workspace.workspace_id, workflow_mode=WorkflowMode.AGENTIC
    )
    run.created_at = _aged(999)
    repository.workflow_runs[run.run_id] = run

    published = create_report_manifest(
        workspace_id=workspace.workspace_id,
        run_id=run.run_id,
        title="Published",
        status=ReportStatus.PUBLISHED,
        published_snapshot_id="snapshot-1",
    )
    published.created_at = _aged(999)
    repository.reports[published.report_id] = published

    result = service.apply_retention_policy(workspace.workspace_id)

    assert result["counts"]["runs"] == 0
    assert result["counts"]["report_snapshots"] == 0
    assert run.run_id in result["protected"]["runs_with_published_reports"]


def test_audit_logs_are_only_swept_when_a_window_is_set_explicitly():
    """Audit events are the record of everything else being deleted."""

    repository = _RetentionRepository()
    workspace = _workspace(repository)
    service = ProductService(repository)
    # Every other window set, audit deliberately left at 0.
    service.set_retention_policy(
        workspace.workspace_id,
        enabled=True,
        draft_retention_days=1,
        run_retention_days=1,
        document_retention_days=1,
        report_snapshot_retention_days=1,
    )
    for event in repository.audit_events:
        event.timestamp = _aged(999)

    result = service.apply_retention_policy(workspace.workspace_id)

    assert result["counts"]["audit_logs"] == 0


def test_ephemeral_quick_analysis_runs_are_swept_under_the_run_window():
    """The one concrete retention behaviour the PRD names."""

    repository = _RetentionRepository()
    workspace = _workspace(repository)
    service = ProductService(repository)
    service.set_retention_policy(
        workspace.workspace_id, enabled=True, run_retention_days=7
    )

    run = create_workflow_run(
        workspace_id=workspace.workspace_id,
        workflow_mode=WorkflowMode.AGENTIC,
        metadata={"ephemeral": True, "origin": "quick_prompt"},
    )
    run.created_at = _aged(30)
    repository.workflow_runs[run.run_id] = run

    result = service.apply_retention_policy(workspace.workspace_id)

    assert result["counts"]["runs"] == 1
    assert result["candidates"]["runs"][0]["ephemeral"] is True


def test_records_inside_the_window_are_kept():
    repository = _RetentionRepository()
    workspace = _workspace(repository)
    service = ProductService(repository)
    service.set_retention_policy(
        workspace.workspace_id, enabled=True, document_retention_days=30
    )

    document = create_source_document(
        workspace_id=workspace.workspace_id,
        filename="recent.md",
        mime_type="text/markdown",
        sha256="abc",
        storage_mode=DocumentStorageMode.EXTRACT_ONLY,
    )
    document.uploaded_at = _aged(5)
    repository.source_documents.append(document)

    result = service.apply_retention_policy(workspace.workspace_id)

    assert result["counts"]["documents"] == 0
