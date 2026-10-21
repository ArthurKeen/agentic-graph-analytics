"""
Constants for agent system.

Centralizes agent names, workflow steps, and configuration constants.
"""


class AgentNames:
    """Standard agent names used in the system."""

    ORCHESTRATOR = "Orchestrator"
    SCHEMA_ANALYST = "SchemaAnalyst"
    REQUIREMENTS_ANALYST = "RequirementsAnalyst"
    USE_CASE_EXPERT = "UseCaseExpert"
    TEMPLATE_ENGINEER = "TemplateEngineer"
    EXECUTION_SPECIALIST = "ExecutionSpecialist"
    REPORTING_SPECIALIST = "ReportingSpecialist"


class WorkflowSteps:
    """Standard workflow step names."""

    SCHEMA_ANALYSIS = "schema_analysis"
    REQUIREMENTS_EXTRACTION = "requirements_extraction"
    USE_CASE_GENERATION = "use_case_generation"
    TEMPLATE_GENERATION = "template_generation"
    EXECUTION = "execution"
    REPORTING = "reporting"

    # Standard workflow order
    STANDARD_WORKFLOW = [
        SCHEMA_ANALYSIS,
        REQUIREMENTS_EXTRACTION,
        USE_CASE_GENERATION,
        TEMPLATE_GENERATION,
        EXECUTION,
        REPORTING,
    ]


class AgentDefaults:
    """Default values for agent configuration."""

    # Maximum number of analyses to execute in a single workflow
    MAX_EXECUTIONS = 3

    # How many analyses may be in flight at once.
    #
    # Analyses share one GAE engine, and each one loads the whole graph before
    # it runs. Fanning every template out at once therefore multiplies the load
    # on a single engine rather than spreading it: a FinReflectKG run (3.1M
    # vertices / 17.5M edges) lost analyses to `503 Service Unavailable` on
    # /loaddata and to jobs that never registered inside the status-poll grace
    # window, and left three orphaned engines billing. 2 keeps some overlap
    # without stampeding the engine; raise it only for small graphs.
    # Override with GAE_MAX_CONCURRENT_ANALYSES.
    MAX_CONCURRENT_ANALYSES = 2

    # Maximum retry attempts for failed steps
    MAX_RETRIES = 2

    # Timeout for agent operations (seconds)
    AGENT_TIMEOUT = 300

    # Maximum results to include in messages
    MAX_RESULTS_IN_MESSAGE = 5
