"""Unit tests for FR-73 Quick Analysis (one-shot prompt) — PRD v0.7.

Self-contained (own in-memory repository) so the suite stays isolated
from the shared product-service fixtures.
"""

import pytest

from graph_analytics_ai.product import (
    ProductService,
    RequirementVersionStatus,
    WorkflowMode,
    WorkflowRunStatus,
    create_graph_profile,
)
from graph_analytics_ai.product.exceptions import ValidationError


class _Repo:
    """Minimal in-memory ProductRepository for quick_analysis tests."""

    def __init__(self):
        self.workspaces = {}
        self.graph_profiles = {}
        self.requirement_versions = []
        self.workflow_runs = {}
        self.audit_events = []

    # workspaces
    def create_workspace(self, workspace):
        self.workspaces[workspace.workspace_id] = workspace
        return workspace.workspace_id

    def get_workspace(self, workspace_id):
        return self.workspaces[workspace_id]

    def update_workspace(self, workspace):
        self.workspaces[workspace.workspace_id] = workspace
        return workspace.workspace_id

    # graph profiles
    def create_graph_profile(self, profile):
        self.graph_profiles[profile.graph_profile_id] = profile
        return profile.graph_profile_id

    def get_graph_profile(self, graph_profile_id):
        return self.graph_profiles[graph_profile_id]

    # requirement versions
    def list_requirement_versions(self, workspace_id):
        return [
            v for v in self.requirement_versions if v.workspace_id == workspace_id
        ]

    def create_requirement_version(self, version):
        self.requirement_versions.append(version)
        return version.requirement_version_id

    # workflow runs
    def create_workflow_run(self, run):
        self.workflow_runs[run.run_id] = run
        return run.run_id

    def get_workflow_run(self, run_id):
        return self.workflow_runs[run_id]

    def update_workflow_run(self, run):
        self.workflow_runs[run.run_id] = run
        return run.run_id

    # audit
    def create_audit_event(self, event):
        self.audit_events.append(event)
        return event

    # listing surfaces used by get_workspace_overview
    def list_connection_profiles(self, workspace_id):
        return []

    def list_graph_profiles(self, workspace_id):
        return [p for p in self.graph_profiles.values() if p.workspace_id == workspace_id]

    def list_source_documents(self, workspace_id):
        return []

    def list_workflow_runs(self, workspace_id):
        return [r for r in self.workflow_runs.values() if r.workspace_id == workspace_id]

    def list_report_manifests(self, workspace_id):
        return []

    def list_audit_events(self, workspace_id, limit=None):
        events = [e for e in self.audit_events if e.workspace_id == workspace_id]
        return events[:limit] if limit else events


def _service_with_profile():
    repo = _Repo()
    service = ProductService(repo)
    workspace = service.create_workspace(
        customer_name="Acme", project_name="Fin", environment="dev"
    )
    profile = create_graph_profile(
        workspace_id=workspace.workspace_id,
        connection_profile_id="connection-test",
        graph_name="FinReflectKG",
        vertex_collections=["Node"],
        edge_collections=["relations"],
    )
    repo.create_graph_profile(profile)
    repo.audit_events.clear()
    return service, repo, workspace, profile


def test_quick_analysis_creates_ephemeral_requirement_and_starts_run():
    service, repo, workspace, profile = _service_with_profile()

    run = service.quick_analysis(
        workspace_id=workspace.workspace_id,
        graph_profile_id=profile.graph_profile_id,
        prompt="Find the most influential organizations",
        actor="analyst@example.com",
    )

    assert run.workflow_mode == WorkflowMode.AGENTIC
    assert run.status == WorkflowRunStatus.RUNNING
    assert len(run.steps) == 6  # canonical agentic layout
    assert run.graph_profile_id == profile.graph_profile_id
    assert run.requirement_version_id is not None
    assert run.metadata.get("origin") == "quick_prompt"
    assert run.metadata.get("ephemeral") is True

    assert len(repo.requirement_versions) == 1
    rv = repo.requirement_versions[0]
    assert rv.status == RequirementVersionStatus.APPROVED
    assert rv.metadata.get("ephemeral") is True
    assert rv.metadata.get("origin") == "quick_prompt"
    assert rv.metadata.get("draft_brd") == "Find the most influential organizations"

    actions = {e.action for e in repo.audit_events}
    assert "quick_analysis" in actions
    assert "start_workflow_run" in actions


def test_quick_analysis_rejects_empty_prompt():
    service, _repo, workspace, profile = _service_with_profile()
    with pytest.raises(ValidationError):
        service.quick_analysis(
            workspace_id=workspace.workspace_id,
            graph_profile_id=profile.graph_profile_id,
            prompt="   ",
        )


def test_quick_analysis_rejects_graph_profile_from_other_workspace():
    service, repo, workspace, _profile = _service_with_profile()
    other_ws = service.create_workspace(
        customer_name="Other", project_name="P", environment="dev"
    )
    other_profile = create_graph_profile(
        workspace_id=other_ws.workspace_id,
        connection_profile_id="c2",
        graph_name="G2",
    )
    repo.create_graph_profile(other_profile)

    with pytest.raises(ValidationError):
        service.quick_analysis(
            workspace_id=workspace.workspace_id,
            graph_profile_id=other_profile.graph_profile_id,
            prompt="anything",
        )


def test_quick_analysis_rejects_unknown_workflow_mode():
    service, _repo, workspace, profile = _service_with_profile()
    with pytest.raises(ValidationError):
        service.quick_analysis(
            workspace_id=workspace.workspace_id,
            graph_profile_id=profile.graph_profile_id,
            prompt="hi",
            workflow_mode="traditional",
        )


def test_quick_analysis_version_excluded_from_curated_overview():
    """The ephemeral quick-analysis requirement version must not appear in
    the consolidated Requirements asset list / version dropdown (FR-73)."""

    service, _repo, workspace, profile = _service_with_profile()
    service.quick_analysis(
        workspace_id=workspace.workspace_id,
        graph_profile_id=profile.graph_profile_id,
        prompt="one-shot prompt",
    )

    overview = service.get_workspace_overview(workspace.workspace_id)
    assert overview.latest_requirement_versions == []
    assert overview.counts["requirement_versions"] == 0
