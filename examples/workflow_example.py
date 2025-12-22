"""
Example: Complete AI-Assisted Workflow

This example demonstrates the complete end-to-end workflow orchestration
for AI-assisted graph analytics.
"""

import os
from pathlib import Path

from graph_analytics_ai.ai.workflow import WorkflowOrchestrator, WorkflowStatus
from graph_analytics_ai.ai.llm import create_llm_provider


def example_complete_workflow():
    """Run complete workflow from requirements to insights."""
    print("=" * 60)
    print("Example: Complete AI-Assisted Workflow")
    print("=" * 60)
    print()
    
    # Configuration
    requirements_files = [
        "requirements.pdf",  # Replace with your actual files
        "business_case.docx"
    ]
    database_endpoint = "http://localhost:8529"
    database_name = "my_graph"
    database_password = os.getenv("ARANGO_PASSWORD", "")
    output_dir = "./workflow_output"
    
    print("Configuration:")
    print(f"  Requirements: {len(requirements_files)} files")
    print(f"  Database: {database_name} @ {database_endpoint}")
    print(f"  Output: {output_dir}")
    print()
    
    # Create orchestrator
    print("Creating workflow orchestrator...")
    orchestrator = WorkflowOrchestrator(
        output_dir=output_dir,
        enable_checkpoints=True,
        max_retries=3
    )
    print("✓ Orchestrator ready")
    print()
    
    # Run workflow
    print("Starting workflow execution...")
    print("This may take several minutes depending on:")
    print("  - Number of requirement documents")
    print("  - Database size and complexity")
    print("  - LLM response times")
    print()
    
    try:
        result = orchestrator.run_complete_workflow(
            business_requirements=requirements_files,
            database_endpoint=database_endpoint,
            database_name=database_name,
            database_password=database_password,
            product_name="My Analytics Project"
        )
        
        # Display results
        print()
        print("=" * 60)
        if result.status == WorkflowStatus.COMPLETED:
            print("✓ Workflow completed successfully!")
            print()
            print("Generated Artifacts:")
            print(f"  • PRD: {result.prd_path}")
            print(f"  • Use Cases: {result.use_cases_path}")
            print(f"  • Schema Analysis: {result.schema_path}")
            print(f"  • Requirements: {result.requirements_path}")
            print()
            print(f"Execution time: {result.total_duration_seconds:.2f} seconds")
            print(f"Completed steps: {len(result.completed_steps)}/7")
        else:
            print("✗ Workflow failed!")
            print(f"  Error: {result.error_message}")
            print(f"  Completed steps: {', '.join(result.completed_steps)}")
            print()
            print("You can resume the workflow with resume_from_checkpoint=True")
        print("=" * 60)
    
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        raise


def example_with_progress_monitoring():
    """Run workflow with progress monitoring."""
    print("=" * 60)
    print("Example: Workflow with Progress Monitoring")
    print("=" * 60)
    print()
    
    orchestrator = WorkflowOrchestrator(
        output_dir="./workflow_output",
        enable_checkpoints=True
    )
    
    # Monitor progress in background
    import time
    from threading import Thread
    
    def monitor():
        """Monitor and display progress."""
        while True:
            if not orchestrator.state:
                time.sleep(1)
                continue
            
            progress = orchestrator.get_progress()
            if progress['status'] == 'not_started':
                break
            
            print(f"\rProgress: {progress['progress'] * 100:.1f}% "
                  f"[{progress['completed_steps']}/{progress['total_steps']} steps] "
                  f"Current: {progress['current_step'] or 'None'}", 
                  end='', flush=True)
            
            if progress['status'] in ('completed', 'failed'):
                break
            
            time.sleep(2)
    
    # Start monitoring
    monitor_thread = Thread(target=monitor, daemon=True)
    monitor_thread.start()
    
    # Run workflow
    result = orchestrator.run_complete_workflow(
        business_requirements=["requirements.pdf"],
        database_endpoint="http://localhost:8529",
        database_name="my_graph",
        database_password=""
    )
    
    print()  # New line after progress
    print()
    print(f"Status: {result.status.value}")


