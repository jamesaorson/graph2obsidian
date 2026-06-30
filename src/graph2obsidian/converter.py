"""Convert a Graph into an Obsidian + Dataview vault."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from graph2obsidian.models import Edge, Graph, Node

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DATAVIEW_PLUGIN = "Dataview"
DATAVIEW_URL = "https://github.com/blacksmithgu/obsidian-dataview"


def _slug(name: str) -> str:
    """Convert a node name into a safe filename (no extension)."""
    slug = name.strip()
    slug = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", slug)
    slug = re.sub(r"\s+", " ", slug)
    return slug


def _format_inline_fields(props: dict[str, Any]) -> str:
    """Render edge properties as Dataview inline fields (key:: value)."""
    if not props:
        return ""
    parts = [f"{k}:: {v}" for k, v in props.items()]
    return " | " + " | ".join(parts)


# ---------------------------------------------------------------------------
# Node note renderer
# ---------------------------------------------------------------------------


def _render_node(node: Node, outgoing: list[Edge], incoming: list[Edge], id_to_node: dict[str, Node]) -> str:
    lines: list[str] = []

    # --- YAML frontmatter ---
    frontmatter: dict[str, Any] = {
        "type": node.type,
        "id": node.id,
        "name": node.name,
        "tags": [f"graph/{node.type}"],
    }
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
            # Group by relationship type
            by_rel: dict[str, list[Edge]] = defaultdict(list)
            for edge in outgoing:
                by_rel[edge.relationship].append(edge)
            for rel, edges in by_rel.items():
                lines.append(f"#### {rel}")
                lines.append("")
                for edge in edges:
                    target = id_to_node.get(edge.to_id)
                    target_name = target.name if target else edge.to_id
                    fields = _format_inline_fields(edge.properties)
                    lines.append(f"- [[{_slug(target_name)}]]{fields}")
                lines.append("")

        if incoming:
            lines.append("### Incoming")
            lines.append("")
            by_rel_in: dict[str, list[Edge]] = defaultdict(list)
            for edge in incoming:
                by_rel_in[edge.relationship].append(edge)
            for rel, edges in by_rel_in.items():
                lines.append(f"#### {rel}")
                lines.append("")
                for edge in edges:
                    source = id_to_node.get(edge.from_id)
                    source_name = source.name if source else edge.from_id
                    fields = _format_inline_fields(edge.properties)
                    lines.append(f"- [[{_slug(source_name)}]]{fields}")
                lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Index note renderer (one per node type)
# ---------------------------------------------------------------------------


def _render_index(node_type: str, nodes: list[Node]) -> str:
    lines: list[str] = []
    lines.append(f"# {node_type} Index")
    lines.append("")
    lines.append(f"> [!info] Requires the [{DATAVIEW_PLUGIN}]({DATAVIEW_URL}) community plugin.")
    lines.append("")
    lines.append("```dataview")
    lines.append(f"TABLE name, id FROM #graph/{node_type}")
    lines.append("SORT name ASC")
    lines.append("```")
    lines.append("")
    lines.append("## All nodes")
    lines.append("")
    for node in sorted(nodes, key=lambda n: n.name):
        lines.append(f"- [[{_slug(node.name)}]]")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Vault overview note
# ---------------------------------------------------------------------------


def _render_vault_overview(graph: Graph) -> str:
    by_type: dict[str, list[Node]] = defaultdict(list)
    for node in graph.nodes:
        by_type[node.type].append(node)

    lines: list[str] = []
    lines.append("# Vault Overview")
    lines.append("")
    lines.append(
        f"> [!info] Requires the [{DATAVIEW_PLUGIN}]({DATAVIEW_URL}) community plugin " f"for the live tables below."
    )
    lines.append("")

    # Stats
    lines.append("## Stats")
    lines.append("")
    lines.append(f"- **Nodes:** {len(graph.nodes)}")
    lines.append(f"- **Edges:** {len(graph.edges)}")
    lines.append(f"- **Types:** {', '.join(sorted(by_type.keys()))}")
    lines.append("")

    # Index links
    lines.append("## Indexes")
    lines.append("")
    for t in sorted(by_type.keys()):
        lines.append(f"- [[_index/{t}]]")
    lines.append("")

    # Per-type Dataview tables
    for node_type in sorted(by_type.keys()):
        lines.append(f"## {node_type}s")
        lines.append("")
        lines.append("```dataview")
        lines.append(f"TABLE name, id FROM #graph/{node_type}")
        lines.append("SORT name ASC")
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def convert(graph: Graph, output_dir: Path) -> list[Path]:
    """
    Convert a Graph into an Obsidian + Dataview vault.

    Writes:
    - One markdown note per node
    - One index note per node type under _index/
    - A _VAULT.md overview note

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

    # Node notes
    for node in graph.nodes:
        content = _render_node(node, outgoing[node.id], incoming[node.id], id_to_node)
        path = output_dir / (_slug(node.name) + ".md")
        path.write_text(content, encoding="utf-8")
        written.append(path)

    # Index notes
    if graph.nodes:
        by_type: dict[str, list[Node]] = defaultdict(list)
        for node in graph.nodes:
            by_type[node.type].append(node)

        index_dir = output_dir / "_index"
        index_dir.mkdir(exist_ok=True)

        for node_type, nodes in by_type.items():
            content = _render_index(node_type, nodes)
            path = index_dir / (node_type + ".md")
            path.write_text(content, encoding="utf-8")
            written.append(path)

        # Vault overview
        vault_note = output_dir / "_VAULT.md"
        vault_note.write_text(_render_vault_overview(graph), encoding="utf-8")
        written.append(vault_note)

    return written
