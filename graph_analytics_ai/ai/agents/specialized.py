"""
Specialized domain agents.

Each agent has specific expertise and responsibilities.
"""

from typing import Any, Optional, List

from ..llm.base import LLMProvider
from ..schema.extractor import SchemaExtractor
from ..schema.analyzer import SchemaAnalyzer
from ..documents.parser import DocumentParser
from ..documents.extractor import RequirementsExtractor
from ..generation.use_cases import UseCaseGenerator
from ..templates import TemplateGenerator
from ..execution import AnalysisExecutor
from ..reporting import ReportGenerator

from .base import (
    SpecializedAgent,
    AgentType,
    AgentMessage,
    AgentState,
    handle_agent_errors,
)
from .constants import AgentNames, AgentDefaults


class SchemaAnalysisAgent(SpecializedAgent):
    """
    Agent specialized in graph schema analysis.

    Extracts and analyzes database schemas, identifies patterns.
    """

    SYSTEM_PROMPT = """You are a Graph Database Schema Expert.

Your expertise:
- Analyzing graph database structures
- Identifying vertex and edge patterns
- Detecting graph complexity and characteristics
- Recommending optimal analysis approaches

Your goal: Provide deep insights about graph structure to guide analytics."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        db_connection,
        trace_collector: Optional[Any] = None,
    ):
        super().__init__(
            agent_type=AgentType.SCHEMA_ANALYSIS,
            name=AgentNames.SCHEMA_ANALYST,
            llm_provider=llm_provider,
            system_prompt=self.SYSTEM_PROMPT,
            trace_collector=trace_collector,
        )
        self.db = db_connection
        self.extractor = SchemaExtractor(db_connection)
        self.analyzer = SchemaAnalyzer(llm_provider)

    @handle_agent_errors
    def process(self, message: AgentMessage, state: AgentState) -> AgentMessage:
        """Extract and analyze schema."""
        self.log("Starting schema analysis...")

        # Extract schema
        schema = self.extractor.extract()
        state.schema = schema

        self.log(
            f"Extracted: {len(schema.vertex_collections)}V + {len(schema.edge_collections)}E"
        )

        # Analyze schema
        try:
            analysis = self.analyzer.analyze(schema)
        except:
            self.log("LLM analysis unavailable, using fallback", "warning")
            analysis = self.analyzer._create_fallback_analysis(schema)

        state.schema_analysis = analysis
        state.mark_step_complete("schema_analysis")

        self.log(
            f"Analysis complete: {analysis.domain}, complexity {analysis.complexity_score:.1f}/10"
        )

        return self.create_success_message(
            to_agent="orchestrator",
            content={
                "schema": {
                    "vertices": len(schema.vertex_collections),
                    "edges": len(schema.edge_collections),
                    "total_documents": schema.total_documents,
                    "total_edges": schema.total_edges,
                },
                "analysis": {
                    "domain": analysis.domain,
                    "complexity": analysis.complexity_score,
                },
            },
            reply_to=message.message_id,
        )


class RequirementsAgent(SpecializedAgent):
    """
    Agent specialized in business requirements analysis.

    Extracts and structures business requirements from documents.
    """

    SYSTEM_PROMPT = """You are a Business Requirements Analyst Expert.

Your expertise:
- Extracting business objectives from documents
- Identifying functional and non-functional requirements
- Prioritizing requirements by business value
- Ensuring requirement completeness and clarity

Your goal: Transform business needs into structured requirements."""

    def __init__(
        self, llm_provider: LLMProvider, trace_collector: Optional[Any] = None
    ):
        super().__init__(
            agent_type=AgentType.REQUIREMENTS,
            name=AgentNames.REQUIREMENTS_ANALYST,
            llm_provider=llm_provider,
            system_prompt=self.SYSTEM_PROMPT,
            trace_collector=trace_collector,
        )
        self.parser = DocumentParser()
        self.extractor = RequirementsExtractor(llm_provider)

    @handle_agent_errors
    def process(self, message: AgentMessage, state: AgentState) -> AgentMessage:
        """Parse and extract requirements."""
        self.log("Analyzing requirements...")

        documents = message.content.get("documents", [])

        if not documents:
            self.log("No documents provided, using defaults", "warning")
            # Create default requirements
            from ..documents.models import (
                ExtractedRequirements,
                Objective,
                Requirement,
                Priority,
                RequirementType,
            )

            requirements = ExtractedRequirements(
                domain="Graph Analytics",
                summary="General graph analytics requirements",
                documents=[],
                objectives=[
                    Objective(
                        id="OBJ-001",
                        title="Analyze Graph Structure",
                        description="Understand key patterns and relationships",
                        priority=Priority.HIGH,
                        success_criteria=["Identify key entities", "Map relationships"],
                    )
                ],
                requirements=[
                    Requirement(
                        id="REQ-001",
                        text="Identify influential nodes",
                        requirement_type=RequirementType.FUNCTIONAL,
                        priority=Priority.HIGH,
                    )
                ],
                stakeholders=[],
                constraints=[],
                risks=[],
            )
        else:
            # Parse documents
            parsed_docs = [self.parser.parse_document(doc) for doc in documents]
            requirements = self.extractor.extract(parsed_docs)

        state.requirements = requirements
        state.mark_step_complete("requirements_extraction")

        self.log(
            f"Extracted: {len(requirements.objectives)} objectives, {len(requirements.requirements)} requirements"
        )

        return self.create_success_message(
            to_agent="orchestrator",
            content={
                "requirements": {
                    "domain": requirements.domain,
                    "objectives_count": len(requirements.objectives),
                    "requirements_count": len(requirements.requirements),
                }
            },
            reply_to=message.message_id,
        )


class UseCaseAgent(SpecializedAgent):
    """
    Agent specialized in graph analytics use case generation.

    Maps business requirements to graph algorithms.
    """

    SYSTEM_PROMPT = """You are a Graph Analytics Consultant Expert.

