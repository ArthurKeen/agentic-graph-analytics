#!/usr/bin/env python3
"""
Run the complete agentic workflow for Premion use cases.

This script will:
1. Extract and analyze the database schema
2. Parse the business use cases from consumer_media_use_cases.md
3. Generate GAE analysis templates
4. Execute the templates
5. Generate comprehensive reports
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from graph_analytics_ai.ai.workflow.orchestrator import WorkflowOrchestrator

# Load environment variables
load_dotenv()

def main():
    print("\n" + "="*70)
    print("PREMION GRAPH ANALYTICS - AGENTIC WORKFLOW")
    print("="*70)
    
    # Configuration
    use_case_file = "consumer_media_use_cases.md"
    database_name = "sharded_premion_graph"
    graph_name = "PremionIdentityGraph"
    output_dir = "./premion_analysis_output"
    
    # Verify use case file exists
    if not Path(use_case_file).exists():
        print(f"\n✗ Error: Use case file '{use_case_file}' not found")
        print("  Please ensure the file exists in the current directory")
        return 1
    
    print(f"\n📋 Use Cases: {use_case_file}")
    print(f"🗄️  Database: {database_name}")
    print(f"🕸️  Graph: {graph_name}")
    print(f"📁 Output: {output_dir}")
    
    # Initialize orchestrator
    print(f"\n{'='*70}")
    print("INITIALIZING WORKFLOW ORCHESTRATOR")
    print("="*70)
    
    try:
        orchestrator = WorkflowOrchestrator(
            output_dir=output_dir,
            enable_checkpoints=True
        )
        print("✓ Orchestrator initialized")
    except Exception as e:
        print(f"✗ Failed to initialize orchestrator: {e}")
        return 1
    
    # Run workflow
    print(f"\n{'='*70}")
    print("RUNNING AGENTIC WORKFLOW")
    print("="*70)
    print("\nThis will:")
    print("  1. Extract and analyze database schema")
    print("  2. Parse business use cases")
    print("  3. Generate GAE templates for:")
    print("     - Household Identity Resolution (WCC)")
    print("     - Anomaly & Fraud Detection (Degree Centrality)")
    print("     - Behavioral Segmentation (Label Propagation)")
    print("     - Cross-Device Attribution (Shortest Path)")
    print("     - Content Popularity (PageRank)")
    print("  4. Execute graph analytics")
    print("  5. Generate comprehensive reports")
    print(f"\n{'='*70}\n")
    
    try:
        # Get database credentials from environment
        db_endpoint = os.getenv("ARANGO_ENDPOINT", "http://localhost:8529")
        db_user = os.getenv("ARANGO_USER", "root")
        db_password = os.getenv("ARANGO_PASSWORD", "")
        
        result = orchestrator.run_complete_workflow(
            business_requirements=[use_case_file],
            database_endpoint=db_endpoint,
            database_name=database_name,
            database_username=db_user,
            database_password=db_password,
            product_name="Premion Identity Graph Analytics"
        )
        
        # Display results
        print(f"\n{'='*70}")
        print("WORKFLOW COMPLETED")
        print("="*70)
        
        if result.status == 'completed':
            print("\n✓ Workflow completed successfully!")
            print(f"\n📊 Workflow ID: {result.workflow_id}")
            print(f"📁 Output Directory: {result.output_dir}")
            print("\nGenerated Artifacts:")
            
            if result.requirements_path:
                print(f"  ✓ Requirements: {result.requirements_path}")
            if result.schema_path:
                print(f"  ✓ Schema Analysis: {result.schema_path}")
            if result.use_cases_path:
                print(f"  ✓ Use Cases: {result.use_cases_path}")
            if result.prd_path:
                print(f"  ✓ PRD: {result.prd_path}")
            
            print(f"\nCompleted Steps: {', '.join(result.completed_steps or [])}")
            
            if result.total_duration_seconds:
                print(f"Total Duration: {result.total_duration_seconds:.2f} seconds")
            
            print("\n📄 Review generated artifacts in:")
            print(f"   {result.output_dir}/")
            
            return 0
        else:
            print("\n✗ Workflow failed or incomplete")
            print(f"  Status: {result.status}")
            if result.error_message:
                print(f"  Error: {result.error_message}")
            if result.completed_steps:
                print(f"  Completed: {', '.join(result.completed_steps)}")
            return 1
            
    except Exception as e:
        print(f"\n✗ Workflow execution failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

