"""
Command-line interface for AI-assisted graph analytics workflow.

Provides easy access to all workflow functionality through CLI commands.
"""

import sys
from pathlib import Path
from typing import Optional

import click

from .workflow import WorkflowOrchestrator, WorkflowStatus
from .llm.factory import create_llm_provider


@click.group()
@click.version_option(version="3.0.0")
def cli():
    """
    Graph Analytics AI - AI-Assisted Graph Analytics Workflow

    Automate your graph analytics from requirements to insights.
    """
    pass


@cli.command("run-workflow")
@click.option(
    "--requirements",
    "-r",
    multiple=True,
    required=True,
    help="Path to business requirements document(s). Can be specified multiple times.",
)
@click.option(
    "--database-endpoint",
    "-e",
    required=True,
    help="ArangoDB endpoint URL (e.g., http://localhost:8529)",
)
@click.option(
    "--database-name",
    "-d",
    required=True,
    help="Name of the ArangoDB database to analyze",
)
@click.option(
    "--database-username",
    "-u",
    default="root",
    help="Database username (default: root)",
)
@click.option("--database-password", "-p", default="", help="Database password")
@click.option(
    "--product-name",
    default="Graph Analytics AI Project",
    help="Product/project name for PRD",
)
@click.option(
    "--output-dir",
    "-o",
    default="./workflow_output",
    help="Output directory for generated files",
)
@click.option("--resume", is_flag=True, help="Resume from last checkpoint")
@click.option("--no-checkpoints", is_flag=True, help="Disable checkpoint saving")
def run_workflow(
    requirements: tuple,
    database_endpoint: str,
    database_name: str,
    database_username: str,
    database_password: str,
    product_name: str,
    output_dir: str,
    resume: bool,
    no_checkpoints: bool,
):
    """
    Run the complete AI-assisted workflow.

    This command orchestrates the entire process:
    1. Parse business requirement documents
    2. Extract requirements with LLM
    3. Extract graph schema from ArangoDB
    4. Analyze schema with LLM
    5. Generate Product Requirements Document
    6. Generate graph analytics use cases
    7. Save all outputs

    Example:
        gaai run-workflow -r requirements.pdf -e http://localhost:8529 -d my_graph -p password
    """
    click.echo("🚀 Starting AI-Assisted Graph Analytics Workflow...")
    click.echo("")

    # Validate requirements files
    req_paths = list(requirements)
    for req_path in req_paths:
        if not Path(req_path).exists():
            click.echo(f"❌ Error: Requirements file not found: {req_path}", err=True)
            sys.exit(1)

    click.echo(f"📄 Requirements: {len(req_paths)} document(s)")
    click.echo(f"🗄️  Database: {database_name} @ {database_endpoint}")
    click.echo(f"📁 Output: {output_dir}")
    click.echo("")

    try:
        # Create orchestrator
        orchestrator = WorkflowOrchestrator(
            output_dir=output_dir, enable_checkpoints=not no_checkpoints
        )

        # Run workflow
        with click.progressbar(
            length=7, label="Executing workflow", show_eta=True
        ) as bar:

            def update_progress():
                progress = orchestrator.get_progress()
                bar.update(progress["completed_steps"] - bar.pos)

            result = orchestrator.run_complete_workflow(
                business_requirements=req_paths,
                database_endpoint=database_endpoint,
                database_name=database_name,
                database_username=database_username,
                database_password=database_password,
                product_name=product_name,
                resume_from_checkpoint=resume,
            )

            bar.update(7 - bar.pos)  # Complete the bar

        click.echo("")

        if result.status == WorkflowStatus.COMPLETED:
            click.echo("✅ Workflow completed successfully!")
            click.echo("")
            click.echo("📦 Generated Artifacts:")
            if result.prd_path:
                click.echo(f"   • PRD: {result.prd_path}")
            if result.use_cases_path:
                click.echo(f"   • Use Cases: {result.use_cases_path}")
            if result.schema_path:
                click.echo(f"   • Schema Analysis: {result.schema_path}")
            if result.requirements_path:
                click.echo(f"   • Requirements: {result.requirements_path}")
            click.echo("")
            click.echo(f"⏱️  Total time: {result.total_duration_seconds:.2f} seconds")
        else:
            click.echo(f"❌ Workflow failed: {result.error_message}", err=True)
            click.echo(f"   Completed steps: {', '.join(result.completed_steps)}")
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command("analyze-schema")
@click.option("--database-endpoint", "-e", required=True, help="ArangoDB endpoint URL")
@click.option("--database-name", "-d", required=True, help="Database name")
@click.option("--database-username", "-u", default="root", help="Database username")
@click.option("--database-password", "-p", default="", help="Database password")
@click.option("--output", "-o", help="Output file for schema analysis report")
def analyze_schema(
    database_endpoint: str,
    database_name: str,
    database_username: str,
    database_password: str,
    output: Optional[str],
):
    """
    Analyze graph database schema.

    Extracts schema from ArangoDB and generates an analysis report with LLM insights.

    Example:
        gaai analyze-schema -e http://localhost:8529 -d my_graph -p password -o schema.md
    """
    click.echo("🔍 Analyzing graph schema...")

    try:
        from .schema.extractor import create_extractor
        from .schema.analyzer import SchemaAnalyzer

        # Extract schema
        click.echo("Extracting schema from database...")
        extractor = create_extractor(
            endpoint=database_endpoint,
            database=database_name,
            username=database_username,
            password=database_password,
        )
        schema = extractor.extract()

        click.echo(f"✓ Found {len(schema.vertex_collections)} vertex collections")
        click.echo(f"✓ Found {len(schema.edge_collections)} edge collections")
        click.echo(f"✓ Total documents: {schema.total_documents:,}")
        click.echo("")

        # Analyze with LLM
        click.echo("Analyzing with LLM...")
        provider = create_llm_provider()
        analyzer = SchemaAnalyzer(provider)
        analysis = analyzer.analyze(schema)

        click.echo(f"✓ Domain identified: {analysis.domain}")
        click.echo(f"✓ Complexity score: {analysis.complexity_score:.1f}/10")
        click.echo("")

        # Generate report
        report = analyzer.generate_report(analysis)

        if output:
            Path(output).write_text(report)
            click.echo(f"📄 Report saved to: {output}")
        else:
            click.echo(report)

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command("parse-requirements")
@click.argument("documents", nargs=-1, required=True)
@click.option("--output", "-o", help="Output file for requirements summary")
def parse_requirements(documents: tuple, output: Optional[str]):
    """
    Parse and extract requirements from documents.

    Supports: TXT, MD, PDF, DOCX, HTML

    Example:
        gaai parse-requirements requirements.pdf scope.docx -o requirements.md
    """
    click.echo(f"📚 Parsing {len(documents)} document(s)...")

    try:
        from .documents.parser import parse_documents
        from .documents.extractor import RequirementsExtractor

        # Parse documents
        doc_paths = list(documents)
        parsed_docs = parse_documents(doc_paths)

        click.echo(f"✓ Parsed {len(parsed_docs)} documents")
        total_words = sum(doc.word_count for doc in parsed_docs)
        click.echo(f"✓ Total words: {total_words:,}")
        click.echo("")

        # Extract requirements
        click.echo("Extracting requirements with LLM...")
        provider = create_llm_provider()
        extractor = RequirementsExtractor(provider)
        extracted = extractor.extract(parsed_docs)

        click.echo(f"✓ Domain: {extracted.domain}")
        click.echo(f"✓ Total requirements: {extracted.total_requirements}")
        click.echo(f"✓ Critical: {len(extracted.critical_requirements)}")
        click.echo(f"✓ Objectives: {len(extracted.objectives)}")
        click.echo(f"✓ Stakeholders: {len(extracted.stakeholders)}")
        click.echo("")

        # Show critical requirements
        if extracted.critical_requirements:
            click.echo("🔴 Critical Requirements:")
            for req in extracted.critical_requirements[:5]:
                click.echo(f"   • {req.id}: {req.text[:80]}...")

        if output:
            from .workflow.steps import WorkflowSteps

            steps = WorkflowSteps(provider)
            summary = steps._format_requirements_summary(extracted)
            Path(output).write_text(summary)
            click.echo(f"\n📄 Summary saved to: {output}")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command("status")
