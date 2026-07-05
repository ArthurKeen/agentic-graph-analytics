#!/usr/bin/env python3
"""One-shot diagnostic: list every named graph in addtech-knowledge-graph."""
import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

from arango import ArangoClient

client = ArangoClient(hosts=os.environ["ARANGO_ENDPOINT"])
db = client.db(
    "addtech-knowledge-graph",
    username=os.environ["ARANGO_USER"],
    password=os.environ["ARANGO_PASSWORD"],
)

graphs = db.graphs()
print(f"Named graphs in addtech-knowledge-graph: {len(graphs)}")
print("=" * 70)

graph_collections = set()
for g in graphs:
    name = g["name"]
    eds = db.graph(name).edge_definitions()
    verts = db.graph(name).vertex_collections()
    print(f"\n  Graph: {name}")
    print(f"    vertex_collections ({len(verts)}):")
    for v in sorted(verts):
        n = db.collection(v).count() if db.has_collection(v) else 0
        print(f"      {v:<28} count={n:,}")
        graph_collections.add(v)
    edge_names = [e["edge_collection"] for e in eds]
    print(f"    edge_collections ({len(edge_names)}):")
    for e in sorted(edge_names):
        n = db.collection(e).count() if db.has_collection(e) else 0
        print(f"      {e:<28} count={n:,}")
        graph_collections.add(e)

print()
print("=" * 70)
all_cols = sorted([c["name"] for c in db.collections() if not c["name"].startswith("_")])
ungraphed = [c for c in all_cols if c not in graph_collections]
print(f"Collections NOT in any named graph ({len(ungraphed)}):")
for c in ungraphed:
    n = db.collection(c).count()
    kind = "edge" if db.collection(c).properties().get("type") == 3 else "vertex"
    print(f"    {c:<30} ({kind}) count={n:,}")
