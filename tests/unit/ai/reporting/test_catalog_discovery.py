from unittest.mock import Mock, patch


def test_catalog_discovery_generates_report_without_llm():
    from graph_analytics_ai.ai.reporting.catalog_discovery import (
        CatalogDiscoveryConfig,
        generate_catalog_discovery_report,
    )
    from graph_analytics_ai.ai.reporting.generator import ReportGenerator
    from graph_analytics_ai.ai.reporting.models import ReportFormat

    # Minimal fake catalog
    catalog = Mock()
    catalog.query_epochs.return_value = [
        Mock(epoch_id="epoch-latest"),
        Mock(epoch_id="epoch-baseline"),
    ]

    # Minimal fake executions (one per epoch)
    exec_latest = Mock(
        epoch_id="epoch-latest",
        algorithm="pagerank",
        results_location="uc_d01_results",
        status="completed",
    )
    exec_baseline = Mock(
        epoch_id="epoch-baseline",
        algorithm="pagerank",
        results_location="uc_d01_results_baseline",
        status="completed",
    )
    catalog.query_executions.side_effect = [[exec_latest], [exec_baseline]]
    catalog.get_epoch_by_name.return_value = None

    db = Mock()

    fake_latest_results = [{"id": "RTL_Module/a", "rank": 0.9}]
    fake_baseline_results = [{"id": "RTL_Module/a", "rank": 0.4}]

    with patch(
        "graph_analytics_ai.ai.reporting.catalog_discovery.ResultSelector.select_results",
        side_effect=[(fake_latest_results, None), (fake_baseline_results, None)],
    ), patch(
        "graph_analytics_ai.ai.reporting.catalog_discovery.detect_patterns",
        return_value=[],
    ):
        cfg = CatalogDiscoveryConfig(
            industry="eda_ic_design",
            since_epochs=2,
            algorithms=("pagerank",),
            per_execution_limit=1000,
        )
        report = generate_catalog_discovery_report(catalog=catalog, db=db, cfg=cfg)

    assert report.algorithm == "catalog_discovery"
    assert report.sections
    assert any("Discovery Summary" in s.title for s in report.sections)

    # Formatting should not require LLM
    formatter = ReportGenerator(use_llm_interpretation=False, enable_charts=False)
    md = formatter.format_report(report, ReportFormat.MARKDOWN)
    assert "Catalog Discovery Report" in md
