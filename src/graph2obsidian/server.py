"""Graph-aware MCP server for graph2obsidian.

Exposes the graph as a set of MCP tools so LLMs can query it over stdio.
"""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from graph2obsidian.models import Edge, Graph, Node
from graph2obsidian.parser import load_graph

mcp = FastMCP("graph2obsidian")

# ---------------------------------------------------------------------------
# Module-level graph state (populated by serve())
# ---------------------------------------------------------------------------

_graph: Graph = Graph()
_id_to_node: dict[str, Node] = {}
_outgoing: dict[str, list[Edge]] = {}
_incoming: dict[str, list[Edge]] = {}


def _load(path: Path) -> None:
    global _graph, _id_to_node, _outgoing, _incoming
    _graph = load_graph(path)
    _id_to_node = {n.id: n for n in _graph.nodes}
    _outgoing = {n.id: [] for n in _graph.nodes}
    _incoming = {n.id: [] for n in _graph.nodes}
    for edge in _graph.edges:
        if edge.from_id in _outgoing:
            _outgoing[edge.from_id].append(edge)
        if edge.to_id in _incoming:
            _incoming[edge.to_id].append(edge)


def _node_to_dict(node: Node) -> dict[str, Any]:
    return {"id": node.id, "name": node.name, "type": node.type, "properties": node.properties}


def _edge_to_dict(edge: Edge) -> dict[str, Any]:
    from_node = _id_to_node.get(edge.from_id)
    to_node = _id_to_node.get(edge.to_id)
    return {
        "relationship": edge.relationship,
        "from_id": edge.from_id,
        "from_name": from_node.name if from_node else edge.from_id,
        "to_id": edge.to_id,
        "to_name": to_node.name if to_node else edge.to_id,
        "properties": edge.properties,
    }


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def graph_stats() -> str:
    """Return a summary of the graph: node count, edge count, and type breakdowns."""
    from collections import Counter

    node_types = Counter(n.type for n in _graph.nodes)
    rel_types = Counter(e.relationship for e in _graph.edges)
    result = {
        "node_count": len(_graph.nodes),
        "edge_count": len(_graph.edges),
        "node_types": dict(node_types),
        "relationship_types": dict(rel_types),
    }
    return json.dumps(result, indent=2)


@mcp.tool()
def find_node(query: str, search_type: str = "name") -> str:
    """
    Find nodes matching a query.

    Args:
        query: Search string.
        search_type: One of 'name' (default), 'id', or 'type'.
                     - 'name': case-insensitive substring match on node name
                     - 'id': exact match on node id
                     - 'type': return all nodes of this type
    """
    q = query.lower()
    results: list[Node] = []

    if search_type == "id":
        node = _id_to_node.get(query)
        if node:
            results = [node]
    elif search_type == "type":
        results = [n for n in _graph.nodes if n.type.lower() == q]
    else:  # name
        results = [n for n in _graph.nodes if q in n.name.lower()]

    return json.dumps([_node_to_dict(n) for n in results], indent=2)


@mcp.tool()
def node_neighbors(node_id: str, direction: str = "both") -> str:
    """
    Return all edges connected to a node, along with the neighbouring nodes.

    Args:
        node_id: The id of the node to look up.
        direction: 'outgoing', 'incoming', or 'both' (default).
    """
    if node_id not in _id_to_node:
        # Try resolving by name
        matches = [n for n in _graph.nodes if n.name.lower() == node_id.lower()]
        if matches:
            node_id = matches[0].id
        else:
            return json.dumps({"error": f"Node '{node_id}' not found."})

    node = _id_to_node[node_id]
    result: dict[str, Any] = {"node": _node_to_dict(node)}

    if direction in ("outgoing", "both"):
        result["outgoing"] = [_edge_to_dict(e) for e in _outgoing.get(node_id, [])]
    if direction in ("incoming", "both"):
        result["incoming"] = [_edge_to_dict(e) for e in _incoming.get(node_id, [])]

    return json.dumps(result, indent=2)