Your expertise:
- Mapping business needs to graph algorithms
- Identifying high-value analytics use cases
- Understanding algorithm strengths and limitations
- Prioritizing use cases by business impact

Your goal: Generate actionable analytics use cases."""

    def __init__(
        self, llm_provider: LLMProvider, trace_collector: Optional[Any] = None
    ):
        super().__init__(
            agent_type=AgentType.USE_CASE,
            name=AgentNames.USE_CASE_EXPERT,
            llm_provider=llm_provider,
            system_prompt=self.SYSTEM_PROMPT,
            trace_collector=trace_collector,
        )
        self.generator = UseCaseGenerator()

    @handle_agent_errors
    def process(self, message: AgentMessage, state: AgentState) -> AgentMessage:
        """Generate use cases."""
        self.log("Generating use cases...")

        if not state.requirements or not state.schema_analysis:
            raise ValueError("Requirements and schema analysis needed")

        use_cases = self.generator.generate(state.requirements, state.schema_analysis)

        state.use_cases = use_cases
        state.mark_step_complete("use_case_generation")

        self.log(f"Generated {len(use_cases)} use cases")

        return self.create_success_message(
            to_agent="orchestrator",
            content={
                "use_cases_count": len(use_cases),
                "use_cases": [
                    {
                        "id": uc.id,
                        "title": uc.title,
                        "use_case_type": uc.use_case_type.value,
                    }
                    for uc in use_cases[: AgentDefaults.MAX_RESULTS_IN_MESSAGE]
                ],
            },
            reply_to=message.message_id,
        )


class TemplateAgent(SpecializedAgent):
    """
    Agent specialized in GAE template generation.

    Converts use cases to optimized analysis templates.
    """

    SYSTEM_PROMPT = """You are a Graph Analytics Engineer Expert.

Your expertise:
- Configuring graph analysis algorithms
- Optimizing algorithm parameters
- Sizing compute resources
- Validating template correctness

Your goal: Create optimized, executable analysis templates."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        graph_name: str = "graph",
        core_collections: Optional[List[str]] = None,
        satellite_collections: Optional[List[str]] = None,
        trace_collector: Optional[Any] = None,
    ):
        super().__init__(
            agent_type=AgentType.TEMPLATE,
            name=AgentNames.TEMPLATE_ENGINEER,
            llm_provider=llm_provider,
            system_prompt=self.SYSTEM_PROMPT,
            trace_collector=trace_collector,
        )
        self.generator = TemplateGenerator(
            graph_name=graph_name,
            core_collections=core_collections,
            satellite_collections=satellite_collections,
        )

    @handle_agent_errors
    def process(self, message: AgentMessage, state: AgentState) -> AgentMessage:
        """Generate templates."""
        self.log("Generating GAE templates...")

        if not state.use_cases or not state.schema or not state.schema_analysis:
            raise ValueError("Use cases, schema, and analysis needed")

        templates = self.generator.generate_templates(
            state.use_cases, state.schema, state.schema_analysis
        )

        state.templates = templates
        state.mark_step_complete("template_generation")

        self.log(f"Generated {len(templates)} templates")

        return self.create_success_message(
            to_agent="orchestrator",
            content={
                "templates_count": len(templates),
                "templates": [
                    {
                        "name": t.name,
                        "algorithm": (
                            t.algorithm.algorithm_type.value
                            if hasattr(t.algorithm, "algorithm_type")
                            else str(t.algorithm)
                        ),
                        "engine_size": (
                            t.config.engine_size.value
                            if hasattr(t.config, "engine_size")
                            else "unknown"
                        ),
                    }
                    for t in templates[: AgentDefaults.MAX_RESULTS_IN_MESSAGE]
                ],
            },
            reply_to=message.message_id,
        )


