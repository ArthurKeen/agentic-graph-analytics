"""
Requirements extractor using LLM to analyze business documents.

This module processes parsed documents and uses LLM to extract:
- Business requirements
- Stakeholders
- Objectives
- Constraints and risks
"""

from typing import List, Optional, Dict, Any

from ..llm import LLMProvider, get_default_provider
from .models import (
    Document,
    ExtractedRequirements,
    Requirement,
    RequirementType,
    Stakeholder,
    Objective,
    Priority,
)


# LLM prompt for requirements extraction with few-shot examples
REQUIREMENTS_EXTRACTION_PROMPT = """You are a business analyst expert at extracting requirements from documents.

# Example Extraction 1: E-commerce Platform

Input Document:
"We need to improve customer retention for our online marketplace. The marketing team wants to identify our most influential customers to create a VIP program. The platform currently has 50,000 active users and 200,000 products. We need to complete this analysis within Q1 2024 with a budget of $50K. The CEO wants to see a 20% increase in repeat purchases within 6 months."

Expected Output:
{{
  "summary": "E-commerce platform seeking to improve customer retention through VIP program targeting influential customers. Analysis must complete in Q1 2024 with goal of 20% increase in repeat purchases.",
  "domain": "e-commerce",
  "requirements": [
    {{
      "id": "REQ-001",
      "text": "Identify most influential customers in the platform",
      "type": "functional",
      "priority": "critical",
      "stakeholders": ["Marketing Team", "CEO"]
    }},
    {{
      "id": "REQ-002",
      "text": "Create VIP customer program based on influence analysis",
      "type": "business",
      "priority": "high",
      "stakeholders": ["Marketing Team"]
    }},
    {{
      "id": "REQ-003",
      "text": "Analyze 50,000 active users and 200,000 products",
      "type": "technical",
      "priority": "high",
      "stakeholders": ["Data Team"]
    }}
  ],
  "stakeholders": [
    {{
      "name": "Marketing Team",
      "role": "Department",
      "organization": "Marketing",
      "interests": ["customer retention", "VIP program creation", "identifying influencers"]
    }},
    {{
      "name": "CEO",
      "role": "Executive",
      "organization": "Executive Leadership",
      "interests": ["business growth", "repeat purchase rate", "ROI"]
    }}
  ],
  "objectives": [
    {{
      "id": "OBJ-001",
      "title": "Improve Customer Retention",
      "description": "Increase repeat purchases by identifying and engaging influential customers",
      "priority": "critical",
      "success_criteria": ["20% increase in repeat purchases within 6 months", "VIP program launched in Q1 2024"],
      "related_requirements": ["REQ-001", "REQ-002"]
    }}
  ],
  "constraints": ["Budget: $50K", "Timeline: Q1 2024", "Platform scale: 50K users, 200K products"],
  "assumptions": ["Current customer data is complete and accurate", "Influential customers will respond positively to VIP treatment", "Marketing team can execute VIP program"],
  "risks": ["Timeline may be aggressive for full implementation", "Budget may be insufficient for comprehensive analysis", "VIP program may not resonate with identified influencers"]
}}

# Example Extraction 2: Healthcare Network Analysis

Input Document:
"Our hospital network needs to optimize patient referrals between specialists. We have 15 hospitals with 500 doctors across 30 specialties. The quality assurance team is concerned about referral bottlenecks causing treatment delays. CFO requires cost analysis of referral patterns. Must comply with HIPAA regulations. Goal is to reduce average referral time by 30%."

Expected Output:
{{
  "summary": "Hospital network optimization project focused on improving specialist referral efficiency across 15 hospitals and 500 doctors. Must reduce referral time by 30% while maintaining HIPAA compliance.",
  "domain": "healthcare",
  "requirements": [
    {{
      "id": "REQ-001",
      "text": "Analyze referral patterns between 500 doctors across 30 specialties",
      "type": "functional",
      "priority": "critical",
      "stakeholders": ["Quality Assurance Team"]
    }},
    {{
      "id": "REQ-002",
      "text": "Identify referral bottlenecks causing treatment delays",
      "type": "functional",
      "priority": "critical",
      "stakeholders": ["Quality Assurance Team", "Clinical Directors"]
    }},
    {{
      "id": "REQ-003",
      "text": "Provide cost analysis of referral patterns",
      "type": "business",
      "priority": "high",
      "stakeholders": ["CFO"]
    }},
    {{
      "id": "REQ-004",
      "text": "Ensure all analysis complies with HIPAA regulations",
      "type": "constraint",
      "priority": "critical",
      "stakeholders": ["Compliance Officer", "Legal Department"]
    }}
  ],
  "stakeholders": [
    {{
      "name": "Quality Assurance Team",
      "role": "Department",
      "organization": "Quality Assurance",
      "interests": ["patient care quality", "reducing treatment delays", "identifying bottlenecks"]
    }},
    {{
      "name": "CFO",
      "role": "Executive",
      "organization": "Finance",
      "interests": ["cost optimization", "resource allocation", "ROI"]
    }},
    {{
      "name": "Compliance Officer",
      "role": "Officer",
      "organization": "Legal/Compliance",
      "interests": ["HIPAA compliance", "data privacy", "regulatory adherence"]
    }}
  ],
  "objectives": [
    {{
      "id": "OBJ-001",
      "title": "Optimize Specialist Referral Efficiency",
      "description": "Reduce bottlenecks and improve referral speed across hospital network",
      "priority": "critical",
      "success_criteria": ["30% reduction in average referral time", "Identify and resolve all critical bottlenecks", "Cost savings quantified"],
      "related_requirements": ["REQ-001", "REQ-002", "REQ-003"]
    }}
  ],
  "constraints": ["HIPAA regulatory compliance required", "Network spans 15 hospitals", "500 doctors across 30 specialties"],
  "assumptions": ["Referral data is available and complete", "Doctors will cooperate with process changes", "Technical infrastructure supports analysis"],
  "risks": ["HIPAA compliance may limit data access", "Complex organizational structure may slow implementation", "Doctor resistance to workflow changes"]
}}

# Your Task

Extract structured requirements from the following document(s) following the same format and extraction depth as the examples above.

# Documents

{documents_text}

# Extraction Guidelines

- **Requirements**: Look for both explicit (stated) and implicit (inferred from context) requirements
- **Priority Classification**:
  - Critical: Must-have, blocking, regulatory
  - High: Important for success, stakeholder emphasis
  - Medium: Valuable but not essential
  - Low: Nice-to-have, future consideration
- **Stakeholder Interests**: Infer interests from their role and mentioned concerns
- **Success Criteria**: Must be measurable (percentages, counts, timeframes, costs)
- **Assumptions vs Constraints**: Assumptions are beliefs/conditions; constraints are fixed limitations

# Response Format

Respond with valid JSON matching this structure:

{{
  "summary": "Executive summary of documents",
  "domain": "identified domain",
  "requirements": [
    {{
      "id": "REQ-001",
      "text": "The requirement description",
      "type": "functional|non_functional|business|technical|constraint|objective",
      "priority": "critical|high|medium|low|unknown",
      "stakeholders": ["stakeholder names"]
    }}
  ],
  "stakeholders": [
    {{
      "name": "Stakeholder Name",
      "role": "Role or Title",
      "organization": "Organization/Department",
      "interests": ["key interest 1", "key interest 2"]
    }}
  ],
  "objectives": [
    {{
      "id": "OBJ-001",
      "title": "Objective Title",
      "description": "Detailed description",
      "priority": "critical|high|medium|low",
      "success_criteria": ["measurable criterion 1"],
      "related_requirements": ["REQ-001", "REQ-002"]
    }}
  ],
  "constraints": ["constraint 1", "constraint 2"],
  "assumptions": ["assumption 1", "assumption 2"],
  "risks": ["risk 1", "risk 2"]
}}

Respond ONLY with the JSON, no additional text.
"""


