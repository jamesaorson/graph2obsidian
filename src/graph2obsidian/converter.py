"""Convert a Graph into Obsidian markdown vault files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from graph2obsidian.models import Edge, Graph, Node


def _slug(name: str) -> str:
    """Convert a node name into a safe filename (no extension)."""
    slug = name.strip()
    slug = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", slug)
    slug = re.sub(r"\s+", " ", slug)
    return slug


def _format_properties(props: dict[str, Any]) -> str:
    """Render edge/extra properties as a compact inline string."""
    if not props:
        return ""
    parts = [f"{k}={v}" for k, v in props.items()]
    return " (" + ", ".join(parts) + ")"


def _render_node(node: Node, outgoing: list[Edge], incoming: list[Edge], id_to_node: dict[str, Node]) -> str:
    """Render a single node as Obsidian markdown."""
    lines: list[str] = []

    # --- YAML frontmatter ---
    frontmatter: dict[str, Any] = {"type": node.type, "id": node.id}
    frontmatter.update(node.properties)
    lines.append("---")
    lines.append(yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True).rstrip())
    lines.append("---")
    lines.append("")

    # --- Title ---
    lines.append(f"# {node.name}")
    lines.append("")

    # --- Relationships ---
    if outgoing or incoming:
        lines.append("## Relationships")
        lines.append("")

        if outgoing:
            lines.append("### Outgoing")
            lines.append("")
            for edge in outgoing:
                target = id_to_node.get(edge.to_id)
                target_name = target.name if target else edge.to_id
                props_str = _format_properties(edge.properties)
                lines.append(f"- **{edge.relationship}** → [[{_slug(target_name)}]]{props_str}")
            lines.append("")

        if incoming:
            lines.append("### Incoming")
            lines.append("")
            for edge in incoming:
                source = id_to_node.get(edge.from_id)
                source_name = source.name if source else edge.from_id
                props_str = _format_properties(edge.properties)
                lines.append(f"- **{edge.relationship}** ← [[{_slug(source_name)}]]{props_str}")
            lines.append("")

    return "\n".join(lines)


def convert(graph: Graph, output_dir: Path) -> list[Path]:
    """
    Convert a Graph into Obsidian markdown files.

    Returns the list of files written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    id_to_node: dict[str, Node] = {n.id: n for n in graph.nodes}

    # Index edges by node id
    outgoing: dict[str, list[Edge]] = {n.id: [] for n in graph.nodes}
    incoming: dict[str, list[Edge]] = {n.id: [] for n in graph.nodes}
    for edge in graph.edges:
        if edge.from_id in outgoing:
            outgoing[edge.from_id].append(edge)
        if edge.to_id in incoming:
            incoming[edge.to_id].append(edge)

    written: list[Path] = []
    for node in graph.nodes:
        content = _render_node(node, outgoing[node.id], incoming[node.id], id_to_node)
        filename = _slug(node.name) + ".md"
        path = output_dir / filename
        path.write_text(content, encoding="utf-8")
        written.append(path)

    return written
