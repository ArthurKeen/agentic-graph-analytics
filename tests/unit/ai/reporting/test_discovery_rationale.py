"""FR-75: an autonomous run must report what it chose and why.

The planner has always had a reason for each analysis it picks. Until now
that reason was folded into ``UseCase.description`` and never reached the
reader, so a report from an unattended run could not be told apart from one
that analysed the whole graph by default — which is what the executor
actually did until PR #28.
"""

from datetime import datetime
from typing import Any, Dict, List

from graph_analytics_ai.ai.agents.base import AgentState
from graph_analytics_ai.ai.agents.specialized import ReportingAgent
from graph_analytics_ai.ai.execution.models import (
    AnalysisJob,
    ExecutionResult,
    ExecutionStatus,
)
from graph_analytics_ai.ai.generation.use_cases import Priority, UseCase, UseCaseType
from graph_analytics_ai.ai.llm.base import LLMConfig, LLMProvider, LLMResponse
from graph_analytics_ai.ai.reporting.generator import ReportGenerator
from graph_analytics_ai.ai.templates.models import (
    AlgorithmParameters,
    AlgorithmType,
    AnalysisTemplate,
    TemplateConfig,
)


class _StubProvider(LLMProvider):
    """Mirrors LLMProvider's two abstract methods and records use.

    Constructed with a real LLMConfig so a drift in that signature breaks
    this test rather than being papered over by a Mock.
    """

    def __init__(self):
        super().__init__(LLMConfig(api_key="none", model="stub-1"))
        self.calls = 0

    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        self.calls += 1
        raise AssertionError("the stub provider must not be called")

    async def generate_async(self, prompt: str, **kwargs) -> LLMResponse:
        self.calls += 1
        raise AssertionError("the stub provider must not be called")

    def generate_structured(
        self, prompt: str, schema: Dict[str, Any], **kwargs
    ) -> Dict[str, Any]:
        self.calls += 1
        raise AssertionError("the stub provider must not be called")

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        self.calls += 1
        raise AssertionError("the stub provider must not be called")


def _result(template_name: str, success: bool = True) -> ExecutionResult:
    job = AnalysisJob(
        job_id=f"job-{template_name}",
        template_name=template_name,
        algorithm="pagerank",
        status=(ExecutionStatus.COMPLETED if success else ExecutionStatus.FAILED),
        submitted_at=datetime(2026, 11, 3, 12, 0, 0),
        completed_at=datetime(2026, 11, 3, 12, 1, 0),
        result_count=2,
    )
    return ExecutionResult(
        job=job,
        success=success,
        results=[{"id": "Venue/a", "rank": 0.9}, {"id": "Venue/b", "rank": 0.4}],
    )


def _use_case(uid: str, title: str, rationale: str, targets) -> UseCase:
    return UseCase(
        id=uid,
        title=title,
        description=f"{title}. {rationale}",
        rationale=rationale,
        use_case_type=UseCaseType.CENTRALITY,
        priority=Priority.HIGH,
        graph_algorithms=["pagerank"],
        data_needs=list(targets),
    )


def _template(use_case: UseCase) -> AnalysisTemplate:
    return AnalysisTemplate(
        name=f"{use_case.id}: {use_case.title}",
        description=use_case.description,
        algorithm=AlgorithmParameters(algorithm=AlgorithmType.PAGERANK),
        config=TemplateConfig(graph_name="citations"),
        use_case_id=use_case.id,
    )


def _context(use_cases):
    """The subset of ReportingAgent's context the report generator reads."""
    return {
        "workflow": {"discovery_mode": True},
        "use_cases": [
            {
                "id": uc.id,
                "title": uc.title,
                "rationale": uc.rationale,
                "algorithms": list(uc.graph_algorithms),
                "target_collections": list(uc.data_needs),
            }
            for uc in use_cases
        ],
    }


def _discovery_summary(report):
    for section in report.sections:
        if "Discovery Summary" in section.title:
            return section.content
    raise AssertionError("no Discovery Summary section")


