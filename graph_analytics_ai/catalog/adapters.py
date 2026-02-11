"""
Adapters to convert workflow model types to catalog model types.

The agentic workflow produces types from ai.documents, ai.generation, and ai.templates.
The catalog storage expects types from catalog.models. These adapters bridge the gap.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from .models import (
    ExtractedRequirements as CatalogExtractedRequirements,
    GeneratedUseCase,
    AnalysisTemplate as CatalogAnalysisTemplate,
    GraphConfig,
    generate_requirements_id,
    generate_use_case_id,
    generate_template_id,
)

logger = logging.getLogger(__name__)


def _is_workflow_requirements(obj: Any) -> bool:
    """Check if object is from ai.documents.models.ExtractedRequirements."""
    return (
        hasattr(obj, "documents")
        and hasattr(obj, "objectives")
        and not hasattr(obj, "to_dict")
    )


def _is_workflow_use_case(obj: Any) -> bool:
    """Check if object is from ai.generation.models.UseCase."""
    return (
        hasattr(obj, "graph_algorithms")
        and hasattr(obj, "use_case_type")
        and not hasattr(obj, "to_dict")
    )


def _is_workflow_template(obj: Any) -> bool:
    """Check if object is from ai.templates.models.AnalysisTemplate."""
    return (
        hasattr(obj, "config")
        and hasattr(obj, "algorithm")
        and hasattr(obj, "name")
        and not hasattr(obj, "template_id")
    )


def adapt_requirements(
    requirements: Any, requirements_id: Optional[str] = None
) -> CatalogExtractedRequirements:
    """
    Convert workflow ExtractedRequirements to catalog ExtractedRequirements.

    Args:
        requirements: From ai.documents.models.ExtractedRequirements
        requirements_id: Optional pre-generated ID

    Returns:
        catalog.models.ExtractedRequirements
    """
    if not _is_workflow_requirements(requirements):
        return requirements  # Already catalog type

    req_id = requirements_id or generate_requirements_id()
    source_docs = []
    for d in getattr(requirements, "documents", []):
        if hasattr(d, "metadata") and d.metadata and hasattr(d.metadata, "file_path"):
            source_docs.append(d.metadata.file_path)
        elif hasattr(d, "file_path"):
            source_docs.append(d.file_path)
        else:
            source_docs.append(str(d))

    objectives = []
    for obj in getattr(requirements, "objectives", []):
        objectives.append(
            {
                "id": getattr(obj, "id", ""),
                "title": getattr(obj, "title", ""),
                "description": getattr(obj, "description", ""),
                "priority": getattr(obj.priority, "value", "unknown")
                if hasattr(obj, "priority")
                else "unknown",
                "success_criteria": getattr(obj, "success_criteria", []),
            }
        )

    reqs = []
    for r in getattr(requirements, "requirements", []):
        reqs.append(
            {
                "id": getattr(r, "id", ""),
                "text": getattr(r, "text", ""),
                "type": getattr(r.requirement_type, "value", "unknown")
                if hasattr(r, "requirement_type")
                else "unknown",
                "priority": getattr(r.priority, "value", "unknown")
                if hasattr(r, "priority")
                else "unknown",
            }
        )

    return CatalogExtractedRequirements(
        requirements_id=req_id,
        timestamp=datetime.now(timezone.utc),
        source_documents=source_docs or ["unknown"],
        domain=requirements.domain or "unknown",
        summary=requirements.summary or "",
        objectives=objectives,
        requirements=reqs,
        constraints=getattr(requirements, "constraints", []) or [],
        epoch_id=None,
        metadata={},
    )


def adapt_use_case(
    use_case: Any,
    requirements_id: Optional[str] = None,
    use_case_id: Optional[str] = None,
) -> GeneratedUseCase:
    """
    Convert workflow UseCase to catalog GeneratedUseCase.

    Args:
        use_case: From ai.generation.models.UseCase
        requirements_id: Optional ID of parent requirements
        use_case_id: Optional pre-generated ID

    Returns:
        catalog.models.GeneratedUseCase
    """
    if not _is_workflow_use_case(use_case):
        return use_case  # Already catalog type

    uc_id = use_case_id or getattr(use_case, "id", None) or generate_use_case_id()
    algorithm = "unknown"
    if hasattr(use_case, "graph_algorithms") and use_case.graph_algorithms:
        algorithm = use_case.graph_algorithms[0]

    return GeneratedUseCase(
        use_case_id=uc_id,
        requirements_id=requirements_id or "",
        timestamp=datetime.now(timezone.utc),
        title=getattr(use_case, "title", ""),
        description=getattr(use_case, "description", ""),
        algorithm=algorithm,
        business_value=getattr(use_case, "expected_outputs", [""])[0]
        if getattr(use_case, "expected_outputs", [])
        else "",
        priority=getattr(use_case.priority, "value", "medium")
        if hasattr(use_case, "priority")
        else "medium",
        addresses_objectives=[],
        addresses_requirements=getattr(use_case, "related_requirements", []) or [],
        epoch_id=None,
        metadata={},
    )


def adapt_template(
    template: Any,
    use_case_id: Optional[str] = None,
    requirements_id: Optional[str] = None,
    template_id: Optional[str] = None,
) -> CatalogAnalysisTemplate:
    """
    Convert workflow AnalysisTemplate to catalog AnalysisTemplate.

    Args:
        template: From ai.templates.models.AnalysisTemplate
        use_case_id: Optional ID of parent use case
        requirements_id: Optional ID of requirements
        template_id: Optional pre-generated ID

    Returns:
        catalog.models.AnalysisTemplate
    """
    if not _is_workflow_template(template):
        return template  # Already catalog type

    tpl_id = template_id or generate_template_id()
    uc_id = use_case_id or getattr(template, "use_case_id", None) or ""

    # Build GraphConfig from template.config
    config = getattr(template, "config", None)
    if config:
        graph_config = GraphConfig(
            graph_name=getattr(config, "graph_name", "unknown"),
            graph_type="named_graph",
            vertex_collections=getattr(config, "vertex_collections", []) or [],
            edge_collections=getattr(config, "edge_collections", []) or [],
            vertex_count=0,
            edge_count=0,
        )
    else:
        graph_config = GraphConfig(
            graph_name="unknown",
            graph_type="named_graph",
            vertex_collections=[],
            edge_collections=[],
            vertex_count=0,
            edge_count=0,
        )

    algorithm = "unknown"
    params = {}
    if hasattr(template, "algorithm"):
        algo_obj = template.algorithm
        algorithm = getattr(algo_obj.algorithm, "value", str(algo_obj)) if hasattr(algo_obj, "algorithm") else str(algo_obj)
        params = getattr(algo_obj, "parameters", {}) or {}

    return CatalogAnalysisTemplate(
        template_id=tpl_id,
        use_case_id=uc_id,
        requirements_id=requirements_id or "",
        timestamp=datetime.now(timezone.utc),
        name=getattr(template, "name", "unknown"),
        algorithm=algorithm,
        parameters=params,
        graph_config=graph_config,
        epoch_id=None,
        metadata=getattr(template, "metadata", {}) or {},
    )
