"""Seed a workspace + connection profile pointed at addtech-knowledge-graph
and bulk-discover its named graphs through the live product API.

This exercises Phase 6e end to end: bulk discovery runs the Autograph
detector, stamps each profile with its corpus / knowledge_graph
purpose, persists ``arango_product`` metadata, and auto-creates a
``GraphSet`` pairing the OpenRTB-API-Specification corpus + KG.

Run with the local backend already running on http://127.0.0.1:8000
and the .env at the repo root populated with the addtech-knowledge-graph
credentials.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

API = os.environ.get("API_BASE", "http://127.0.0.1:8000").rstrip("/")
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def load_env() -> dict[str, str]:
    """Tiny .env loader; tolerates spaces and comments."""
    env: dict[str, str] = {}
    if not ENV_PATH.exists():
        return env
    for raw in ENV_PATH.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env


def post(path: str, payload: dict) -> dict:
    r = requests.post(f"{API}{path}", json=payload, timeout=120)
    if not r.ok:
        print(f"POST {path} -> HTTP {r.status_code}\n{r.text}", file=sys.stderr)
        r.raise_for_status()
    return r.json()


def main() -> int:
    env = load_env()
    db = env.get("ARANGO_DATABASE", "addtech-knowledge-graph")
    endpoint = env.get("ARANGO_ENDPOINT", "https://prod.demo.pilot.arango.ai")
    username = env.get("ARANGO_USER", "root")
    password_var = "ARANGO_PASSWORD"  # secret-ref to the env var
    if not env.get(password_var):
        print(f"ERROR: {password_var} not set in {ENV_PATH}", file=sys.stderr)
        return 2
    # Make the password visible to the backend process via its own env;
    # if the backend was started in a separate shell we need to ensure
    # the var is also exported there. The currently running backend
    # was launched from the repo root and inherited the .env via
    # python-dotenv loading at import time, so it sees ARANGO_PASSWORD.

    print("==> Creating workspace")
    ws = post(
        "/api/workspaces",
        {
            "customer_name": "Arango Demo",
            "project_name": "AdTech Knowledge Graph",
            "environment": "demo",
            "description": "Demo workspace targeting addtech-knowledge-graph "
            "(contains the OpenRTB-API-Specification Autograph project).",
            "tags": ["adtech", "autograph", "graphrag", "demo"],
            "actor": "demo-script",
        },
    )
    workspace_id = ws["workspace_id"]
    print(f"   workspace_id={workspace_id}")

    print("==> Creating connection profile -> %s @ %s" % (db, endpoint))
    cp = post(
        f"/api/workspaces/{workspace_id}/connection-profiles",
        {
            "name": f"{db} (live)",
            "deployment_mode": "self_managed",
            "endpoint": endpoint,
            "database": db,
            "username": username,
            "verify_ssl": True,
            "secret_refs": {
                "password": {"kind": "env", "ref": password_var},
            },
            "metadata": {"source": "seed_addtech_demo.py"},
        },
    )
    connection_profile_id = cp["connection_profile_id"]
    print(f"   connection_profile_id={connection_profile_id}")

    print("==> Verifying connection")
    v = post(
        f"/api/connection-profiles/{connection_profile_id}/verify",
        {"password_secret_key": "password"},
    )
    print(f"   status={v.get('status')} message={v.get('message')}")

    print("==> Bulk-discovering graph profiles (runs Autograph detector)")
    inv = post(
        f"/api/connection-profiles/{connection_profile_id}/discover-graph-profiles",
        {
            "password_secret_key": "password",
            "include_system": False,
            "schema_strategy": "auto",
        },
    )
    print(f"   discovered_graph_count={inv.get('discovered_graph_count')}")
    if inv.get("failures"):
        print(f"   failures={len(inv['failures'])}")
        for f in inv["failures"][:3]:
            print(f"     - {f}")
    if inv.get("arango_product"):
        prod = inv["arango_product"]
        autographs = prod.get("autograph_projects", [])
        print(f"   AUTOGRAPH PROJECTS DETECTED: {len(autographs)}")
        for p in autographs:
            print(
                f"     - {p['project_name']} "
                f"({p['completeness']}, conf={p['confidence']:.2f})"
            )
            if p.get("warnings"):
                for w in p["warnings"]:
                    print(f"       warn: {w}")
    if inv.get("auto_created_graph_sets"):
        print(f"   AUTO-CREATED GRAPH SETS: {len(inv['auto_created_graph_sets'])}")
        for gs in inv["auto_created_graph_sets"]:
            print(
                f"     - {gs['name']} "
                f"({len(gs.get('graph_profile_ids', []))} members, "
                f"{len(gs.get('cross_graph_links', []))} cross-links)"
            )

    print()
    print(f"DONE. Open http://localhost:3001/workspace?id={workspace_id}")
    print()
    print("Quick cross-reference URLs (for the API):")
    print(f"  GET  {API}/api/workspaces/{workspace_id}/overview")
    print(f"  GET  {API}/api/workspaces/{workspace_id}/graph-sets")
    print(f"  GET  {API}/api/connection-profiles/{connection_profile_id}/graphs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
