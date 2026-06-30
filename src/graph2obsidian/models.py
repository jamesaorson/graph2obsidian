"""Domain models for graph2obsidian."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Node:
    """A node in the graph."""

    id: str
    name: str
    type: str = "Node"
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    """A directed edge between two nodes."""

    from_id: str
    to_id: str
    relationship: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class Graph:
    """A collection of nodes and edges."""

    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
