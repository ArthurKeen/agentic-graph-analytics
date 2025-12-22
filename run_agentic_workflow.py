#!/usr/bin/env python3
"""
Run the complete agentic workflow using the library's orchestrator.

This example demonstrates how to use the graph_analytics_ai library:
- WorkflowOrchestrator for end-to-end automation
- LLM-powered schema analysis
- Automatic template generation from use cases
- Execution and reporting

This is a generic example - for customer-specific implementations,
create a separate project that imports this library.
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

from graph_analytics_ai.ai.workflow.orchestrator import WorkflowOrchestrator

def main():
    print("\n" + "="*70)
    print("GRAPH ANALYTICS AI - WORKFLOW EXAMPLE")
    print("="*70)
    
    # Configuration - using example e-commerce use case
    use_case_file = "examples/use_case_document.md"
    database_name = os.getenv("ARANGO_DATABASE", "graph-analytics-ai")
    output_dir = "./workflow_output"
    
    # Verify use case file
    if not Path(use_case_file).exists():
        print(f"\n✗ Error: Use case file '{use_case_file}' not found")
        return 1
    
    # Get database credentials from environment
    db_endpoint = os.getenv("ARANGO_ENDPOINT")
    db_user = os.getenv("ARANGO_USER", "root")
    db_password = os.getenv("ARANGO_PASSWORD")
    
    if not db_endpoint or not db_password:
        print("\n✗ Error: Database credentials not found in .env")
        print("   Required: ARANGO_ENDPOINT, ARANGO_PASSWORD")
        return 1
    
    print("\n📋 Configuration:")
    print(f"   Use Cases: {use_case_file}")
    print(f"   Database: {database_name}")
    print(f"   Endpoint: {db_endpoint}")
    print(f"   Output: {output_dir}")
    
    print(f"\n{'='*70}")
    print("INITIALIZING AGENTIC WORKFLOW ORCHESTRATOR")
    print("="*70)
    
    try:
        # Initialize orchestrator with LLM provider
        orchestrator = WorkflowOrchestrator(
            output_dir=output_dir,
            enable_checkpoints=True,
            max_retries=3
        )
        print("✓ Orchestrator initialized")
        print(f"   LLM Provider: {orchestrator.llm_provider.__class__.__name__}")
        
    except Exception as e:
        print(f"✗ Failed to initialize orchestrator: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print(f"\n{'='*70}")
    print("RUNNING COMPLETE WORKFLOW")
    print("="*70)
    print("\nThe workflow will:")
    print("  1. Parse business use cases (LLM)")
    print("  2. Extract requirements (LLM)")
    print("  3. Extract database schema")
    print("  4. Analyze schema (LLM)")
    print("  5. Generate Product Requirements Document (LLM)")
    print("  6. Generate use cases from requirements (LLM)")
    print("  7. Save all outputs")
    print(f"\n{'='*70}\n")
    
    try:
        # Run the complete workflow
        result = orchestrator.run_complete_workflow(
            business_requirements=[use_case_file],
            database_endpoint=db_endpoint,
            database_name=database_name,
            database_username=db_user,
            database_password=db_password,
            product_name="Graph Analytics AI - Example Workflow",
            resume_from_checkpoint=False
        )
        
        # Display results
        print(f"\n{'='*70}")
        print("WORKFLOW RESULTS")
        print("="*70)
        
        print(f"\n📊 Status: {result.status}")
        print(f"   Workflow ID: {result.workflow_id}")
        print(f"   Output Directory: {result.output_dir}")
        
        if result.completed_steps:
            print(f"\n✓ Completed Steps ({len(result.completed_steps)}):")
            for step in result.completed_steps:
                print(f"   - {step}")
        
        if result.total_duration_seconds:
            print(f"\n⏱️  Total Duration: {result.total_duration_seconds:.1f} seconds")
        
        # Show generated artifacts
        print("\n📁 Generated Artifacts:")
        artifacts = []
        if result.requirements_path:
            artifacts.append(("Requirements", result.requirements_path))
        if result.schema_path:
            artifacts.append(("Schema Analysis", result.schema_path))
        if result.use_cases_path:
            artifacts.append(("Use Cases", result.use_cases_path))
        if result.prd_path:
            artifacts.append(("PRD", result.prd_path))
        
        for name, path in artifacts:
            print(f"   ✓ {name}: {path}")
        
        # Check for errors
        if result.error_message:
            print("\n⚠️  Errors Encountered:")
            print(f"   {result.error_message}")
        
        # Success determination
        if result.status.value == 'completed':
            print(f"\n{'='*70}")
            print("✅ WORKFLOW COMPLETED SUCCESSFULLY!")
            print("="*70)
            print("\nNext Steps:")
            print(f"  1. Review generated artifacts in: {output_dir}/")
            print("  2. Templates will be in use cases output")
            print("  3. Use AnalysisExecutor to run the templates on GAE")
            return 0
        else:
            print(f"\n{'='*70}")
            print("⚠️  WORKFLOW INCOMPLETE")
            print("="*70)
            return 1
            
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

