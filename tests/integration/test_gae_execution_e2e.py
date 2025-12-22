"""
GAE execution integration tests.

Tests actual GAE algorithm execution with real engines.

Requirements:
- ARANGO_GRAPH_TOKEN or ArangoDB credentials
- GAE access (AMP or self-managed)
- Test database with graph data

Run with: pytest tests/integration/test_gae_execution_e2e.py --run-integration -v
"""

import pytest
import time

from graph_analytics_ai import GAEOrchestrator, AnalysisConfig, AnalysisStatus
from graph_analytics_ai.ai.execution.metrics import (
    ExecutionSummary,
    TimingBreakdown,
    CostBreakdown,
    AlgorithmExecutionStats,
)
from graph_analytics_ai.ai.reporting import ExecutionReportFormatter, ReportConfig


@pytest.mark.integration
@pytest.mark.requires_gae
@pytest.mark.requires_db
class TestGAEExecutionE2E:
    """End-to-end GAE execution tests."""

    def test_complete_gae_analysis_with_metrics(self, check_env_vars, temp_output_dir):
        """
        Test complete GAE analysis with real engine and metric tracking.

        This test:
        1. Deploys a GAE engine
        2. Loads graph data
        3. Runs PageRank algorithm
        4. Stores results
        5. Verifies metrics were tracked
        6. Cleans up engine
        """
        # Initialize orchestrator
        orchestrator = GAEOrchestrator(verbose=True)

        # Configure analysis
        config = AnalysisConfig(
            name="Integration Test - PageRank",
            database=check_env_vars["db_name"],
            vertex_collections=["customers", "products"],
            edge_collections=["purchased", "viewed"],
            algorithm="pagerank",
            algorithm_params={"damping_factor": 0.85, "maximum_supersteps": 20},
            target_collection="pagerank_results_test",
            result_field="pagerank_score",
            engine_size="e8",  # Small engine for testing
            auto_cleanup=True,
        )

        # Run analysis
        result = orchestrator.run_analysis(config)

        # Verify analysis completed
        assert (
            result.status == AnalysisStatus.COMPLETED
        ), f"Analysis failed: {result.error_message}"
        assert result.duration_seconds is not None
        assert result.duration_seconds > 0

        # Verify phase timing was tracked
        assert result.deploy_time_seconds is not None
        assert result.load_time_seconds is not None
        assert result.execution_time_seconds is not None
        assert result.store_time_seconds is not None

        assert result.deploy_time_seconds > 0
        assert result.load_time_seconds > 0
        assert result.execution_time_seconds > 0
        assert result.store_time_seconds > 0

        # Verify graph info
        assert result.graph_id is not None
        assert result.vertex_count > 0
        assert result.edge_count > 0

        # Verify job info
        assert result.job_id is not None
        assert result.algorithm == "pagerank"

        # Verify results
        assert result.results_stored is True
        assert result.documents_updated is not None
        assert result.documents_updated > 0

        # Verify cost tracking (AMP only)
        if result.estimated_cost_usd is not None:
            assert result.estimated_cost_usd > 0
            assert result.engine_runtime_minutes > 0

        print("\n✅ GAE analysis test passed!")
        print(f"   Duration: {result.duration_seconds:.1f}s")
        print(f"   Deploy: {result.deploy_time_seconds:.1f}s")
        print(f"   Load: {result.load_time_seconds:.1f}s")
        print(f"   Execute: {result.execution_time_seconds:.1f}s")
        print(f"   Store: {result.store_time_seconds:.1f}s")
        print(f"   Vertices: {result.vertex_count:,}")
        print(f"   Edges: {result.edge_count:,}")
        print(f"   Results: {result.documents_updated:,}")
        if result.estimated_cost_usd:
            print(f"   Cost: ${result.estimated_cost_usd:.4f}")

    def test_execution_summary_generation(self, check_env_vars, temp_output_dir):
        """
        Test execution summary and report generation from GAE results.
        """

        # Run a simple analysis
        orchestrator = GAEOrchestrator(verbose=True)

        config = AnalysisConfig(
            name="Integration Test - WCC",
            database=check_env_vars["db_name"],
            vertex_collections=["customers"],
            edge_collections=["purchased"],
            algorithm="wcc",
            target_collection="wcc_results_test",
            result_field="component",
            engine_size="e8",
            auto_cleanup=True,
        )

        result = orchestrator.run_analysis(config)

        assert result.status == AnalysisStatus.COMPLETED

        # Create execution summary from result
        summary = ExecutionSummary(
            workflow_id=f"test_{int(time.time())}",
            started_at=result.start_time,
            completed_at=result.end_time,
            templates_executed=1,
            templates_succeeded=1,
            templates_failed=0,
            total_execution_time_seconds=result.duration_seconds or 0,
            total_vertices_processed=result.vertex_count or 0,
            total_edges_processed=result.edge_count or 0,
            total_results_generated=result.documents_updated or 0,
            engine_size=result.engine_size,
            deployment_mode="test",
        )

        # Add timing breakdown
        summary.timing_breakdown = TimingBreakdown(
            graph_load_seconds=result.load_time_seconds or 0,
            algorithm_execution_seconds=result.execution_time_seconds or 0,
            results_store_seconds=result.store_time_seconds or 0,
            total_seconds=result.duration_seconds or 0,
        )

        # Add cost breakdown if available
        if result.estimated_cost_usd:
            summary.cost_breakdown = CostBreakdown(
                runtime_cost_usd=result.estimated_cost_usd,
                total_cost_usd=result.estimated_cost_usd,
                runtime_minutes=result.engine_runtime_minutes or 0,
                engine_size=result.engine_size,
            )

        # Add algorithm stats
        summary.add_algorithm_stats(
            AlgorithmExecutionStats(
                algorithm=result.algorithm or "unknown",
                job_id=result.job_id,
                execution_time_seconds=result.execution_time_seconds or 0,
                vertex_count=result.vertex_count or 0,
                edge_count=result.edge_count or 0,
                results_count=result.documents_updated or 0,
                status="completed",
                retry_count=result.retry_count,
            )
        )

        # Verify summary
        assert summary.templates_executed == 1
        assert summary.templates_succeeded == 1
        assert summary.success_rate == 100.0
        assert summary.total_duration_seconds > 0

        # Generate report
        config = ReportConfig(include_costs=True)
        formatter = ExecutionReportFormatter(config)

        report_md = formatter.format_report(summary)

        # Verify report content
        assert len(report_md) > 500, "Report too short"
        assert "GAE Execution Report" in report_md
        assert "Executive Summary" in report_md
        assert "Timing Breakdown" in report_md
        assert "Performance Metrics" in report_md

        # Save report
        report_path = temp_output_dir / "execution_report.md"
        formatter.save_report(summary, report_path)

        assert report_path.exists()

        print("\n✅ Execution summary test passed!")
        print(f"   Report generated: {report_path}")
        print(f"   Report size: {len(report_md)} characters")

    def test_multiple_algorithms_with_summary(self, check_env_vars, temp_output_dir):
        """
        Test running multiple algorithms and aggregating metrics.
        """

        orchestrator = GAEOrchestrator(verbose=True)

        algorithms = ["wcc", "scc"]
        results = []

        for algo in algorithms:
            config = AnalysisConfig(
                name=f"Integration Test - {algo.upper()}",
                database=check_env_vars["db_name"],
                vertex_collections=["customers"],
                edge_collections=["purchased"],
                algorithm=algo,
                target_collection=f"{algo}_results_test",
                result_field=f"{algo}_value",
                engine_size="e8",
                auto_cleanup=True,
            )

            result = orchestrator.run_analysis(config)
            results.append(result)

            # Small delay between tests
            time.sleep(2)

        # Verify all completed
        for result in results:
            assert result.status == AnalysisStatus.COMPLETED

        # Create aggregate summary
        summary = ExecutionSummary(
            workflow_id=f"multi_test_{int(time.time())}",
            started_at=results[0].start_time,
            completed_at=results[-1].end_time,
            templates_executed=len(results),
            templates_succeeded=len(
                [r for r in results if r.status == AnalysisStatus.COMPLETED]
            ),
            templates_failed=len(
                [r for r in results if r.status != AnalysisStatus.COMPLETED]
            ),
        )

        # Aggregate metrics
        for result in results:
            summary.add_algorithm_stats(
                AlgorithmExecutionStats(
                    algorithm=result.algorithm or "unknown",
                    job_id=result.job_id,
                    execution_time_seconds=result.execution_time_seconds or 0,
                    vertex_count=result.vertex_count or 0,
                    edge_count=result.edge_count or 0,
                    results_count=result.documents_updated or 0,
                    status="completed",
                )
            )

        # Verify aggregation
        assert summary.templates_executed == len(algorithms)
        assert summary.templates_succeeded == len(algorithms)
        assert summary.total_execution_time_seconds > 0
        assert len(summary.algorithm_stats) == len(algorithms)

        print("\n✅ Multiple algorithms test passed!")
        print(f"   Algorithms run: {len(algorithms)}")
        print(f"   Total execution time: {summary.total_execution_time_seconds:.1f}s")
        print(f"   Success rate: {summary.success_rate}%")