def test_the_discovery_summary_says_which_analysis_and_why():
    use_case = _use_case(
        "UC-A01",
        "Influence among venues",
        "Venues are the smallest entity type at 300 nodes, so PageRank over "
        "them is cheap and the ranking is readable.",
        ["Venue"],
    )
    context = _context([use_case])
    context["use_case"] = context["use_cases"][0]

    generator = ReportGenerator(use_llm_interpretation=False, enable_charts=False)
    report = generator.generate_report(
        _result("UC-A01: Influence among venues"), context
    )

    summary = _discovery_summary(report)
    assert "Influence among venues" in summary
    assert "pagerank" in summary.lower()
    assert "Venue" in summary
    assert "smallest entity type at 300 nodes" in summary


def test_an_analysis_with_no_rationale_says_so_rather_than_implying_one():
    use_case = _use_case("UC-D01", "Overall influence", "", [])
    context = _context([use_case])
    context["use_case"] = context["use_cases"][0]

    generator = ReportGenerator(use_llm_interpretation=False, enable_charts=False)
    report = generator.generate_report(_result("UC-D01: Overall influence"), context)

    summary = _discovery_summary(report)
    assert "not recorded" in summary
    assert "the whole graph" in summary


def test_a_failed_execution_does_not_shift_the_rationale_onto_another_report():
    """The bug this guards: ``successful_results`` is filtered, so pairing
    report *i* with use case *i* moved every later report onto the previous
    analysis's reason once anything failed."""

    first = _use_case("UC-A01", "Venues", "Venues are small.", ["Venue"])
    second = _use_case("UC-A02", "Authors", "Authors drive citation flow.", ["Author"])

    state = AgentState()
    state.use_cases = [first, second]
    state.templates = [_template(first), _template(second)]

    # The first analysis failed; only the second produced a report.
    survivors = [_result("UC-A02: Authors")]
    context = _context([first, second])

    lookup = ReportingAgent._use_case_lookup(state, context)
    resolved = ReportingAgent._use_case_for_result(
        survivors[0], 0, survivors, state, lookup, context
    )

    assert resolved is not None
    assert resolved["id"] == "UC-A02"
    assert resolved["rationale"] == "Authors drive citation flow."


def test_an_unresolvable_result_carries_no_rationale_at_all():
    """A wrong reason is worse than none (NFR-19). When the template cannot
    be matched and executions were dropped, nothing is claimed."""

    first = _use_case("UC-A01", "Venues", "Venues are small.", ["Venue"])
    second = _use_case("UC-A02", "Authors", "Authors drive citation flow.", ["Author"])

    state = AgentState()
    state.use_cases = [first, second]
    state.templates = []  # no templates recorded, so no sound link

    survivors = [_result("UC-A02: Authors")]
    context = _context([first, second])

    lookup = ReportingAgent._use_case_lookup(state, context)
    resolved = ReportingAgent._use_case_for_result(
        survivors[0], 0, survivors, state, lookup, context
    )

    assert resolved is None


def test_the_assembled_reporting_agent_attributes_the_surviving_report():
    """The helpers above are unit-tested; this drives the real loop.

    One execution failed, so ``successful_results`` holds a single report
    that must carry UC-A02's reason. Before the fix the loop indexed the
    filtered list and handed it UC-A01's.
    """

    from graph_analytics_ai.ai.agents.base import AgentMessage

    first = _use_case("UC-A01", "Venues", "Venues are small.", ["Venue"])
    second = _use_case("UC-A02", "Authors", "Authors drive citation flow.", ["Author"])

    state = AgentState()
    state.use_cases = [first, second]
    state.templates = [_template(first), _template(second)]
    state.execution_results = [
        _result("UC-A01: Venues", success=False),
        _result("UC-A02: Authors"),
    ]
    state.metadata["discovery_mode"] = True

    agent = ReportingAgent(llm_provider=_StubProvider())
    # Insights come from the heuristic path, so the provider is never
    # called. Asserting that keeps the stub honest: a test that quietly
    # reached a real model would be measuring something else.
    agent.generator.use_llm_interpretation = False

    agent.process(
        AgentMessage(
            from_agent="test",
            to_agent="reporting",
            message_type="task",
            content={},
        ),
        state,
    )

    assert agent.llm_provider.calls == 0
    assert len(state.reports) == 1
    summary = _discovery_summary(state.reports[0])
    assert "Authors drive citation flow." in summary
    assert "Venues are small." not in summary