@mcp.tool()
def query_edges(
    relationship: str,
    property_key: str = "",
    property_value: str = "",
    comparison: str = "eq",
) -> str:
    """
    Filter edges by relationship type, and optionally by a property value.

    Args:
        relationship: Relationship type to filter by (e.g. 'DONATED_TO').
        property_key: Property name to filter on (optional).
        property_value: Value to compare (as string; numeric comparisons cast automatically).
        comparison: 'eq' (default), 'ne', 'gt', 'gte', 'lt', 'lte', or 'contains'.
    """
    edges = [e for e in _graph.edges if e.relationship.upper() == relationship.upper()]

    if property_key:
        filtered: list[Edge] = []
        for edge in edges:
            raw = edge.properties.get(property_key)
            if raw is None:
                continue
            # Try numeric comparison
            try:
                raw_num = float(raw)
                cmp_num = float(property_value)
                if comparison == "gt" and raw_num > cmp_num:
                    filtered.append(edge)
                elif comparison == "gte" and raw_num >= cmp_num:
                    filtered.append(edge)
                elif comparison == "lt" and raw_num < cmp_num:
                    filtered.append(edge)
                elif comparison == "lte" and raw_num <= cmp_num:
                    filtered.append(edge)
                elif comparison == "ne" and raw_num != cmp_num:
                    filtered.append(edge)
                elif comparison == "eq" and raw_num == cmp_num:
                    filtered.append(edge)
                elif comparison == "contains" and property_value.lower() in str(raw).lower():
                    filtered.append(edge)
            except (ValueError, TypeError):
                # String comparison
                raw_str = str(raw).lower()
                cmp_str = property_value.lower()
                if comparison in ("eq", "gte", "lte") and raw_str == cmp_str:
                    filtered.append(edge)
                elif comparison == "ne" and raw_str != cmp_str:
                    filtered.append(edge)
                elif comparison == "contains" and cmp_str in raw_str:
                    filtered.append(edge)
        edges = filtered

    return json.dumps([_edge_to_dict(e) for e in edges], indent=2)


@mcp.tool()
def find_path(from_node_id: str, to_node_id: str, max_depth: int = 6) -> str:
    """
    Find the shortest path between two nodes using BFS.

    Args:
        from_node_id: Starting node id (or name).
        to_node_id: Target node id (or name).
        max_depth: Maximum hops to search (default 6).
    """

    def resolve(query: str) -> str | None:
        if query in _id_to_node:
            return query
        matches = [n for n in _graph.nodes if n.name.lower() == query.lower()]
        return matches[0].id if matches else None

    src = resolve(from_node_id)
    dst = resolve(to_node_id)

    if not src:
        return json.dumps({"error": f"Start node '{from_node_id}' not found."})
    if not dst:
        return json.dumps({"error": f"End node '{to_node_id}' not found."})
    if src == dst:
        return json.dumps({"path": [_node_to_dict(_id_to_node[src])], "hops": 0})

    # BFS over undirected graph
    queue: deque[tuple[str, list[str]]] = deque([(src, [src])])
    visited: set[str] = {src}

    while queue:
        current_id, path = queue.popleft()
        if len(path) > max_depth + 1:
            break
        neighbors: list[str] = []
        for e in _outgoing.get(current_id, []):
            neighbors.append(e.to_id)
        for e in _incoming.get(current_id, []):
            neighbors.append(e.from_id)
        for neighbor_id in neighbors:
            if neighbor_id not in visited:
                new_path = path + [neighbor_id]
                if neighbor_id == dst:
                    return json.dumps(
                        {
                            "path": [_node_to_dict(_id_to_node[nid]) for nid in new_path if nid in _id_to_node],
                            "hops": len(new_path) - 1,
                        },
                        indent=2,
                    )
                visited.add(neighbor_id)
                queue.append((neighbor_id, new_path))

    return json.dumps({"error": f"No path found within {max_depth} hops."})


@mcp.tool()
def search(query: str) -> str:
    """
    Fuzzy search across node names, ids, types, and property values.

    Args:
        query: Search string (case-insensitive substring match).
    """
    q = query.lower()
    results: list[dict[str, Any]] = []

    for node in _graph.nodes:
        score = 0
        if q in node.name.lower():
            score += 3
        if q in node.id.lower():
            score += 2
        if q in node.type.lower():
            score += 1
        for v in node.properties.values():
            if q in str(v).lower():
                score += 1
        if score > 0:
            d = _node_to_dict(node)
            d["_score"] = score
            results.append(d)

    results.sort(key=lambda x: x["_score"], reverse=True)
    for r in results:
        del r["_score"]

    return json.dumps(results, indent=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def serve(graph_path: Path) -> None:
    """Load the graph and start the MCP stdio server."""
    _load(graph_path)
    mcp.run(transport="stdio")
