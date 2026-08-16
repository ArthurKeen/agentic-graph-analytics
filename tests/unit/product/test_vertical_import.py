"""Tests for vertical project bundle import (PRD FR-49 / FR-50).

No concrete source format exists for either requirement, so the product
defines one documented bundle (docs/vertical_project_bundle.md) with a
`vertical` discriminator. These tests pin that contract — especially the
safety property both requirements share: importing must not execute code.
"""

import pytest

from graph_analytics_ai.product import ProductService, create_workspace
from graph_analytics_ai.product.exceptions import ValidationError
from graph_analytics_ai.product.models import AnalysisTemplateStatus, UseCaseStatus

from test_service import FakeProductRepository


ADTECH_BUNDLE = """
vertical: adtech
name: Audience Planning
use_cases:
  - title: Rank audiences by influence
    type: centrality
    priority: high
    description: Find the most influential audience segments.
    algorithms: [pagerank]
templates:
  - name: PageRank on Audience
    algorithm: pagerank
    parameters:
      damping_factor: 0.85
    config:
      graph_name: adtech_graph
    use_case: Rank audiences by influence
"""

CLINICAL_BUNDLE = """
vertical: clinical_trials
name: Site Enrollment
use_cases:
  - title: Cluster trial sites
    type: community
    priority: critical
templates:
  - name: WCC on Sites
    algorithm: wcc
    use_case: Cluster trial sites
"""


def _workspace(repository):
    workspace = create_workspace(
        customer_name="C", project_name="P", environment="dev"
    )
    repository.workspaces[workspace.workspace_id] = workspace
    return workspace


def test_adtech_bundle_imports_linked_use_cases_and_templates():
    repository = FakeProductRepository()
    workspace = _workspace(repository)

    result = ProductService(repository).import_vertical_project(
        workspace.workspace_id, ADTECH_BUNDLE, actor="analyst@example.com"
    )

    assert result["vertical"] == "adtech"
    assert result["counts"] == {"use_cases": 1, "templates": 1}
    assert result["warnings"] == []

    use_case = repository.use_cases[0]
    template = repository.analysis_templates[0]
    # Templates resolve their use case by title.
    assert template.use_case_id == use_case.use_case_id
    # Importing is not approving.
    assert use_case.status is UseCaseStatus.DRAFT
    assert template.status is AnalysisTemplateStatus.DRAFT
    # Imported rows are attributed to generation, not hand-authoring.
    assert use_case.origin.value == "generated"
    assert any(
        event.action == "import_vertical_project" for event in repository.audit_events
    )


def test_the_same_format_serves_the_clinical_and_osint_verticals():
    """FR-49 and FR-50 differ in vocabulary, not structure."""

    repository = FakeProductRepository()
    workspace = _workspace(repository)

    result = ProductService(repository).import_vertical_project(
        workspace.workspace_id, CLINICAL_BUNDLE
    )

    assert result["vertical"] == "clinical_trials"
    assert result["counts"] == {"use_cases": 1, "templates": 1}


def test_json_bundles_parse_with_the_same_reader():
    repository = FakeProductRepository()
    workspace = _workspace(repository)
    document = (
        '{"vertical": "osint", "use_cases": '
        '[{"title": "Trace source networks", "type": "pathfinding"}]}'
    )

    result = ProductService(repository).import_vertical_project(
        workspace.workspace_id, document, document_format="json"
    )

    assert result["vertical"] == "osint"
    assert result["counts"]["use_cases"] == 1


def test_yaml_python_object_tags_are_rejected_not_executed():
    """The safety property FR-49/FR-50 share with FR-26.

    yaml.safe_load refuses !!python/... tags. With the default loader this
    payload would construct and CALL os.system.
    """

    repository = FakeProductRepository()
    workspace = _workspace(repository)
    hostile = """
vertical: adtech
use_cases:
  - title: !!python/object/apply:os.system ["echo pwned"]
    type: centrality
"""

    with pytest.raises(ValidationError) as exc_info:
        ProductService(repository).import_vertical_project(
            workspace.workspace_id, hostile
        )

    assert "parse" in str(exc_info.value).lower()
    # Nothing was created from the hostile bundle.
    assert repository.use_cases == []


def test_unknown_enum_values_degrade_with_a_warning_rather_than_failing():
    repository = FakeProductRepository()
    workspace = _workspace(repository)
    document = """
vertical: adtech
use_cases:
  - title: Something novel
    type: telepathy
    priority: extremely-urgent
"""

    result = ProductService(repository).import_vertical_project(
        workspace.workspace_id, document
    )

    use_case = repository.use_cases[0]
    assert use_case.use_case_type == "pattern"
    assert use_case.priority == "medium"
    # Degradation is reported, never silent.
    assert any("telepathy" in warning for warning in result["warnings"])
    assert any("extremely-urgent" in warning for warning in result["warnings"])


def test_unresolvable_use_case_reference_imports_the_template_unlinked():
    repository = FakeProductRepository()
    workspace = _workspace(repository)
    document = """
vertical: adtech
templates:
  - name: Orphan template
    algorithm: pagerank
    use_case: A use case that is not in this bundle
"""

    result = ProductService(repository).import_vertical_project(
        workspace.workspace_id, document
    )

    assert result["counts"]["templates"] == 1
    assert repository.analysis_templates[0].use_case_id is None
    assert any("unknown use case" in warning for warning in result["warnings"])


def test_malformed_and_empty_bundles_are_rejected():
    repository = FakeProductRepository()
    workspace = _workspace(repository)
    service = ProductService(repository)

    with pytest.raises(ValidationError):
        service.import_vertical_project(workspace.workspace_id, "just a string")
    with pytest.raises(ValidationError):
        service.import_vertical_project(workspace.workspace_id, "vertical: adtech")
    with pytest.raises(ValidationError):
        service.import_vertical_project(
            workspace.workspace_id, ADTECH_BUNDLE, document_format="toml"
        )
