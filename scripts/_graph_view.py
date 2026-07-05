"""Build interactive Plotly node-link diagrams from algorithm result collections.

Used by `seed_adtech_workspace.py` to inject a 'Graph View' chart into reports
whose result collection has enough data to make one (PageRank / WCC / SCC /
Betweenness / Label Propagation).
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import plotly.graph_objects as go


# Visual style ----------------------------------------------------------------
_NODE_FONT_SIZE = 9
_DEFAULT_HEIGHT = 520
_DEFAULT_WIDTH = 900
_LAYOUT_ITERATIONS = 200
_LAYOUT_K_SCALE = 1.0
_PALETTE = [
    "#2563eb",  # blue
    "#16a34a",  # green
    "#dc2626",  # red
    "#9333ea",  # purple
    "#ea580c",  # orange
    "#0891b2",  # teal
    "#ca8a04",  # mustard
    "#db2777",  # pink
]


def _short_label(node_id: str, max_len: int = 22) -> str:
    """Render a short, human-friendly node label."""

    if len(node_id) <= max_len:
        return node_id
    head, _, tail = node_id.partition("/")
    if tail:
        if len(tail) > max_len - len(head) - 1:
            return f"{head}/{tail[: max_len - len(head) - 4]}…"
        return f"{head}/{tail}"
    return node_id[: max_len - 1] + "…"


def _force_layout(
    node_ids: Sequence[str],
    edges: Sequence[Tuple[str, str]],
    iterations: int = _LAYOUT_ITERATIONS,
) -> Dict[str, Tuple[float, float]]:
    """Tiny pure-Python force-directed layout.

    Used in lieu of networkx so this file has no extra deps.
    """

    rng = random.Random(42)
    n = len(node_ids)
    if n == 0:
        return {}

    positions = {nid: (rng.random(), rng.random()) for nid in node_ids}
    if n == 1:
        return positions

    k = _LAYOUT_K_SCALE / math.sqrt(n)
    edge_set = {(u, v) for u, v in edges}

    temperature = 0.1
    for _ in range(iterations):
        disp = {nid: [0.0, 0.0] for nid in node_ids}

        for i, u in enumerate(node_ids):
            ux, uy = positions[u]
            for v in node_ids[i + 1 :]:
                vx, vy = positions[v]
                dx = ux - vx
                dy = uy - vy
                dist = math.sqrt(dx * dx + dy * dy) or 0.001
                force = (k * k) / dist
                disp[u][0] += dx / dist * force
                disp[u][1] += dy / dist * force
                disp[v][0] -= dx / dist * force
                disp[v][1] -= dy / dist * force

        for u, v in edge_set:
            if u not in positions or v not in positions:
                continue
            ux, uy = positions[u]
            vx, vy = positions[v]
            dx = ux - vx
            dy = uy - vy
            dist = math.sqrt(dx * dx + dy * dy) or 0.001
            force = (dist * dist) / k
            disp[u][0] -= dx / dist * force
            disp[u][1] -= dy / dist * force
            disp[v][0] += dx / dist * force
            disp[v][1] += dy / dist * force

        for nid in node_ids:
            dx, dy = disp[nid]
            mag = math.sqrt(dx * dx + dy * dy) or 0.001
            new_x = positions[nid][0] + (dx / mag) * min(mag, temperature)
            new_y = positions[nid][1] + (dy / mag) * min(mag, temperature)
            positions[nid] = (new_x, new_y)

        temperature *= 0.97

    return positions


def _figure_html(fig: go.Figure, title: str) -> str:
    """Serialize a Plotly figure into a self-contained HTML string."""

    fig.update_layout(
        title=title,
        showlegend=True,
        hovermode="closest",
        height=_DEFAULT_HEIGHT,
        width=_DEFAULT_WIDTH,
        margin=dict(l=20, r=20, t=50, b=20),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font=dict(family="Inter, Helvetica, Arial, sans-serif", size=11),
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, zeroline=False, visible=False),
    )
    return fig.to_html(include_plotlyjs="cdn", full_html=True)


def _edge_trace(
    edges: Iterable[Tuple[str, str]],
    positions: Dict[str, Tuple[float, float]],
) -> go.Scatter:
    edge_x: List[float | None] = []
    edge_y: List[float | None] = []
    for u, v in edges:
        if u not in positions or v not in positions:
            continue
        x0, y0 = positions[u]
        x1, y1 = positions[v]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    return go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(width=0.6, color="#94a3b8"),
        hoverinfo="skip",
        showlegend=False,
    )


def _node_trace(
    node_ids: Sequence[str],
    positions: Dict[str, Tuple[float, float]],
    *,
    sizes: Optional[Sequence[float]] = None,
    group_label: Optional[str] = None,
    color: str,
    customdata: Optional[Sequence[Any]] = None,
    hovertemplate: Optional[str] = None,
) -> go.Scatter:
    xs = [positions[nid][0] for nid in node_ids if nid in positions]
    ys = [positions[nid][1] for nid in node_ids if nid in positions]
    labels = [_short_label(nid) for nid in node_ids if nid in positions]
    text_full = [nid for nid in node_ids if nid in positions]
    return go.Scatter(
        x=xs,
        y=ys,
        mode="markers+text",
        marker=dict(
            size=sizes if sizes is not None else 14,
            color=color,
            line=dict(width=1, color="#1e293b"),
            sizemode="diameter",
        ),
        text=labels,
        textposition="top center",
        textfont=dict(size=_NODE_FONT_SIZE, color="#1e293b"),
        customdata=customdata if customdata is not None else text_full,
        hovertemplate=hovertemplate
        or "<b>%{customdata}</b><extra></extra>",
        name=group_label or "Nodes",
    )


def _scaled_marker_sizes(values: Sequence[float], lo: float = 8.0, hi: float = 36.0) -> List[float]:
    if not values:
        return []
    vmax = max(values)
    vmin = min(values)
    if vmax == vmin:
        return [hi] * len(values)
    span = vmax - vmin
    return [lo + (hi - lo) * ((v - vmin) / span) for v in values]


# ---------------------------------------------------------------------------- #
# Graph data extraction                                                        #
# ---------------------------------------------------------------------------- #
def _extract_neighbors_subgraph(
    db: Any,
    seed_nodes: Sequence[str],
    edge_collections: Sequence[str],
    *,
    max_extra_neighbors: int = 30,
    max_edges: int = 80,
) -> Tuple[List[str], List[Tuple[str, str]]]:
    """Return (nodes, edges) for the seed set and a bounded neighborhood.

    Only edges that touch at least one seed node are pulled, and only up to
    `max_edges`. New neighbors discovered from those edges are added up to
    `max_extra_neighbors` to keep the layout legible.
    """

    if not seed_nodes:
        return [], []

    seed_set = list(dict.fromkeys(seed_nodes))
    seed_lookup = set(seed_set)

    edges: List[Tuple[str, str]] = []
    extra_nodes: List[str] = []

    # Per-collection LIMIT: split the budget evenly across edge collections so
    # a single dense edge type doesn't crowd out everything else.
    if edge_collections:
        per_collection_limit = max(2, max_edges // len(edge_collections))
    else:
        per_collection_limit = max_edges

    for collection in edge_collections:
        if len(edges) >= max_edges:
            break
        if not db.has_collection(collection):
            continue
        try:
            cursor = db.aql.execute(
                f"""
                FOR e IN {collection}
                    FILTER e._from IN @seeds OR e._to IN @seeds
                    LIMIT @per_collection_limit
                    RETURN {{ from: e._from, to: e._to }}
                """,
                bind_vars={
                    "seeds": seed_set,
                    "per_collection_limit": per_collection_limit,
                },
            )
        except Exception:
            continue

        for entry in cursor:
            u, v = entry["from"], entry["to"]
            edges.append((u, v))
            for nid in (u, v):
                if nid not in seed_lookup and nid not in extra_nodes:
                    extra_nodes.append(nid)
            if len(edges) >= max_edges:
                break
            if len(extra_nodes) >= max_extra_neighbors:
                # Stop pulling NEW neighbors but keep edges between known nodes.
                pass

    extra_nodes = extra_nodes[:max_extra_neighbors]
    nodes = list(seed_set) + extra_nodes
    node_set = set(nodes)
    pruned_edges = [(u, v) for (u, v) in edges if u in node_set and v in node_set]
    return nodes, pruned_edges


# ---------------------------------------------------------------------------- #
# Public builders                                                              #
# ---------------------------------------------------------------------------- #
def build_pagerank_graph_html(
    db: Any,
    result_collection: str,
    edge_collections: Sequence[str],
    *,
    top_n: int = 25,
    title: str = "PageRank Top-N Subgraph",
) -> Optional[str]:
    """Build a Plotly node-link diagram of the top-N PageRank nodes."""

    rows = list(
        db.aql.execute(
            f"""
            FOR doc IN {result_collection}
                FILTER HAS(doc, 'rank')
                SORT doc.rank DESC
                LIMIT @top_n
                RETURN {{ id: doc.id, rank: doc.rank }}
            """,
            bind_vars={"top_n": top_n},
        )
    )
    if not rows:
        return None

    seeds = [r["id"] for r in rows]
    rank_by_id = {r["id"]: float(r["rank"]) for r in rows}
    nodes, edges = _extract_neighbors_subgraph(
        db, seeds, edge_collections, max_extra_neighbors=30, max_edges=140
    )
    positions = _force_layout(nodes, edges)

    seed_set = set(seeds)
    seed_nodes = [n for n in nodes if n in seed_set]
    seed_sizes = _scaled_marker_sizes([rank_by_id[n] for n in seed_nodes])
    seed_hover = [
        f"{n}<br>rank: {rank_by_id[n]:.3e}" for n in seed_nodes
    ]
    neighbor_nodes = [n for n in nodes if n not in seed_set]

    fig = go.Figure()
    fig.add_trace(_edge_trace(edges, positions))
    if neighbor_nodes:
        fig.add_trace(
            _node_trace(
                neighbor_nodes,
                positions,
                color="#cbd5e1",
                sizes=[10] * len(neighbor_nodes),
                group_label="Neighbors",
            )
        )
    fig.add_trace(
        _node_trace(
            seed_nodes,
            positions,
            color=_PALETTE[0],
            sizes=seed_sizes,
            group_label=f"Top {len(seed_nodes)} by PageRank",
            customdata=seed_hover,
            hovertemplate="%{customdata}<extra></extra>",
        )
    )
    return _figure_html(fig, title)


def build_components_graph_html(
    db: Any,
    result_collection: str,
    edge_collections: Sequence[str],
    *,
    top_components: int = 4,
    members_per_component: int = 10,
    title: str = "Top Connected Components",
    field: str = "component",
) -> Optional[str]:
    """Build a node-link diagram of the largest WCC / SCC / LPA components."""

    component_rows = list(
        db.aql.execute(
            f"""
            FOR doc IN {result_collection}
                FILTER HAS(doc, '{field}')
                COLLECT cid = doc.{field} WITH COUNT INTO size
                SORT size DESC
                LIMIT @top_components
                RETURN {{ component: cid, size: size }}
            """,
            bind_vars={"top_components": top_components},
        )
    )
    if not component_rows:
        return None

    cid_to_size = {r["component"]: r["size"] for r in component_rows}
    cids = list(cid_to_size.keys())

    seeds: List[str] = []
    cid_for_node: Dict[str, str] = {}
    for cid in cids:
        members = list(
            db.aql.execute(
                f"""
                FOR doc IN {result_collection}
                    FILTER doc.{field} == @cid
                    LIMIT @limit
                    RETURN doc.id
                """,
                bind_vars={"cid": cid, "limit": members_per_component},
            )
        )
        for m in members:
            seeds.append(m)
            cid_for_node[m] = cid

    nodes, edges = _extract_neighbors_subgraph(
        db, seeds, edge_collections, max_extra_neighbors=10, max_edges=150
    )
    positions = _force_layout(nodes, edges)

    fig = go.Figure()
    fig.add_trace(_edge_trace(edges, positions))

    for idx, cid in enumerate(cids):
        members = [n for n in nodes if cid_for_node.get(n) == cid]
        if not members:
            continue
        size = cid_to_size[cid]
        fig.add_trace(
            _node_trace(
                members,
                positions,
                color=_PALETTE[idx % len(_PALETTE)],
                sizes=[16] * len(members),
                group_label=f"{_short_label(cid, 24)}  (n={size})",
            )
        )

    others = [n for n in nodes if n not in cid_for_node]
    if others:
        fig.add_trace(
            _node_trace(
                others,
                positions,
                color="#e2e8f0",
                sizes=[8] * len(others),
                group_label="Other neighbors",
            )
        )
    return _figure_html(fig, title)
