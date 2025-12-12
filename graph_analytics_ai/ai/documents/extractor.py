"""
Requirements extractor using LLM to analyze business documents.

This module processes parsed documents and uses LLM to extract:
- Business requirements
- Stakeholders
- Objectives
- Constraints and risks
"""

import json
from typing import List, Optional, Dict, Any

from ..llm import LLMProvider, get_default_provider
from .models import (
    Document,
    ExtractedRequirements,
    Requirement,
    RequirementType,
    Stakeholder,
    Objective,
    Priority
)


# LLM prompt for requirements extraction
REQUIREMENTS_EXTRACTION_PROMPT = """You are a business analyst expert at extracting requirements from documents.

Given the following business document(s), extract structured requirements information.

# Documents

{documents_text}

# Extraction Tasks

1. **Summary**: Provide a 2-3 sentence executive summary of what these documents describe.

2. **Domain**: Identify the business domain (e.g., "e-commerce", "healthcare", "financial services", "supply chain", "social network", etc.).

3. **Requirements**: Extract all business requirements. For each requirement:
   - Assign a unique ID (e.g., "REQ-001", "REQ-002")
   - Classify the type (functional, non_functional, business, technical, constraint, objective)
   - Assign priority (critical, high, medium, low, unknown)
   - Extract the requirement text
   - Identify associated stakeholders

4. **Stakeholders**: Identify all stakeholders mentioned. For each:
   - Name
   - Role/title (if mentioned)
   - Organization/department (if mentioned)
   - Key interests or concerns

5. **Objectives**: Extract business objectives. For each:
   - Assign a unique ID (e.g., "OBJ-001")
   - Title
   - Description
   - Priority
   - Success criteria (measurable outcomes)
   - Related requirement IDs

6. **Constraints**: List any constraints (budget, timeline, technical limitations, regulatory, etc.).

7. **Assumptions**: List any stated or implied assumptions.

8. **Risks**: Identify potential risks or concerns mentioned.

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
        max_content_length: int = 50000
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
            docs_text = docs_text[:self.max_content_length] + "\n\n[... content truncated ...]"
        
        # Format prompt
        prompt = REQUIREMENTS_EXTRACTION_PROMPT.format(
            documents_text=docs_text
        )
        
        # Extract with LLM
        try:
            result = self.llm_provider.generate_structured(
                prompt,
                schema=self._get_response_schema()
            )
            
            # Convert to domain models
            extracted = self._parse_result(result, documents)
            
            return extracted
        
        except Exception as e:
            # Return minimal extraction on failure
            return self._create_fallback_extraction(documents, error=str(e))
    
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
        
        return "\n".join(formatted)
    
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
                                "items": {"type": "string"}
                            }
                        }
                    }
                },
                "stakeholders": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "role": {"type": "string"},
                            "organization": {"type": "string"},
                            "interests": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    }
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
                                "items": {"type": "string"}
                            },
                            "related_requirements": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    }
                },
                "constraints": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "assumptions": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "risks": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["summary", "domain", "requirements"]
        }
    
    def _parse_result(
        self,
        result: Dict[str, Any],
        documents: List[Document]
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
                stakeholders=req_data.get("stakeholders", [])
            )
            requirements.append(req)
        
        # Parse stakeholders
        stakeholders = []
        for sh_data in result.get("stakeholders", []):
            sh = Stakeholder(
                name=sh_data.get("name", ""),
                role=sh_data.get("role"),
                organization=sh_data.get("organization"),
                interests=sh_data.get("interests", [])
            )
            # Link to requirements
            sh.requirements = [
                r.id for r in requirements
                if sh.name in r.stakeholders
            ]
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
                related_requirements=obj_data.get("related_requirements", [])
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
            risks=result.get("risks", [])
        )
    
    def _parse_requirement_type(self, type_str: str) -> RequirementType:
        """Parse requirement type from string."""
        type_map = {
            "functional": RequirementType.FUNCTIONAL,
            "non_functional": RequirementType.NON_FUNCTIONAL,
            "business": RequirementType.BUSINESS,
            "technical": RequirementType.TECHNICAL,
            "constraint": RequirementType.CONSTRAINT,
            "objective": RequirementType.OBJECTIVE
        }
        return type_map.get(type_str.lower(), RequirementType.BUSINESS)
    
    def _parse_priority(self, priority_str: str) -> Priority:
        """Parse priority from string."""
        priority_map = {
            "critical": Priority.CRITICAL,
            "high": Priority.HIGH,
            "medium": Priority.MEDIUM,
            "low": Priority.LOW
        }
        return priority_map.get(priority_str.lower(), Priority.UNKNOWN)
    
    def _create_fallback_extraction(
        self,
        documents: List[Document],
        error: Optional[str] = None
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
            objectives=[]
        )