class ExecutionAgent(SpecializedAgent):
    """
    Agent specialized in analysis execution.

    Executes templates on GAE cluster with monitoring.
    """

    SYSTEM_PROMPT = """You are a Graph Analytics Operations Expert.

Your expertise:
- Executing graph analyses on GAE clusters
- Monitoring execution progress
- Handling errors and retries
- Optimizing resource usage

Your goal: Execute analyses reliably and efficiently."""

    def __init__(
        self, llm_provider: LLMProvider, trace_collector: Optional[Any] = None
    ):
        super().__init__(
            agent_type=AgentType.EXECUTION,
            name=AgentNames.EXECUTION_SPECIALIST,
            llm_provider=llm_provider,
            system_prompt=self.SYSTEM_PROMPT,
            trace_collector=trace_collector,
        )
        self.executor = AnalysisExecutor()

    @handle_agent_errors
    def process(self, message: AgentMessage, state: AgentState) -> AgentMessage:
        """Execute analyses."""
        self.log("Executing analyses...")

        if not state.templates:
            raise ValueError("Templates needed for execution")

        # Execute templates (limited to first few for demo)
        max_executions = message.content.get(
            "max_executions", AgentDefaults.MAX_EXECUTIONS
        )
        templates_to_run = state.templates[:max_executions]

        results = []
        for template in templates_to_run:
            self.log(f"Executing: {template.name}")
            result = self.executor.execute_template(template, wait=True)
            results.append(result)

            if result.success:
                self.log(f"✓ Completed in {result.job.execution_time_seconds:.1f}s")
            else:
                self.log(f"✗ Failed: {result.error}", "error")

        state.execution_results = results
        state.mark_step_complete("execution")

        successful = sum(1 for r in results if r.success)

        return self.create_success_message(
            to_agent="orchestrator",
            content={
                "total": len(results),
                "successful": successful,
                "failed": len(results) - successful,
            },
            reply_to=message.message_id,
        )


class ReportingAgent(SpecializedAgent):
    """
    Agent specialized in report generation.

    Generates actionable intelligence reports from results.
    """

    SYSTEM_PROMPT = """You are a Business Intelligence Report Expert.

Your expertise:
- Analyzing graph analytics results
- Extracting business insights
- Generating actionable recommendations
- Communicating technical findings to business stakeholders

Your goal: Transform analysis results into actionable intelligence."""

    def __init__(
        self, llm_provider: LLMProvider, trace_collector: Optional[Any] = None
    ):
        super().__init__(
            agent_type=AgentType.REPORTING,
            name=AgentNames.REPORTING_SPECIALIST,
            llm_provider=llm_provider,
            system_prompt=self.SYSTEM_PROMPT,
            trace_collector=trace_collector,
        )
        self.generator = ReportGenerator(llm_provider, use_llm_interpretation=False)

    @handle_agent_errors
    def process(self, message: AgentMessage, state: AgentState) -> AgentMessage:
        """Generate reports with full context."""
        self.log("Generating reports...")

        if not state.execution_results:
            raise ValueError("Execution results needed for reporting")

        # Generate reports for successful executions
        successful_results = [r for r in state.execution_results if r.success]

        if not successful_results:
            raise ValueError("No successful executions to report on")

        # Build rich context from workflow state
        context = {
            "requirements": {
                "domain": state.requirements.domain if state.requirements else None,
                "summary": state.requirements.summary if state.requirements else None,
                "objectives": [
                    {
                        "title": obj.title,
                        "description": obj.description,
                        "success_criteria": obj.success_criteria,
                    }
                    for obj in (
                        state.requirements.objectives if state.requirements else []
                    )
                ],
                "constraints": (
                    state.requirements.constraints if state.requirements else []
                ),
            },
            "schema_analysis": {
                "domain": (
                    state.schema_analysis.domain if state.schema_analysis else None
                ),
                "complexity_score": (
                    state.schema_analysis.complexity_score
                    if state.schema_analysis
                    else None
                ),
                "description": (
                    state.schema_analysis.description if state.schema_analysis else None
                ),
                "key_entities": (
                    state.schema_analysis.key_entities if state.schema_analysis else []
                ),
                "key_relationships": (
                    state.schema_analysis.key_relationships
                    if state.schema_analysis
                    else []
                ),
            },
            "use_cases": [
                {
                    "id": uc.id,
                    "title": uc.title,
                    "objective": getattr(uc, "objective", None),
                    "use_case_type": (
                        uc.use_case_type.value if hasattr(uc, "use_case_type") else None
                    ),
                }
                for uc in state.use_cases
            ],
        }

        reports = []
        for i, result in enumerate(successful_results):
            # Add use case-specific context if available
            use_case_context = context.copy()
            if i < len(state.use_cases):
                use_case_context["use_case"] = context["use_cases"][i]

            report = self.generator.generate_report(result, context=use_case_context)
            reports.append(report)

        state.reports = reports
        state.mark_step_complete("reporting")

        total_insights = sum(len(r.insights) for r in reports)
        total_recommendations = sum(len(r.recommendations) for r in reports)

        self.log(f"Generated {len(reports)} reports with {total_insights} insights")

        return self.create_success_message(
            to_agent="orchestrator",
            content={
                "reports_count": len(reports),
                "total_insights": total_insights,
                "total_recommendations": total_recommendations,
            },
            reply_to=message.message_id,
        )
