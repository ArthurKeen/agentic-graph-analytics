"""
Custom industry vertical loading and management.

This module handles loading custom industry verticals from client projects
and registering them with the platform for use in analysis.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def load_custom_vertical(project_root: Path) -> Optional[Dict[str, Any]]:
    """
    Load custom industry vertical from client project.

    Looks for: <project_root>/.graph-analytics/industry_vertical.json

    Args:
        project_root: Root directory of the client project

    Returns:
        Dictionary containing the custom vertical, or None if not found
    """
    vertical_path = project_root / ".graph-analytics" / "industry_vertical.json"

    if not vertical_path.exists():
        logger.debug(f"No custom vertical found at {vertical_path}")
        return None

    try:
        vertical_data = json.loads(vertical_path.read_text())
        logger.info(
            f"Loaded custom vertical: {vertical_data['metadata']['display_name']}"
        )
        return vertical_data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse custom vertical JSON: {e}")
        return None
    except KeyError as e:
        logger.error(f"Invalid custom vertical structure, missing key: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading custom vertical: {e}")
        return None


def load_platform_custom_vertical(industry_name: str) -> Optional[Dict[str, Any]]:
    """
    Load custom vertical from platform registry.

    Looks for: graph_analytics_ai/ai/reporting/verticals/<industry_name>.json

    Args:
        industry_name: Name of the industry vertical

    Returns:
        Dictionary containing the custom vertical, or None if not found
    """
    # Get the platform's reporting directory
    from graph_analytics_ai.ai.reporting import prompts

    reporting_dir = Path(prompts.__file__).parent
    verticals_dir = reporting_dir / "verticals"

    vertical_path = verticals_dir / f"{industry_name}.json"

    if not vertical_path.exists():
        logger.debug(f"No platform custom vertical found: {industry_name}")
        return None

    try:
        vertical_data = json.loads(vertical_path.read_text())
        logger.info(
            f"Loaded platform custom vertical: {vertical_data['metadata']['display_name']}"
        )
        return vertical_data
    except Exception as e:
        logger.error(f"Error loading platform custom vertical {industry_name}: {e}")
        return None


def register_custom_vertical(vertical: Dict[str, Any]) -> str:
    """
    Register custom vertical with the platform for current session.

    This adds the custom vertical's prompt to the global INDUSTRY_PROMPTS
    registry so it can be used by the reporting system.

    Args:
        vertical: Dictionary containing the custom vertical configuration

    Returns:
        The industry key to use for this vertical

    Raises:
        ValueError: If vertical data is invalid
    """
    try:
        industry_key = vertical["metadata"]["name"]
        prompt = vertical["analysis_prompt"]

        # Validate minimum requirements
        if not industry_key or not prompt:
            raise ValueError(
                "Vertical missing required fields: name or analysis_prompt"
            )

        # Register in the global registry
        from graph_analytics_ai.ai.reporting.prompts import INDUSTRY_PROMPTS

        INDUSTRY_PROMPTS[industry_key] = prompt

        logger.info(f"Registered custom vertical: {industry_key}")
        return industry_key

    except KeyError as e:
        raise ValueError(f"Invalid vertical structure, missing key: {e}")


def save_custom_vertical(vertical: Dict[str, Any], output_path: Path) -> None:
    """
    Save custom vertical to file.

    Args:
        vertical: Dictionary containing the custom vertical configuration
        output_path: Path where to save the vertical JSON file
    """
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write with pretty formatting
    output_path.write_text(json.dumps(vertical, indent=2, ensure_ascii=False))
    logger.info(f"Saved custom vertical to: {output_path}")


def get_industry_prompt_with_custom(
    industry: str, project_root: Optional[Path] = None
) -> str:
    """
    Get industry prompt with support for custom verticals.

    Load priority:
    1. Client project custom vertical (.graph-analytics/industry_vertical.json)
    2. Platform custom verticals (graph_analytics_ai/ai/reporting/verticals/)
    3. Built-in verticals (INDUSTRY_PROMPTS registry)

    Args:
        industry: Industry identifier
        project_root: Root directory of client project (defaults to current directory)

    Returns:
        Industry-specific prompt string
    """
    from graph_analytics_ai.ai.reporting.prompts import (
        get_industry_prompt,
        GENERIC_PROMPT,
    )

    if project_root is None:
        project_root = Path.cwd()

    industry_lower = industry.lower().strip()

    # 1. Try client project custom vertical
    custom_vertical = load_custom_vertical(project_root)
    if custom_vertical and custom_vertical["metadata"]["name"] == industry_lower:
        logger.info(f"Using client project custom vertical: {industry}")
        return custom_vertical["analysis_prompt"]

    # 2. Try platform custom verticals
    platform_vertical = load_platform_custom_vertical(industry_lower)
    if platform_vertical:
        logger.info(f"Using platform custom vertical: {industry}")
        return platform_vertical["analysis_prompt"]

    # 3. Fall back to built-in
    logger.debug(f"Using built-in vertical: {industry}")
    return get_industry_prompt(industry)


def list_all_verticals(project_root: Optional[Path] = None) -> Dict[str, list]:
    """
    List all available industry verticals.

    Returns:
        Dictionary with keys: builtin, platform_custom, project_custom
    """
    from graph_analytics_ai.ai.reporting.prompts import list_supported_industries

    if project_root is None:
        project_root = Path.cwd()

    result = {
        "builtin": list_supported_industries(),
        "platform_custom": [],
        "project_custom": None,
    }

    # Check platform custom verticals
    from graph_analytics_ai.ai.reporting import prompts

    reporting_dir = Path(prompts.__file__).parent
    verticals_dir = reporting_dir / "verticals"

    if verticals_dir.exists():
        for vertical_file in verticals_dir.glob("*.json"):
            try:
                vertical = json.loads(vertical_file.read_text())
                result["platform_custom"].append(
                    {
                        "name": vertical["metadata"]["name"],
                        "display_name": vertical["metadata"]["display_name"],
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to load platform vertical {vertical_file}: {e}")

    # Check project custom vertical
    custom_vertical = load_custom_vertical(project_root)
    if custom_vertical:
        result["project_custom"] = {
            "name": custom_vertical["metadata"]["name"],
            "display_name": custom_vertical["metadata"]["display_name"],
            "generated_at": custom_vertical["metadata"]["generated_at"],
            "user_validated": custom_vertical.get("user_validated", False),
        }

    return result
