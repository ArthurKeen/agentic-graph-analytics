#!/usr/bin/env python3
"""One-shot upgrade for FR-67b on an *existing* workspace.

The workspace at ``--workspace-id`` was created before the
"default / all-collections" graph profile existed. This script:

1. Re-discovers a database-scope profile (force_database_scope=True)
   on the workspace's first verified connection profile, creating a
   ``default`` GraphProfile alongside the existing named-graph
   profiles. Idempotent: if a ``default`` profile already exists for
   the workspace+connection pair, the existing profile is reused.

2. Sets ``workspace.active_graph_profile_id`` to the graph profile
   matching ``--active-graph-name`` (default: ``AdtechGraph``) so the
   banner picks that graph deterministically on the next page load.

Drives the running Product API (so the live demo backend gets the
state changes without a restart). Run after upgrading the
``agentic-graph-analytics`` server to a build that includes the new
``/active-graph-profile`` route.

Example:

    python scripts/upgrade_workspace_default_graph.py \\
      --base-url http://127.0.0.1:8020 \\
      --workspace-id workspace-82ce0dc1-3857-41bd-bc11-abc0111b76c7 \\
      --active-graph-name AdtechGraph
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, Dict, List, Optional

import requests


def _api_get(base_url: str, path: str, timeout: int = 15) -> Any:
    resp = requests.get(f"{base_url}{path}", timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _api_post(
    base_url: str, path: str, payload: Dict[str, Any], timeout: int = 90
) -> Any:
    resp = requests.post(f"{base_url}{path}", json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _api_patch(
    base_url: str, path: str, payload: Dict[str, Any], timeout: int = 15
) -> Any:
    resp = requests.patch(f"{base_url}{path}", json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _find_connection_profile(
    overview: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    profiles: List[Dict[str, Any]] = overview.get("latest_connection_profiles", [])
    # Prefer a verified profile so discovery actually works.
    verified = [p for p in profiles if p.get("last_verification_status") == "success"]
    return (verified or profiles)[0] if profiles else None


def _find_existing_default(
    overview: Dict[str, Any], connection_profile_id: str
) -> Optional[Dict[str, Any]]:
    for profile in overview.get("latest_graph_profiles", []):
        if (
            profile.get("graph_name") == "default"
            and profile.get("connection_profile_id") == connection_profile_id
        ):
            return profile
    return None


def _find_profile_by_name(
    overview: Dict[str, Any], graph_name: str
) -> Optional[Dict[str, Any]]:
    for profile in overview.get("latest_graph_profiles", []):
        if profile.get("graph_name") == graph_name:
            return profile
    return None


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8020",
        help="Running Product API base URL (default: %(default)s)",
    )
    parser.add_argument(
        "--workspace-id",
        required=True,
        help="Workspace to upgrade (e.g. workspace-82ce0dc1-...)",
    )
    parser.add_argument(
        "--active-graph-name",
        default="AdtechGraph",
        help="graph_name to set as active after discovery (default: %(default)s)",
    )
    parser.add_argument(
        "--actor",
        default="upgrade-script:fr-67b",
        help="Actor recorded on the audit event (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    print(f"--- FR-67b upgrade for {args.workspace_id} ---", flush=True)
    overview = _api_get(args.base_url, f"/api/workspaces/{args.workspace_id}/overview")
    profile = _find_connection_profile(overview)
    if not profile:
        print(
            "FAIL: no connection profile on this workspace; create one first.",
            file=sys.stderr,
        )
        return 1
    connection_profile_id = profile["connection_profile_id"]
    print(
        f"  connection_profile_id={connection_profile_id} "
        f"({profile.get('name')!r}, {profile.get('last_verification_status')})",
        flush=True,
    )

    existing_default = _find_existing_default(overview, connection_profile_id)
    if existing_default:
        print(
            f"  default profile already exists: "
            f"{existing_default['graph_profile_id']} — skipping discovery.",
            flush=True,
        )
    else:
        print(
            "  default profile missing — running database-scope discovery "
            "(may take 30-90s on large DBs)...",
            flush=True,
        )
        result = _api_post(
            args.base_url,
            f"/api/connection-profiles/{connection_profile_id}/discover-graph",
            {
                "force_database_scope": True,
                "sample_size": 100,
                "max_samples_per_collection": 3,
                "verify_system": True,
                "created_by": args.actor,
            },
        )
        new_profile = result.get("graph_profile", {})
        print(
            f"  created default profile: {new_profile.get('graph_profile_id')} "
            f"(graph_name={new_profile.get('graph_name')}, "
            f"vertex_collections={len(new_profile.get('vertex_collections', []))}, "
            f"edge_collections={len(new_profile.get('edge_collections', []))})",
            flush=True,
        )

    # Re-fetch overview now that the default profile exists, so the
    # name resolution below can see the full set.
    overview = _api_get(args.base_url, f"/api/workspaces/{args.workspace_id}/overview")

    target = _find_profile_by_name(overview, args.active_graph_name)
    if not target:
        print(
            f"FAIL: no graph profile named {args.active_graph_name!r} found "
            f"(available: "
            f"{[p['graph_name'] for p in overview.get('latest_graph_profiles', [])]})",
            file=sys.stderr,
        )
        return 2
    target_id = target["graph_profile_id"]
    print(
        f"  setting active_graph_profile_id={target_id} ({args.active_graph_name})",
        flush=True,
    )
    updated = _api_patch(
        args.base_url,
        f"/api/workspaces/{args.workspace_id}/active-graph-profile",
        {"graph_profile_id": target_id, "actor": args.actor},
    )
    print(
        f"  workspace.active_graph_profile_id is now "
        f"{updated.get('active_graph_profile_id')!r}",
        flush=True,
    )
    print("--- done ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
