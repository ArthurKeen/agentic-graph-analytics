#!/usr/bin/env python3
"""
Cleanup GAE Engines Script

Utility to manually clean up leftover Graph Analytics Engines from failed runs.
Engines bill while they are DEPLOYED, and a run killed mid-flight leaves them
behind: cleanup happens after the retry loop, so an interrupted or crashed run
never reaches it. One FinReflect run deployed 34 engines and cleaned up 29.

SAFETY -- the platform lists every service in the namespace, not just ours:
GraphRAG retrievers, Autograph instances and user-defined services belonging to
other projects sit alongside GAE engines. Only services whose id begins with
``arangodb-gral-`` are Graph Analytics Engines, and this script will not touch
anything else. An earlier version listed everything and offered to delete it
all, which would have taken down unrelated workloads.

Usage:
    python scripts/cleanup_gae_engines.py --list           # show, delete nothing
    python scripts/cleanup_gae_engines.py                  # delete, with confirmation
    python scripts/cleanup_gae_engines.py --force          # delete, no confirmation
    python scripts/cleanup_gae_engines.py --engine-id=<id> # delete one
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# `get_gae_connection` lives in the submodule; it is not re-exported from the
# package root, which is what broke this script (ImportError) at exactly the
# moment it was needed to clean up after a failed run.
from graph_analytics_ai.gae_connection import get_gae_connection

# Graph Analytics Engines are the only services this script may delete.
GAE_SERVICE_PREFIX = "arangodb-gral-"


def _service_id(service: dict) -> str:
    return service.get("serviceId") or service.get("id") or ""


def list_services(gae):
    """Return (gae_engines, other_services) from the platform."""

    services = gae.list_services()
    ours = [s for s in services if _service_id(s).startswith(GAE_SERVICE_PREFIX)]
    others = [s for s in services if s not in ours]
    return ours, others


def print_inventory(ours, others):
    print(f"\nGraph Analytics Engines ({len(ours)}) — eligible for cleanup:")
    if not ours:
        print("  (none)")
    for idx, service in enumerate(ours, 1):
        print(
            f"  {idx}. {_service_id(service)}  "
            f"status={service.get('status', 'unknown')}  "
            f"{service.get('description', '')}"
        )

    print(f"\nOther services ({len(others)}) — NOT touched by this script:")
    for service in others:
        db_name = service.get("dbName")
        suffix = f"  db={db_name}" if db_name else ""
        print(f"  - {_service_id(service)}  status={service.get('status')}{suffix}")


def delete_engine(gae, engine_id: str) -> bool:
    if not engine_id.startswith(GAE_SERVICE_PREFIX):
        print(
            f"REFUSED: '{engine_id}' is not a Graph Analytics Engine "
            f"(expected prefix '{GAE_SERVICE_PREFIX}'). Nothing deleted."
        )
        return False
    try:
        print(f"Stopping {engine_id}...")
        gae.stop_engine(engine_id)
        print(f"  deleted {engine_id}")
        return True
    except Exception as exc:  # noqa: BLE001 — report and continue to the next
        print(f"  FAILED to delete {engine_id}: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean up leftover GAE engines")
    parser.add_argument(
        "--list", "-l", action="store_true", help="List only; delete nothing"
    )
    parser.add_argument("--engine-id", help="Delete a single engine by id")
    parser.add_argument(
        "--force", "-f", action="store_true", help="Skip the confirmation prompt"
    )
    args = parser.parse_args()

    gae = get_gae_connection()

    if args.engine_id:
        return 0 if delete_engine(gae, args.engine_id) else 1

    ours, others = list_services(gae)
    print_inventory(ours, others)

    if args.list:
        return 0

    if not ours:
        print("\nNothing to clean up.")
        return 0

    if not args.force:
        print(
            f"\nThis deletes {len(ours)} Graph Analytics Engine(s). Cannot be undone."
        )
        if input("Proceed? [y/N]: ").strip().lower() != "y":
            print("Cancelled.")
            return 0

    deleted = sum(1 for service in ours if delete_engine(gae, _service_id(service)))
    print(f"\nDeleted {deleted} of {len(ours)}.")
    return 0 if deleted == len(ours) else 1


if __name__ == "__main__":
    raise SystemExit(main())