def example_resume_from_checkpoint():
    """Resume a failed workflow from checkpoint."""
    print("=" * 60)
    print("Example: Resume from Checkpoint")
    print("=" * 60)
    print()
    
    output_dir = "./workflow_output"
    
    # Check for existing checkpoint
    checkpoint_files = list(Path(output_dir).glob("checkpoint_*.json"))
    
    if not checkpoint_files:
        print("No checkpoint found. Run a workflow first.")
        return
    
    print(f"Found {len(checkpoint_files)} checkpoint(s)")
    print()
    
    # Create orchestrator
    orchestrator = WorkflowOrchestrator(
        output_dir=output_dir,
        enable_checkpoints=True
    )
    
    # Resume workflow
    print("Resuming workflow from last checkpoint...")
    result = orchestrator.run_complete_workflow(
        business_requirements=["requirements.pdf"],
        database_endpoint="http://localhost:8529",
        database_name="my_graph",
        database_password="",
        resume_from_checkpoint=True
    )
    
    print()
    print(f"Result: {result.status.value}")
    if result.status == WorkflowStatus.COMPLETED:
        print(f"Artifacts: {result.output_dir}")


def example_individual_steps():
    """Execute individual workflow steps."""
    print("=" * 60)
    print("Example: Individual Step Execution")
    print("=" * 60)
    print()
    
    from graph_analytics_ai.ai.workflow import WorkflowSteps
    
    provider = create_llm_provider()
    steps = WorkflowSteps(provider)
    
    # Step 1: Parse documents
    print("Step 1: Parsing documents...")
    documents = steps.parse_documents(["requirements.txt"])
    print(f"✓ Parsed {len(documents)} documents")
    print()
    
    # Step 2: Extract requirements
    print("Step 2: Extracting requirements...")
    requirements = steps.extract_requirements(documents)
    print(f"✓ Extracted {requirements.total_requirements} requirements")
    print(f"  Domain: {requirements.domain}")
    print(f"  Critical: {len(requirements.critical_requirements)}")
    print()
    
    # Step 3: Extract schema
    print("Step 3: Extracting schema...")
    schema = steps.extract_schema(
        database_endpoint="http://localhost:8529",
        database_name="my_graph",
        password=""
    )
    print("✓ Extracted schema")
    print(f"  Vertices: {len(schema.vertex_collections)}")
    print(f"  Edges: {len(schema.edge_collections)}")
    print()
    
    # Step 4: Analyze schema
    print("Step 4: Analyzing schema...")
    analysis = steps.analyze_schema(schema)
    print("✓ Schema analyzed")
    print(f"  Domain: {analysis.domain}")
    print(f"  Complexity: {analysis.complexity_score}/10")
    print()
    
    # Step 5: Generate PRD
    print("Step 5: Generating PRD...")
    prd = steps.generate_prd(
        extracted_requirements=requirements,
        schema=schema,
        schema_analysis=analysis,
        product_name="My Project"
    )
    print(f"✓ PRD generated ({len(prd)} characters)")
    print()
    
    # Step 6: Generate use cases
    print("Step 6: Generating use cases...")
    use_cases = steps.generate_use_cases(
        extracted_requirements=requirements,
        schema_analysis=analysis
    )
    print(f"✓ Generated {len(use_cases)} use cases")
    print()
    
    # Step 7: Save outputs
    print("Step 7: Saving outputs...")
    saved_files = steps.save_outputs(
        output_dir=Path("./output"),
        prd_content=prd,
        use_cases=use_cases,
        schema=schema,
        schema_analysis=analysis,
        extracted_requirements=requirements
    )
    print(f"✓ Saved {len(saved_files)} files:")
    for output_type, path in saved_files.items():
        print(f"  • {output_type}: {path}")


def example_error_handling():
    """Demonstrate error handling and recovery."""
    print("=" * 60)
    print("Example: Error Handling")
    print("=" * 60)
    print()
    
    orchestrator = WorkflowOrchestrator(
        output_dir="./workflow_output",
        enable_checkpoints=True,
        max_retries=2
    )
    
    try:
        result = orchestrator.run_complete_workflow(
            business_requirements=["nonexistent.pdf"],  # This will fail
            database_endpoint="http://localhost:8529",
            database_name="my_graph",
            database_password=""
        )
        
        if result.status == WorkflowStatus.FAILED:
            print("Workflow failed as expected")
            print(f"Error: {result.error_message}")
            print(f"Completed {len(result.completed_steps)} steps before failure")
            print()
            
            # Check state for details
            state = orchestrator.get_state()
            print("Step Details:")
            for step_name, step_result in state.step_results.items():
                status = step_result.status.value
                print(f"  • {step_name}: {status}")
                if step_result.error_message:
                    print(f"    Error: {step_result.error_message}")
    
    except Exception as e:
        print(f"Exception caught: {e}")
        print("This is expected behavior for this example")


if __name__ == "__main__":
    # Run the example
    # Uncomment the example you want to run:
    
    # example_complete_workflow()
    # example_with_progress_monitoring()
    # example_resume_from_checkpoint()
    # example_individual_steps()
    # example_error_handling()
    
    print("Uncomment an example in the main block to run it")

