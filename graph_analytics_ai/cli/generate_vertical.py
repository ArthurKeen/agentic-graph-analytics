"""
CLI command to generate custom industry verticals from business requirements.

Usage:
    python -m graph_analytics_ai.cli.generate_vertical \
        --input docs/business_requirements.md \
        --graph-name my_graph \
        --output .graph-analytics/industry_vertical.json
"""

import argparse
import asyncio
import sys
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


async def generate_vertical_async(args):
    """Generate custom industry vertical asynchronously."""
    from graph_analytics_ai.ai.agents.industry_vertical import IndustryVerticalAgent
    from graph_analytics_ai.ai.reporting.vertical_schema import validate_vertical_schema

    # Read input files
    logger.info(f"Reading business requirements from: {args.input}")
    if not Path(args.input).exists():
        logger.error(f"Input file not found: {args.input}")
        return 1

    business_requirements = Path(args.input).read_text()

    # Read optional domain description
    domain_description = None
    if args.domain_description:
        if not Path(args.domain_description).exists():
            logger.error(
                f"Domain description file not found: {args.domain_description}"
            )
            return 1
        domain_description = Path(args.domain_description).read_text()
        logger.info(f"Read domain description from: {args.domain_description}")

    # Initialize agent
    logger.info("Initializing IndustryVerticalAgent...")
    agent = IndustryVerticalAgent()

    # Generate vertical
    logger.info("")
    logger.info("=" * 70)
    logger.info("GENERATING CUSTOM INDUSTRY VERTICAL")
    logger.info("=" * 70)
    logger.info("")

    try:
        vertical = await agent.generate_vertical(
            business_requirements=business_requirements,
            graph_name=args.graph_name,
            domain_description=domain_description,
            base_vertical=args.base_vertical,
        )
    except Exception as e:
        logger.error(f"Failed to generate vertical: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1

    # Validate the generated vertical
    if args.validate:
        logger.info("")
        logger.info("Validating generated vertical...")
        is_valid, errors = validate_vertical_schema(vertical)
        if not is_valid:
            logger.error("Validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            if not args.force:
                logger.error("Use --force to save anyway")
                return 1
            logger.warning("Saving despite validation errors (--force)")
        else:
            logger.info("✓ Validation passed")

    # Display summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("GENERATED VERTICAL SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Name: {vertical['metadata']['display_name']}")
    logger.info(f"Key: {vertical['metadata']['name']}")
    logger.info(f"Version: {vertical['metadata']['version']}")
    logger.info(f"Generated: {vertical['metadata']['generated_at']}")
    logger.info("")
    logger.info(
        f"Node Types: {len(vertical['domain_context']['key_entities']['nodes'])}"
    )
    logger.info(
        f"Edge Types: {len(vertical['domain_context']['key_entities']['edges'])}"
    )
    logger.info(
        f"Key Metrics: {len(vertical['domain_context'].get('key_metrics', []))}"
    )
    logger.info("")
    logger.info(f"Prompt Length: {len(vertical['analysis_prompt'])} characters")
    logger.info(f"WCC Patterns: {len(vertical['pattern_definitions'].get('wcc', []))}")
    logger.info(
        f"PageRank Patterns: {len(vertical['pattern_definitions'].get('pagerank', []))}"
    )
    logger.info("=" * 70)
    logger.info("")

    # Save to file
    output_path = Path(args.output)
    logger.info(f"Saving to: {output_path}")

    await agent.save_vertical(vertical, output_path)

    logger.info("")
    logger.info("✓ Custom vertical generated successfully!")
    logger.info("")
    logger.info("Next steps:")
    logger.info(f"  1. Review the generated vertical: {output_path}")
    logger.info(f"  2. Edit if needed to refine prompts and patterns")
    logger.info(f"  3. Use in your workflow:")
    logger.info(f"     runner = AgenticWorkflowRunner(")
    logger.info(f"         graph_name='{args.graph_name}',")
    logger.info(f"         industry='{vertical['metadata']['name']}'")
    logger.info(f"     )")
    logger.info("")

    if args.interactive:
        # Ask if user wants to review
        response = input("Open the generated file? [Y/n]: ").strip().lower()
        if response in ["", "y", "yes"]:
            import subprocess

            editor = subprocess.os.environ.get("EDITOR", "cat")
            subprocess.run([editor, str(output_path)])

    return 0


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Generate custom industry vertical from business requirements",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic generation
  python -m graph_analytics_ai.cli.generate_vertical \\
      --input docs/business_requirements.md \\
      --graph-name supply_chain_graph
  
  # With domain description and validation
  python -m graph_analytics_ai.cli.generate_vertical \\
      --input docs/business_requirements.md \\
      --domain-description docs/domain_description.md \\
      --graph-name healthcare_graph \\
      --validate \\
      --interactive
  
  # Based on existing vertical
  python -m graph_analytics_ai.cli.generate_vertical \\
      --input docs/business_requirements.md \\
      --graph-name my_graph \\
      --base-vertical fintech \\
      --output custom_fintech.json
""",
    )

    parser.add_argument(
        "--input", required=True, help="Path to business requirements document"
    )

    parser.add_argument(
        "--graph-name", required=True, help="Name of the graph to analyze"
    )

    parser.add_argument(
        "--output",
        default=".graph-analytics/industry_vertical.json",
        help="Output path for generated vertical (default: .graph-analytics/industry_vertical.json)",
    )

    parser.add_argument(
        "--domain-description", help="Optional path to domain description document"
    )

    parser.add_argument(
        "--base-vertical",
        choices=["adtech", "fintech", "fraud_intelligence", "social", "generic"],
        help="Base the generated vertical on an existing one",
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate the generated vertical against schema",
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for user confirmation and review",
    )

    parser.add_argument(
        "--force", action="store_true", help="Save even if validation fails"
    )

    parser.add_argument(
        "--verbose", action="store_true", help="Show detailed error messages"
    )

    args = parser.parse_args()

    # Run async generation
    exit_code = asyncio.run(generate_vertical_async(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
