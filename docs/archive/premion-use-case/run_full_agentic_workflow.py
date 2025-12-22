#!/usr/bin/env python3
"""
Run the FULL agentic workflow using AgenticWorkflowRunner.

This is the complete multi-agent system that:
1. Analyzes your schema
2. Extracts requirements from use cases  
3. Generates templates
4. EXECUTES templates on GAE
5. Generates reports

Pure library usage - no custom code!
"""
import sys
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv()

from graph_analytics_ai.ai.agents.runner import AgenticWorkflowRunner
from graph_analytics_ai.db_connection import get_db_connection

def main():
    print("\n" + "="*70)
    print("PREMION - FULL AGENTIC WORKFLOW")
    print("Multi-Agent System with Template Generation & Execution")
    print("="*70)
    
    # Configuration
    use_case_file = "consumer_media_use_cases.md"
    graph_name = "PremionIdentityGraph"
    output_file = "premion_agentic_state.json"
    max_executions = 3  # Limit to first 3 templates for testing
    
    # Verify use case file
    if not Path(use_case_file).exists():
        print(f"\n✗ Error: Use case file '{use_case_file}' not found")
        return 1
    
    # Read use case document
    with open(use_case_file) as f:
        doc_content = f.read()
    
    print("\n📋 Configuration:")
    print(f"   Use Cases: {use_case_file} ({len(doc_content)} chars)")
    print(f"   Graph: {graph_name}")
    print(f"   Max Executions: {max_executions}")
    print(f"   Output: {output_file}")
    
    # Get database connection
    print(f"\n{'='*70}")
    print("CONNECTING TO DATABASE")
    print("="*70)
    
    try:
        db = get_db_connection()
        print(f"✓ Connected to database: {db.name}")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return 1
    
    # Initialize runner
    print(f"\n{'='*70}")
    print("INITIALIZING AGENTIC WORKFLOW RUNNER")
    print("="*70)
    
    try:
        runner = AgenticWorkflowRunner(
            db_connection=db,
            graph_name=graph_name
        )
        print("✓ Runner initialized")
        print(f"   LLM Provider: {runner.llm_provider.__class__.__name__}")
        print(f"   Agents: {len(runner.agents)}")
        print("\n🤖 Agent Team:")
        for name, agent in runner.agents.items():
            print(f"   - {name}: {agent.__class__.__name__}")
        
    except Exception as e:
        print(f"✗ Failed to initialize runner: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Prepare input
    input_documents = [{
        "path": use_case_file,
        "content": doc_content,
        "type": "text/markdown"
    }]
    
    database_config = {
        "endpoint": os.getenv("ARANGO_ENDPOINT"),
        "database": os.getenv("ARANGO_DATABASE"),
        "username": os.getenv("ARANGO_USER", "root"),
        "password": os.getenv("ARANGO_PASSWORD")
    }
    
    # Run workflow
    print(f"\n{'='*70}")
    print("RUNNING MULTI-AGENT WORKFLOW")
    print("="*70)
    print("\nAgents will collaborate to:")
    print("  1. 🔍 Schema Agent: Analyze database structure")
    print("  2. 📋 Requirements Agent: Extract business requirements")
    print("  3. 🎯 Use Case Agent: Generate use cases")
    print("  4. 🔧 Template Agent: Generate GAE templates")
    print("  5. ⚡ Execution Agent: Run templates on GAE")
    print("  6. 📊 Reporting Agent: Generate analysis reports")
    print(f"\n{'='*70}\n")
    
    try:
        # Run the complete agentic workflow
        final_state = runner.run(
            input_documents=input_documents,
            database_config=database_config,
            max_executions=max_executions
        )
        
        # Export state
        print("\n💾 Exporting workflow state...")
        runner.export_state(final_state, output_file)
        
        # Save reports to files
        print("\n📄 Saving reports...")
        reports_dir = Path("premion_reports")
        reports_dir.mkdir(exist_ok=True)
        
        saved_reports = []
        for i, report in enumerate(final_state.reports, 1):
            # Generate filename from report title
            filename = report.title.lower().replace(" ", "_").replace(":", "").replace("-", "_")
            filename = f"{i}_{filename}.md"
            report_path = reports_dir / filename
            
            # Convert report to markdown
            report_md = f"# {report.title}\n\n"
            report_md += f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
            
            if hasattr(report, 'executive_summary') and report.executive_summary:
                report_md += f"## Executive Summary\n\n{report.executive_summary}\n\n"
            
            # Add insights
            if report.insights:
                report_md += f"## Key Insights ({len(report.insights)})\n\n"
                for j, insight in enumerate(report.insights, 1):
                    report_md += f"### {j}. {insight.title}\n\n"
                    report_md += f"**Type:** {insight.insight_type}\n"
                    if hasattr(insight, 'confidence') and insight.confidence:
                        report_md += f"**Confidence:** {insight.confidence}%\n"
                    report_md += f"\n{insight.description}\n\n"
                    if hasattr(insight, 'impact') and insight.impact:
                        report_md += f"**Impact:** {insight.impact}\n\n"
            
            # Add recommendations
            if report.recommendations:
                report_md += f"## Recommendations ({len(report.recommendations)})\n\n"
                for j, rec in enumerate(report.recommendations, 1):
                    report_md += f"### {j}. {rec.title}\n\n"
                    if hasattr(rec, 'priority') and rec.priority:
                        report_md += f"**Priority:** {rec.priority}\n"
                    report_md += f"\n{rec.description}\n\n"
                    if hasattr(rec, 'expected_impact') and rec.expected_impact:
                        report_md += f"**Expected Impact:** {rec.expected_impact}\n\n"
            
            # Save to file
            report_path.write_text(report_md)
            saved_reports.append(str(report_path))
            print(f"   ✓ Saved: {report_path}")
        
        # Additional summary
        print(f"\n{'='*70}")
        print("DETAILED RESULTS")
        print("="*70)
        
        if final_state.use_cases:
            print(f"\n📋 Use Cases ({len(final_state.use_cases)}):")
            for uc in final_state.use_cases[:5]:
                # UseCase may have 'title' or 'name' attribute
                name = getattr(uc, 'title', getattr(uc, 'name', 'Unknown'))
                use_type = getattr(uc, 'use_case_type', 'unknown')
                print(f"   - {name}: {use_type}")
        
        if final_state.templates:
            print(f"\n🔧 Templates ({len(final_state.templates)}):")
            for t in final_state.templates[:5]:
                name = getattr(t, 'name', getattr(t, 'title', 'Unknown'))
                if hasattr(t, 'algorithm'):
                    algo = t.algorithm.algorithm_type.value if hasattr(t.algorithm, 'algorithm_type') else str(t.algorithm)[:30]
                else:
                    algo = 'unknown'
                print(f"   - {name}: {algo}")
        
        if final_state.execution_results:
            print(f"\n⚡ Execution Results ({len(final_state.execution_results)}):")
            for result in final_state.execution_results:
                status = "✓" if result.success else "✗"
                print(f"   {status} Job {result.job.job_id}: {result.job.status.value}")
        
        if final_state.reports:
            print(f"\n📊 Reports ({len(final_state.reports)}):")
            for report in final_state.reports:
                print(f"   - {report.title}")
                print(f"     Insights: {len(report.insights)}, Recommendations: {len(report.recommendations)}")
        
        if final_state.errors:
            print(f"\n⚠️  Errors ({len(final_state.errors)}):")
            for error in final_state.errors[:5]:
                print(f"   - {error.get('agent', 'unknown')}: {error.get('error', 'unknown')[:100]}")
        
        print(f"\n{'='*70}")
        print("✅ WORKFLOW COMPLETE!")
        print("="*70)
        print("\n📁 Output Files:")
        print(f"   State: {output_file}")
        if saved_reports:
            print(f"   Reports: premion_reports/ ({len(saved_reports)} files)")
            for rpt in saved_reports:
                print(f"      - {Path(rpt).name}")
        print("\n💡 View reports: cat premion_reports/*.md")
        print(f"   View state: python -m json.tool {output_file} | less")
        
        return 0
        
    except Exception as e:
        print(f"\n{'='*70}")
        print("✗ WORKFLOW FAILED")
        print("="*70)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

