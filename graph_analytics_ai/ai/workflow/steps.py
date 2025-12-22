"""
Individual workflow step implementations.

Each method corresponds to a step in the AI-assisted graph analytics workflow.
"""

from pathlib import Path
from typing import List, Optional, Dict

from ..llm.base import LLMProvider
from ..documents.parser import parse_documents
from ..documents.extractor import RequirementsExtractor
from ..documents.models import Document, ExtractedRequirements
from ..schema.extractor import create_extractor
from ..schema.analyzer import SchemaAnalyzer
from ..schema.models import GraphSchema, SchemaAnalysis
from ..generation.prd import PRDGenerator
from ..generation.use_cases import UseCaseGenerator, UseCase


class WorkflowSteps:
    """
    Executes individual workflow steps.

    This class encapsulates the logic for each step in the workflow,
    making it easy to test and maintain each step independently.
    """

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize workflow steps.

        Args:
            llm_provider: LLM provider for AI operations.
        """
        self.llm_provider = llm_provider

    def parse_documents(self, document_paths: List[str]) -> List[Document]:
        """
        Step 1: Parse business requirement documents.

        Args:
            document_paths: Paths to documents to parse.

        Returns:
            List of parsed documents.

        Raises:
            WorkflowStepError: If parsing fails.
        """
        return parse_documents(document_paths)

    def extract_requirements(self, documents: List[Document]) -> ExtractedRequirements:
        """
        Step 2: Extract requirements from parsed documents using LLM.

        Args:
            documents: Parsed documents from step 1.

        Returns:
            Extracted requirements.

        Raises:
            WorkflowStepError: If extraction fails.
        """
        extractor = RequirementsExtractor(self.llm_provider)
        return extractor.extract(documents)

    def extract_schema(
        self,
        database_endpoint: str,
        database_name: str,
        username: str = "root",
        password: str = "",
    ) -> GraphSchema:
        """
        Step 3: Extract graph schema from ArangoDB.

        Args:
            database_endpoint: ArangoDB endpoint URL.
            database_name: Name of the database.
            username: Database username.
            password: Database password.

        Returns:
            Extracted graph schema.

        Raises:
            WorkflowStepError: If extraction fails.
        """
        extractor = create_extractor(
            endpoint=database_endpoint,
            database=database_name,
            username=username,
            password=password,
        )
        return extractor.extract()

    def analyze_schema(self, schema: GraphSchema) -> SchemaAnalysis:
        """
        Step 4: Analyze graph schema using LLM.

        Args:
            schema: Extracted graph schema from step 3.

        Returns:
            Schema analysis with insights.

        Raises:
            WorkflowStepError: If analysis fails.
        """
        analyzer = SchemaAnalyzer(self.llm_provider)
        return analyzer.analyze(schema)

    def generate_prd(
        self,
        extracted_requirements: ExtractedRequirements,
        schema: Optional[GraphSchema] = None,
        schema_analysis: Optional[SchemaAnalysis] = None,
        product_name: str = "Graph Analytics AI Project",
    ) -> str:
        """
        Step 5: Generate Product Requirements Document.

        Args:
            extracted_requirements: Extracted requirements from step 2.
            schema: Optional graph schema from step 3.
            schema_analysis: Optional schema analysis from step 4.
            product_name: Name of the product/project.

        Returns:
            PRD as markdown string.

        Raises:
            WorkflowStepError: If generation fails.
        """
        generator = PRDGenerator()
        return generator.generate_prd(
            extracted=extracted_requirements,
            schema=schema,
            schema_analysis=schema_analysis,
            product_name=product_name,
        )

    def generate_use_cases(
        self,
        extracted_requirements: ExtractedRequirements,
        schema_analysis: Optional[SchemaAnalysis] = None,
    ) -> List[UseCase]:
        """
        Step 6: Generate graph analytics use cases.

        Args:
            extracted_requirements: Extracted requirements from step 2.
            schema_analysis: Optional schema analysis from step 4.

        Returns:
            List of generated use cases.

        Raises:
            WorkflowStepError: If generation fails.
        """
        generator = UseCaseGenerator()
        return generator.generate(
            extracted=extracted_requirements, schema_analysis=schema_analysis
        )

    def save_outputs(
        self,
        output_dir: Path,
        prd_content: Optional[str] = None,
        use_cases: Optional[List[UseCase]] = None,
        schema: Optional[GraphSchema] = None,
        schema_analysis: Optional[SchemaAnalysis] = None,
        extracted_requirements: Optional[ExtractedRequirements] = None,
    ) -> Dict[str, str]:
        """
        Step 7: Save all outputs to files.

        Args:
            output_dir: Directory to save outputs.
            prd_content: PRD markdown content.
            use_cases: Generated use cases.
            schema: Extracted schema.
            schema_analysis: Schema analysis.
            extracted_requirements: Extracted requirements.

        Returns:
            Dictionary mapping output type to file path.

        Raises:
            WorkflowStepError: If saving fails.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        saved_files = {}

        # Save PRD
        if prd_content:
            prd_path = output_dir / "product_requirements.md"
            prd_path.write_text(prd_content)
            saved_files["prd"] = str(prd_path)

        # Save use cases
        if use_cases:
            use_cases_path = output_dir / "use_cases.md"
            use_cases_md = self._format_use_cases_markdown(use_cases)
            use_cases_path.write_text(use_cases_md)
            saved_files["use_cases"] = str(use_cases_path)

        # Save schema report
        if schema and schema_analysis:
            schema_path = output_dir / "schema_analysis.md"
            analyzer = SchemaAnalyzer(self.llm_provider)
            schema_report = analyzer.generate_report(schema_analysis)
            schema_path.write_text(schema_report)
            saved_files["schema"] = str(schema_path)

        # Save requirements summary
        if extracted_requirements:
            req_path = output_dir / "requirements_summary.md"
            req_summary = self._format_requirements_summary(extracted_requirements)
            req_path.write_text(req_summary)
            saved_files["requirements"] = str(req_path)

        return saved_files

    def _format_use_cases_markdown(self, use_cases: List[UseCase]) -> str:
        """Format use cases as markdown."""
        lines = ["# Graph Analytics Use Cases\n"]
        lines.append(f"Generated {len(use_cases)} use cases for graph analytics.\n")

        for uc in use_cases:
            lines.append(f"\n## {uc.id}: {uc.title}\n")
            lines.append(f"**Type:** {uc.use_case_type.value}  ")
            lines.append(f"**Priority:** {uc.priority.value}\n")
            lines.append(f"\n### Description\n{uc.description}\n")

            if uc.related_requirements:
                lines.append("\n### Related Requirements\n")
                for req_id in uc.related_requirements:
                    lines.append(f"- {req_id}")
                lines.append("")

            if uc.graph_algorithms:
                lines.append("\n### Suggested Algorithms\n")
                for algo in uc.graph_algorithms:
                    lines.append(f"- {algo}")
                lines.append("")

            if uc.data_needs:
                lines.append("\n### Data Requirements\n")
                for need in uc.data_needs:
                    lines.append(f"- {need}")
                lines.append("")

            if uc.expected_outputs:
                lines.append("\n### Expected Outputs\n")
                for output in uc.expected_outputs:
                    lines.append(f"- {output}")
                lines.append("")

            if uc.success_metrics:
                lines.append("\n### Success Metrics\n")
                for metric in uc.success_metrics:
                    lines.append(f"- {metric}")
                lines.append("")

        return "\n".join(lines)

    def _format_requirements_summary(self, extracted: ExtractedRequirements) -> str:
        """Format extracted requirements as markdown summary."""
        lines = ["# Requirements Summary\n"]
        lines.append(f"**Domain:** {extracted.domain or 'General'}")
        lines.append(f"**Total Requirements:** {extracted.total_requirements}")
        lines.append(f"**Documents Analyzed:** {len(extracted.documents)}\n")

        if extracted.summary:
            lines.append(f"## Executive Summary\n{extracted.summary}\n")

        if extracted.objectives:
            lines.append(f"## Objectives ({len(extracted.objectives)})\n")
            for obj in extracted.objectives:
                lines.append(f"- **{obj.id}**: {obj.title} ({obj.priority.value})")
            lines.append("")

        if extracted.stakeholders:
            lines.append(f"## Stakeholders ({len(extracted.stakeholders)})\n")
            for sh in extracted.stakeholders:
                lines.append(f"- **{sh.name}** ({sh.role}): {sh.interest}")
            lines.append("")

        # Group requirements by priority
        critical = extracted.critical_requirements
        high = [r for r in extracted.all_requirements if r.priority.value == "high"]
        [r for r in extracted.all_requirements if r.priority.value == "medium"]
        [r for r in extracted.all_requirements if r.priority.value == "low"]

        if critical:
            lines.append(f"## Critical Requirements ({len(critical)})\n")
            for req in critical:
                lines.append(f"- **{req.id}**: {req.text}")
            lines.append("")

        if high:
            lines.append(f"## High Priority Requirements ({len(high)})\n")
            for req in high[:5]:  # Show top 5
                lines.append(f"- **{req.id}**: {req.text}")
            if len(high) > 5:
                lines.append(f"- _... and {len(high) - 5} more_")
            lines.append("")

        return "\n".join(lines)