@click.option(
    "--output-dir", "-o", default="./workflow_output", help="Workflow output directory"
)
def status(output_dir: str):
    """
    Check status of workflow execution.

    Shows progress and checkpoint information.

    Example:
        gaai status -o ./workflow_output
    """
    try:
        from .workflow.state import WorkflowState

        checkpoint_files = list(Path(output_dir).glob("checkpoint_*.json"))

        if not checkpoint_files:
            click.echo("No workflow checkpoints found.")
            return

        # Get most recent checkpoint
        latest_checkpoint = max(checkpoint_files, key=lambda p: p.stat().st_mtime)
        state = WorkflowState.load_checkpoint(latest_checkpoint)

        click.echo("📊 Workflow Status")
        click.echo(f"   ID: {state.workflow_id}")
        click.echo(f"   Status: {state.status.value}")
        click.echo(f"   Created: {state.created_at}")
        click.echo(f"   Updated: {state.updated_at}")
        click.echo("")

        if state.current_step:
            click.echo(f"   Current Step: {state.current_step.value}")

        click.echo(f"   Completed Steps: {len(state.completed_steps)}")
        for step in state.completed_steps:
            click.echo(f"      ✓ {step.value}")

        if state.error_message:
            click.echo(f"\n   ❌ Error: {state.error_message}")

    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command("version")
def version():
    """Show version information."""
    click.echo("Graph Analytics AI v2.0.0")
    click.echo("Phase 6: Complete Workflow Orchestration")
    click.echo("")
    click.echo("Features:")
    click.echo("  • AI-assisted workflow automation")
    click.echo("  • Schema extraction and analysis")
    click.echo("  • Requirements extraction from documents")
    click.echo("  • PRD and use case generation")
    click.echo("  • State management and checkpointing")


def main():
    """Entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
