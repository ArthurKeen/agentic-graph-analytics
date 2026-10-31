"""Unit tests for FR-75 autonomous analysis.

Reuses the self-contained repository from the Quick Analysis suite: the two
entry points differ only in where the brief comes from, so testing them
against the same fake keeps that difference visible.
"""

import pytest

from graph_analytics_ai.product import (
    ProductService,
    RequirementVersionStatus,
    WorkflowMode,
    create_graph_profile,
)
from graph_analytics_ai.product.exceptions import ValidationError

from test_quick_analysis import _Repo


def _service_with_profile(**profile_kwargs):
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
        **profile_kwargs,
    )
    repo.create_graph_profile(profile)
    repo.audit_events.clear()
    return service, repo, workspace, profile


def test_a_graph_profile_is_the_whole_input():
    """No prompt, no interview, no approval. That is the feature."""

    service, repo, workspace, profile = _service_with_profile()

    run = service.autonomous_analysis(
        workspace_id=workspace.workspace_id,
        graph_profile_id=profile.graph_profile_id,
    )

    assert run.workflow_mode is WorkflowMode.AGENTIC
    assert run.graph_profile_id == profile.graph_profile_id
    assert len(repo.requirement_versions) == 1


def test_the_run_asks_the_pipeline_to_plan_its_own_use_cases():
    """discovery_mode is what the supervisor reads to turn on planning. With
    it absent the run would quietly behave like an ordinary agentic run."""

    service, repo, workspace, profile = _service_with_profile()

    run = service.autonomous_analysis(
        workspace_id=workspace.workspace_id,
        graph_profile_id=profile.graph_profile_id,
    )

    assert run.metadata["discovery_mode"] is True
    assert run.metadata["origin"] == "autonomous"


def test_the_brief_names_the_actual_graph():
    """With no documents the Requirements agent falls back to 'General graph
    analytics requirements', and every use case inherits that vagueness."""

    service, repo, workspace, profile = _service_with_profile(
        conceptual_schema={
            "entities": [{"name": "Organization"}, {"name": "Metric"}],
            "relationships": [
                {"type": "reports", "fromEntity": "Organization", "toEntity": "Metric"}
            ],
        }
    )

    service.autonomous_analysis(
        workspace_id=workspace.workspace_id,
        graph_profile_id=profile.graph_profile_id,
    )

    brief = repo.requirement_versions[0].metadata["draft_brd"]
    assert "FinReflectKG" in brief
    assert "Organization" in brief
    assert "reports" in brief
    assert (
        "no business requirements" in brief.lower()
    ), "the brief must say the context is absent rather than invent one"


def test_the_requirement_version_is_ephemeral_and_approved():
    """Approved so nothing blocks on review; ephemeral so unattended runs do
    not accumulate in the curated Requirements list (FR-17)."""

    service, repo, workspace, profile = _service_with_profile()

    service.autonomous_analysis(
        workspace_id=workspace.workspace_id,
        graph_profile_id=profile.graph_profile_id,
    )

    version = repo.requirement_versions[0]
    assert version.status is RequirementVersionStatus.APPROVED
    assert version.metadata["ephemeral"] is True
    assert version.metadata["origin"] == "autonomous"


def test_a_graph_profile_from_another_workspace_is_refused():
    service, repo, workspace, profile = _service_with_profile()
    other = service.create_workspace(
        customer_name="Other", project_name="Other", environment="dev"
    )

    with pytest.raises(ValidationError):
        service.autonomous_analysis(
            workspace_id=other.workspace_id,
            graph_profile_id=profile.graph_profile_id,
        )


@pytest.mark.parametrize("mode", ["traditional", "nonsense"])
def test_only_agentic_modes_are_accepted(mode):
    """An autonomous run has no requirements to walk through sequentially."""

    service, repo, workspace, profile = _service_with_profile()

    with pytest.raises(ValidationError):
        service.autonomous_analysis(
            workspace_id=workspace.workspace_id,
            graph_profile_id=profile.graph_profile_id,
            workflow_mode=mode,
        )


def test_the_run_is_audited():
    service, repo, workspace, profile = _service_with_profile()

    service.autonomous_analysis(
        workspace_id=workspace.workspace_id,
        graph_profile_id=profile.graph_profile_id,
    )

    actions = [event.action for event in repo.audit_events]
    assert "autonomous_analysis" in actions