class RequirementsExtractor:
    """
    Extract structured requirements from business documents using LLM.

    Example:
        >>> from graph_analytics_ai.ai.documents import parse_documents, RequirementsExtractor
        >>> from graph_analytics_ai.ai.llm import create_llm_provider
        >>>
        >>> # Parse documents
        >>> docs = parse_documents(["requirements.pdf", "scope.docx"])
        >>>
        >>> # Extract requirements
        >>> provider = create_llm_provider()
        >>> extractor = RequirementsExtractor(provider)
        >>> extracted = extractor.extract(docs)
        >>>
        >>> print(f"Found {extracted.total_requirements} requirements")
        >>> print(f"Domain: {extracted.domain}")
        >>>
        >>> for req in extracted.critical_requirements:
        ...     print(f"- {req.id}: {req.text}")
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        max_content_length: int = 50000,
    ):
        """
        Initialize requirements extractor.

        Args:
            llm_provider: LLM provider to use. If None, uses default.
            max_content_length: Maximum content length to send to LLM.
        """
        self.llm_provider = llm_provider or get_default_provider()
        self.max_content_length = max_content_length

    def extract(self, documents: List[Document]) -> ExtractedRequirements:
        """
        Extract requirements from documents.

        Args:
            documents: List of parsed documents.

        Returns:
            ExtractedRequirements with all extracted information.

        Raises:
            LLMProviderError: If LLM extraction fails.
        """
        # Combine document content
        docs_text = self._format_documents(documents)

        # Truncate if too long
        if len(docs_text) > self.max_content_length:
            docs_text = (
                docs_text[: self.max_content_length] + "\n\n[... content truncated ...]"
            )

        # Format prompt
        prompt = REQUIREMENTS_EXTRACTION_PROMPT.format(documents_text=docs_text)

        # Extract with LLM
        try:
            result = self.llm_provider.generate_structured(
                prompt, schema=self._get_response_schema()
            )

            # Convert to domain models
            extracted = self._parse_result(result, documents)

            # Validate and add warnings
            extracted = self._validate_extraction(extracted, documents)

            return extracted

        except Exception as e:
            # Return minimal extraction on failure
            return self._create_fallback_extraction(documents, error=str(e))

    def _validate_extraction(
        self, extracted: ExtractedRequirements, documents: List[Document]
    ) -> ExtractedRequirements:
        """
        Validate extraction quality and log warnings.

        Args:
            extracted: Initial extraction from LLM
            documents: Source documents

        Returns:
            Validated extraction (may raise if critical validation fails)
        """
        import logging

        logger = logging.getLogger(__name__)

        warnings = []
        confidence = 1.0

        # Critical: Must have at least some content
        if len(extracted.requirements) == 0 and len(extracted.objectives) == 0:
            raise ValueError(
                "No requirements or objectives extracted from documents - extraction failed"
            )

        # Validate objectives
        if len(extracted.objectives) == 0:
            warnings.append("No objectives extracted - workflow may lack clear goals")
            confidence *= 0.7
        else:
            # Check for success criteria
            objectives_without_criteria = [
                obj for obj in extracted.objectives if not obj.success_criteria
            ]
            if objectives_without_criteria:
                warnings.append(
                    f"{len(objectives_without_criteria)} objectives lack success criteria"
                )
                confidence *= 0.8

        # Validate requirements
        if len(extracted.requirements) < 3:
            warnings.append(
                f"Only {len(extracted.requirements)} requirements extracted (expected >3 typically)"
            )
            confidence *= 0.8

        # Check priority distribution
        critical_count = len(
            [r for r in extracted.requirements if r.priority.value == "critical"]
        )
        if critical_count == 0:
            warnings.append(
                "No critical priority requirements - may indicate incomplete prioritization"
            )
            confidence *= 0.9

        # Validate stakeholders
        if len(extracted.stakeholders) == 0:
            warnings.append(
                "No stakeholders identified - may miss important perspectives"
            )
            confidence *= 0.9
        else:
            # Check stakeholders have interests
            stakeholders_without_interests = [
                s for s in extracted.stakeholders if not s.interests
            ]
            if stakeholders_without_interests:
                warnings.append(
                    f"{len(stakeholders_without_interests)} stakeholders lack identified interests"
                )
                confidence *= 0.9

        # Check domain
        if not extracted.domain or extracted.domain.lower() in [
            "unknown",
            "general",
            "unspecified",
        ]:
            warnings.append(
                "Domain unclear - may reduce quality of downstream analysis"
            )
            confidence *= 0.7

        # Check summary quality
        if not extracted.summary or len(extracted.summary) < 30:
            warnings.append("Summary too brief or missing")
            confidence *= 0.8

        # Check if truncation occurred
        total_words = sum(doc.word_count for doc in documents)
        if (
            total_words > self.max_content_length / 5
        ):  # Rough estimate (5 chars per word)
            warnings.append(
                f"Documents were truncated ({total_words} words) - extraction may be incomplete"
            )
            confidence *= 0.85

        if warnings:
            logger.warning(
                f"Requirements extraction validation issues (confidence: {confidence:.2f}): {'; '.join(warnings)}"
            )

        return extracted

    def _format_documents(self, documents: List[Document]) -> str:
        """Format documents for LLM prompt."""
        formatted = []

        for i, doc in enumerate(documents, 1):
            formatted.append(f"## Document {i}: {doc.metadata.file_name}")
            formatted.append(f"Type: {doc.metadata.document_type.value}")
            formatted.append(f"Size: {doc.word_count} words")
            formatted.append("")
            formatted.append(doc.content)
            formatted.append("")
            formatted.append("---")
            formatted.append("")

        formatted_text = "\n".join(formatted)

        # Truncate to respect max_content_length (used in tests and runtime)
        if len(formatted_text) > self.max_content_length:
            formatted_text = (
                formatted_text[: self.max_content_length]
                + "\n\n[... content truncated ...]"
            )

        return formatted_text

    def _get_response_schema(self) -> Dict[str, Any]:
        """Get JSON schema for LLM response."""
        return {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "domain": {"type": "string"},
                "requirements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "text": {"type": "string"},
                            "type": {"type": "string"},
                            "priority": {"type": "string"},
                            "stakeholders": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                },
                "stakeholders": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "role": {"type": "string"},
                            "organization": {"type": "string"},
                            "interests": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
                "objectives": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "priority": {"type": "string"},
                            "success_criteria": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "related_requirements": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                },
                "constraints": {"type": "array", "items": {"type": "string"}},
                "assumptions": {"type": "array", "items": {"type": "string"}},
                "risks": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["summary", "domain", "requirements"],
        }

    def _parse_result(
        self, result: Dict[str, Any], documents: List[Document]
    ) -> ExtractedRequirements:
        """Parse LLM result into domain models."""
        # Parse requirements
        requirements = []
        for req_data in result.get("requirements", []):
            req = Requirement(
                id=req_data.get("id", ""),
                text=req_data.get("text", ""),
                requirement_type=self._parse_requirement_type(req_data.get("type", "")),
                priority=self._parse_priority(req_data.get("priority", "")),
                stakeholders=req_data.get("stakeholders", []),
            )
            requirements.append(req)

        # Parse stakeholders
        stakeholders = []
        for sh_data in result.get("stakeholders", []):
            sh = Stakeholder(
                name=sh_data.get("name", ""),
                role=sh_data.get("role"),
                organization=sh_data.get("organization"),
                interests=sh_data.get("interests", []),
            )
            # Link to requirements
            sh.requirements = [r.id for r in requirements if sh.name in r.stakeholders]
            stakeholders.append(sh)

        # Parse objectives
        objectives = []
        for obj_data in result.get("objectives", []):
            obj = Objective(
                id=obj_data.get("id", ""),
                title=obj_data.get("title", ""),
                description=obj_data.get("description", ""),
                priority=self._parse_priority(obj_data.get("priority", "")),
                success_criteria=obj_data.get("success_criteria", []),
                related_requirements=obj_data.get("related_requirements", []),
            )
            objectives.append(obj)

        return ExtractedRequirements(
            documents=documents,
            requirements=requirements,
            stakeholders=stakeholders,
            objectives=objectives,
            summary=result.get("summary", ""),
            domain=result.get("domain"),
            constraints=result.get("constraints", []),
            assumptions=result.get("assumptions", []),
            risks=result.get("risks", []),
        )

    def _parse_requirement_type(self, type_str: str) -> RequirementType:
        """Parse requirement type from string."""
        type_map = {
            "functional": RequirementType.FUNCTIONAL,
            "non_functional": RequirementType.NON_FUNCTIONAL,
            "business": RequirementType.BUSINESS,
            "technical": RequirementType.TECHNICAL,
            "constraint": RequirementType.CONSTRAINT,
            "objective": RequirementType.OBJECTIVE,
        }
        return type_map.get(type_str.lower(), RequirementType.BUSINESS)

    def _parse_priority(self, priority_str: str) -> Priority:
        """Parse priority from string."""
        priority_map = {
            "critical": Priority.CRITICAL,
            "high": Priority.HIGH,
            "medium": Priority.MEDIUM,
            "low": Priority.LOW,
        }
        return priority_map.get(priority_str.lower(), Priority.UNKNOWN)

    def _create_fallback_extraction(
        self, documents: List[Document], error: Optional[str] = None
    ) -> ExtractedRequirements:
        """Create minimal extraction if LLM fails."""
        # Create a basic summary
        total_words = sum(doc.word_count for doc in documents)
        summary = (
            f"Document analysis incomplete. "
            f"Processed {len(documents)} document(s) with {total_words:,} words total."
        )

        if error:
            summary += f" (Error: {error[:100]})"

        return ExtractedRequirements(
            documents=documents,
            summary=summary,
            domain="Unknown (extraction failed)",
            requirements=[],
            stakeholders=[],
            objectives=[],
        )
