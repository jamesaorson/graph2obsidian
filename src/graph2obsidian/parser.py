"""Parse graph JSON input into Graph model."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from graph2obsidian.models import Edge, Graph, Node


def _parse_node(raw: dict[str, Any]) -> Node:
    return Node(
        id=raw["id"],
        name=raw["name"],
        type=raw.get("type", "Node"),
        properties=raw.get("properties", {}),
    )


def _parse_edge(raw: dict[str, Any]) -> Edge:
    return Edge(
        from_id=raw["from"],
        to_id=raw["to"],
        relationship=raw["relationship"],
        properties=raw.get("properties", {}),
    )


def parse_graph(data: dict[str, Any]) -> Graph:
    """Parse a raw dict into a Graph."""
    nodes = [_parse_node(n) for n in data.get("nodes", [])]
    edges = [_parse_edge(e) for e in data.get("edges", [])]
    return Graph(nodes=nodes, edges=edges)


def load_graph(path: Path) -> Graph:
    """Load a Graph from a JSON file."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return parse_graph(data)
