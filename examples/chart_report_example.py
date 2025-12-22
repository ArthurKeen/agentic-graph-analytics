"""
Example: Generate HTML Report with Interactive Charts

Demonstrates how to create beautiful HTML reports with embedded Plotly charts.
"""

from graph_analytics_ai.ai.reporting import (
    ReportGenerator,
    HTMLReportFormatter,
    is_plotly_available
)
from datetime import datetime


def create_sample_wcc_results():
    """Create sample WCC results for demonstration."""
    # Simulate 4,534 components with realistic distribution
    results = []
    
    # Main cluster (155,131 nodes - 97.43%)
    for i in range(155131):
        results.append({
            '_key': f'Device/{i}',
            'component': 'Site/8448912'
        })
    
    # Second cluster (1,488 nodes)
    for i in range(1488):
        results.append({
            '_key': f'Device/{155131+i}',
            'component': 'AppProduct/573458'
        })
    
    # Third cluster (511 nodes)
    for i in range(511):
        results.append({
            '_key': f'Device/{156619+i}',
            'component': 'AppProduct/590112'
        })
    
    # Many small clusters (remaining ~2,000 nodes in 4,531 clusters)
    component_id = 1000
    for cluster_size in [10, 8, 5, 3, 2, 2, 2, 1, 1, 1] * 450:  # Realistic distribution
        for i in range(cluster_size):
            results.append({
                '_key': f'Device/{component_id * 10 + i}',
                'component': f'Device/{component_id}'
            })
        component_id += 1
    
    return results


def generate_sample_html_report():
    """Generate a sample HTML report with charts."""
    
    print("=" * 70)
    print("GENERATING SAMPLE HTML REPORT WITH CHARTS")
    print("=" * 70)
    print()
    
    # Check if plotly is available
    if not is_plotly_available():
        print("❌ Plotly is not installed!")
        print("Install with: pip install plotly")
        return
    
    print("✓ Plotly is available")
    print()
    
    # Create sample data
    print("Creating sample WCC results (household analysis)...")
    results = create_sample_wcc_results()
    print(f"✓ Generated {len(results):,} sample results")
    print()
    
    # Create mock execution result
    from graph_analytics_ai.ai.execution.models import ExecutionResult, AnalysisJob
    
    job = AnalysisJob(
        job_id="test-job-001",
        template_name="Household Identity Resolution",
        algorithm="wcc",
        status="completed",
        submitted_at=datetime.now(),
        execution_time_seconds=28.5,
        result_count=len(results),
        completed_at=datetime.now()
    )
    
    execution_result = ExecutionResult(
        job=job,
        results=results,
        success=True
    )
    
    # Generate report with charts
    print("Generating report with interactive charts...")
    
    # Create a mock LLM provider to avoid needing API keys for this example
    from unittest.mock import Mock
    mock_llm = Mock()
    
    generator = ReportGenerator(
        llm_provider=mock_llm,
        enable_charts=True,
        use_llm_interpretation=False
    )
    report = generator.generate_report(
        execution_result,
        context={
            "use_case": {
                "title": "Household Identity Resolution",
                "objective": "Identify distinct household clusters from device data"
            },
            "requirements": {
                "domain": "advertising technology",
                "objectives": [
                    {
                        "title": "Household Clustering",
                        "description": "Group devices into households for cross-device attribution",
                        "success_criteria": [
                            "Identify multiple distinct household clusters (not 1 giant cluster)",
                            "Enable household-level targeting and attribution"
                        ]
                    }
                ]
            },
            "schema_analysis": {
                "domain": "advertising technology",
                "complexity_score": 6.5,
                "key_entities": ["Device", "IP", "AppProduct", "Site"]
            }
        }
    )
    print(f"✓ Report generated with {len(report.insights)} insights")
    print()
    
    # Get charts from report metadata
    charts = report.metadata.get('charts', {})
    print(f"✓ Generated {len(charts)} chart types:")
    for chart_name in charts.keys():
        print(f"  - {chart_name}")
    print()
    
    # Format as HTML
    print("Formatting as interactive HTML...")
    html_formatter = HTMLReportFormatter()
    html_content = html_formatter.format_report(report, charts=charts)
    print("✓ HTML formatted")
    print()
    
    # Save to file
    output_file = "sample_household_report.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("=" * 70)
    print("✅ REPORT GENERATED SUCCESSFULLY!")
    print("=" * 70)
    print()
    print(f"📄 File: {output_file}")
    print(f"📊 Charts: {len(charts)} interactive visualizations")
    print(f"💡 Insights: {len(report.insights)}")
    print(f"🎯 Recommendations: {len(report.recommendations)}")
    print()
    print("To view the report:")
    print(f"  open {output_file}")
    print()
    print("The report includes:")
    print("  • Executive summary with key metrics")
    print("  • Interactive Plotly charts (hover, zoom, pan)")
    print("  • Component size distribution")
    print("  • Top 10 largest components")
    print("  • Connectivity overview pie chart")
    print("  • Key insights with confidence scores")
    print("  • Actionable recommendations")
    print()


if __name__ == "__main__":
    generate_sample_html_report()

