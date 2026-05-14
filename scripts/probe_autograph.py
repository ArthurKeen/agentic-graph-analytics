"""One-shot probe of an Autograph-bearing ArangoDB.

Connects to the database configured in .env, lists all collections and
named graphs, and groups them by inferred Autograph project prefix so
we can confirm the proposed detection rules match real Autograph output
before recommending where to land them in arango-schema-analyzer.

Usage:
    python scripts/probe_autograph.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

# Load .env
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from arango import ArangoClient


# Suffixes Autograph uses (per the user's description). Edge collections
# go in EDGE_SUFFIXES; everything else is a vertex collection or a named
# graph definition.
CORPUS_VERTEX_SUFFIXES = {"domains", "modules", "sources", "rags"}
KG_VERTEX_SUFFIXES = {"Chunks", "Communities", "Documents", "Entities"}
EDGE_SUFFIXES = {"relations"}
GRAPH_SUFFIXES = {"CorpusGraph", "kg"}

ALL_SUFFIXES = (
    CORPUS_VERTEX_SUFFIXES
    | KG_VERTEX_SUFFIXES
    | EDGE_SUFFIXES
    | GRAPH_SUFFIXES
)


def _connect():
    endpoint = os.environ["ARANGO_ENDPOINT"]
    user = os.environ["ARANGO_USER"]
    password = os.environ["ARANGO_PASSWORD"]
    database = os.environ["ARANGO_DATABASE"]
    verify = os.environ.get("ARANGO_VERIFY_SSL", "true").lower() != "false"
    client = ArangoClient(hosts=endpoint, verify_override=verify)
    return client.db(database, username=user, password=password, verify=True)


def _split_prefix_suffix(name: str) -> tuple:
    """Return (project_prefix, suffix) if `name` matches `<prefix>_<suffix>`
    where `suffix` is one of the known Autograph suffixes; else (None, None)."""
    if "_" not in name:
        return None, None
    # Try greedy: take everything after the LAST underscore as suffix first,
    # but Autograph project names can contain underscores, so iterate.
    parts = name.split("_")
    for i in range(len(parts) - 1, 0, -1):
        candidate_suffix = "_".join(parts[i:])
        if candidate_suffix in ALL_SUFFIXES:
            return "_".join(parts[:i]), candidate_suffix
    return None, None


def _classify_project(suffixes: set) -> dict:
    """Given the set of Autograph suffixes seen for one project prefix,
    classify completeness."""
    has_corpus_vertex = bool(suffixes & CORPUS_VERTEX_SUFFIXES)
    has_kg_vertex = bool(suffixes & KG_VERTEX_SUFFIXES)
    has_corpus_graph = "CorpusGraph" in suffixes
    has_kg_graph = "kg" in suffixes
    has_edge = bool(suffixes & EDGE_SUFFIXES)

    role_corpus = has_corpus_vertex or has_corpus_graph
    role_kg = has_kg_vertex or has_kg_graph

    if role_corpus and role_kg:
        completeness = "complete"
    elif role_corpus and not role_kg:
        completeness = "corpus_only"
    elif role_kg and not role_corpus:
        completeness = "kg_only"
    else:
        completeness = "unknown"

    # Confidence: corpus needs >=2 of the corpus suffixes, KG needs >=3 of KG
    corpus_score = len(suffixes & CORPUS_VERTEX_SUFFIXES) / 4.0
    kg_score = len(suffixes & KG_VERTEX_SUFFIXES) / 4.0
    confidence = max(corpus_score, kg_score)
    if has_edge:
        confidence = min(1.0, confidence + 0.1)
    if has_corpus_graph or has_kg_graph:
        confidence = min(1.0, confidence + 0.1)

    return {
        "completeness": completeness,
        "has_corpus_role": role_corpus,
        "has_kg_role": role_kg,
        "confidence": round(confidence, 2),
    }


def main() -> int:
    db = _connect()

    # --- Enumerate collections ---
    all_collections = [
        c["name"] for c in db.collections() if not c["name"].startswith("_")
    ]
    print(f"=== Database: {os.environ['ARANGO_DATABASE']} ===")
    print(f"Total user collections: {len(all_collections)}")

    # --- Enumerate named graphs ---
    graphs = list(db.graphs())
    print(f"Total named graphs: {len(graphs)}")
    print()

    # --- Group by project prefix ---
    by_project: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "collections": {},  # suffix -> name
            "graphs": [],
            "non_autograph_collections": [],
        }
    )

    unmatched: List[str] = []
    for name in all_collections:
        prefix, suffix = _split_prefix_suffix(name)
        if prefix is None:
            unmatched.append(name)
            continue
        by_project[prefix]["collections"][suffix] = name

    for g in graphs:
        prefix, suffix = _split_prefix_suffix(g["name"])
        if prefix is not None and suffix in GRAPH_SUFFIXES:
            by_project[prefix]["graphs"].append(
                {"name": g["name"], "suffix": suffix}
            )

    # --- Report per-project findings ---
    print("=== Autograph projects detected ===")
    if not by_project:
        print("(none)")
    for prefix in sorted(by_project):
        info = by_project[prefix]
        suffixes_seen = set(info["collections"].keys()) | {
            g["suffix"] for g in info["graphs"]
        }
        verdict = _classify_project(suffixes_seen)
        print(f"\nProject: {prefix!r}")
        print(f"  Verdict: {verdict}")
        print(f"  Suffixes observed: {sorted(suffixes_seen)}")
        print(f"  Collections: {info['collections']}")
        print(f"  Graphs: {[g['name'] for g in info['graphs']]}")

    # --- Report unmatched (potential blind spots in detection rules) ---
    print(f"\n=== Collections that did NOT match Autograph patterns "
          f"({len(unmatched)}) ===")
    for name in sorted(unmatched):
        print(f"  {name}")

    # --- For each detected project's edge collection, sample _from/_to to
    # check for cross-graph linkage (KG.Chunks pointing at corpus.modules,
    # KG.Documents pointing at corpus.sources, etc.) ---
    print("\n=== Cross-graph link probe ===")
    for prefix, info in by_project.items():
        edge_name = info["collections"].get("relations")
        if not edge_name:
            continue
        try:
            sample = list(
                db.aql.execute(
                    "FOR e IN @@edge LIMIT 50 RETURN {f: e._from, t: e._to}",
                    bind_vars={"@edge": edge_name},
                )
            )
        except Exception as e:
            print(f"  {edge_name}: probe failed: {e}")
            continue
        endpoint_collections: Dict[str, int] = defaultdict(int)
        for row in sample:
            for ref in (row["f"], row["t"]):
                if isinstance(ref, str) and "/" in ref:
                    endpoint_collections[ref.split("/")[0]] += 1
        print(f"  Edge {edge_name!r} (sampled {len(sample)} edges):")
        for coll, count in sorted(
            endpoint_collections.items(), key=lambda x: -x[1]
        ):
            print(f"    -> {coll}: {count} refs")

    # --- For one fully-matched project, sample a corpus vertex and a KG
    # vertex to compare property shapes and discriminator presence ---
    print("\n=== Document shape probe (first complete project) ===")
    complete = [
        p for p, info in by_project.items()
        if _classify_project(
            set(info["collections"].keys())
            | {g["suffix"] for g in info["graphs"]}
        )["completeness"] == "complete"
    ]
    if not complete:
        print("  (no complete project found)")
    else:
        target = sorted(complete)[0]
        info = by_project[target]
        print(f"  Project: {target!r}")
        for suffix, name in sorted(info["collections"].items()):
            try:
                doc = list(
                    db.aql.execute(
                        "FOR d IN @@coll LIMIT 1 RETURN d",
                        bind_vars={"@coll": name},
                    )
                )
            except Exception as e:
                print(f"    {suffix} ({name}): probe failed: {e}")
                continue
            if not doc:
                print(f"    {suffix} ({name}): empty")
                continue
            keys = sorted(doc[0].keys())
            print(f"    {suffix} ({name}): {len(keys)} fields -> {keys}")

    # --- Print the named graph edge definitions (this is where the
    # corpus/kg distinction is officially encoded) ---
    print("\n=== Named graph edge definitions ===")
    for g in graphs:
        meta = db.graph(g["name"])
        try:
            ed = meta.edge_definitions()
        except Exception:
            ed = []
        print(f"  {g['name']}:")
        for definition in ed:
            print(
                f"    {definition['edge_collection']}: "
                f"{definition['from_vertex_collections']} -> "
                f"{definition['to_vertex_collections']}"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
