#!/usr/bin/env python3
"""
Cleanup GAE Engines Script

Utility to manually cleanup leftover Graph Analytics Engines from failed runs.
Useful when auto_cleanup fails or is disabled.

Usage:
    python scripts/cleanup_gae_engines.py                    # List and cleanup all engines
    python scripts/cleanup_gae_engines.py --list             # List only (no cleanup)
    python scripts/cleanup_gae_engines.py --engine-id=<id>   # Cleanup specific engine
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph_analytics_ai import get_gae_connection
from graph_analytics_ai.config import get_gae_config


def list_engines():
    """List all running engines."""
    try:
        gae = get_gae_connection()
        
        # Check if we can list engines (AMP only)
        if not hasattr(gae, 'list_engines'):
            print("Engine listing not supported for this deployment type")
            print("(Only available for ArangoDB Managed Platform)")
            return []
        
        engines = gae.list_engines()
        return engines
    
    except Exception as e:
        print(f"Error listing engines: {e}")
        return []


def cleanup_engine(engine_id: str):
    """Cleanup a specific engine."""
    try:
        gae = get_gae_connection()
        print(f"Deleting engine {engine_id}...")
        gae.delete_engine(engine_id)
        print(f"Successfully deleted engine {engine_id}")
        return True
    except Exception as e:
        print(f"Error deleting engine {engine_id}: {e}")
        return False


def cleanup_all_engines(engines):
    """Cleanup all engines with user confirmation."""
    if not engines:
        print("No engines to cleanup")
        return
    
    print("\nEngines found:")
    for idx, engine in enumerate(engines, 1):
        size = engine.get('size_id', 'unknown')
        status = engine.get('status', {})
        is_started = status.get('is_started', False)
        print(f"  {idx}. {engine['id']} (size: {size}, started: {is_started})")
    
    print(f"\nThis will delete {len(engines)} engine(s)")
    print("WARNING: This action cannot be undone!")
    response = input("\nProceed with cleanup? [y/N]: ").lower()
    
    if response != 'y':
        print("Cleanup cancelled")
        return
    
    print("\nCleaning up engines...")
    success_count = 0
    fail_count = 0
    
    for engine in engines:
        engine_id = engine['id']
        if cleanup_engine(engine_id):
            success_count += 1
        else:
            fail_count += 1
    
    print(f"\nCleanup complete:")
    print(f"  Successfully deleted: {success_count}")
    print(f"  Failed: {fail_count}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Cleanup GAE Engines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all running engines
  python scripts/cleanup_gae_engines.py --list

  # Cleanup all engines (with confirmation)
  python scripts/cleanup_gae_engines.py

  # Cleanup specific engine
  python scripts/cleanup_gae_engines.py --engine-id=<id>

  # Force cleanup without confirmation
  python scripts/cleanup_gae_engines.py --force
        """
    )
    
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List engines only (no cleanup)"
    )
    parser.add_argument(
        "--engine-id", "-e",
        type=str,
        help="Cleanup specific engine ID"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    args = parser.parse_args()
    
    # Check configuration
    try:
        config = get_gae_config()
        print(f"Deployment: {config.get('deployment_mode', 'unknown')}")
        print(f"Deployment URL: {config.get('deployment_url', 'unknown')}")
        print()
    except Exception as e:
        print(f"Warning: Could not get GAE config: {e}")
        print()
    
    # Cleanup specific engine
    if args.engine_id:
        success = cleanup_engine(args.engine_id)
        return 0 if success else 1
    
    # List engines
    engines = list_engines()
    
    if not engines:
        print("No running engines found")
        return 0
    
    # Just list
    if args.list:
        print(f"Found {len(engines)} running engine(s):")
        for idx, engine in enumerate(engines, 1):
            size = engine.get('size_id', 'unknown')
            status = engine.get('status', {})
            is_started = status.get('is_started', False)
            print(f"  {idx}. {engine['id']} (size: {size}, started: {is_started})")
        return 0
    
    # Cleanup all
    if args.force:
        print(f"Force cleanup of {len(engines)} engine(s)...")
        for engine in engines:
            cleanup_engine(engine['id'])
    else:
        cleanup_all_engines(engines)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
