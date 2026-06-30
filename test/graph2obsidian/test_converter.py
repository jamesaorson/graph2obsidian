"""Tests for graph2obsidian converter."""

import json
import textwrap
from pathlib import Path

import pytest

from graph2obsidian.converter import _slug, convert
from graph2obsidian.models import Edge, Graph, Node
from graph2obsidian.parser import parse_graph

# ---------------------------------------------------------------------------
# _slug
# ---------------------------------------------------------------------------


def test_slug_simple():
    assert _slug("John Doe") == "John Doe"


def test_slug_strips_illegal_chars():
    assert _slug('Bad/Name:Here"') == "Bad_Name_Here_"


def test_slug_collapses_whitespace():
    assert _slug("Too   Many   Spaces") == "Too Many Spaces"


# ---------------------------------------------------------------------------
# parse_graph
# ---------------------------------------------------------------------------

SAMPLE_GRAPH = {
    "nodes": [
        {"id": "alice", "name": "Alice", "type": "Person", "properties": {"age": 30}},
        {"id": "acme", "name": "Acme Corp", "type": "Organization", "properties": {"industry": "tech"}},
    ],
    "edges": [
        {
            "from": "acme",
            "to": "alice",
            "relationship": "EMPLOYS",
            "properties": {"since": 2020},
        }
    ],
}


def test_parse_graph_nodes():
    graph = parse_graph(SAMPLE_GRAPH)
    assert len(graph.nodes) == 2
    assert graph.nodes[0].id == "alice"
    assert graph.nodes[0].name == "Alice"
    assert graph.nodes[0].type == "Person"
    assert graph.nodes[0].properties == {"age": 30}


def test_parse_graph_edges():
    graph = parse_graph(SAMPLE_GRAPH)
    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert edge.from_id == "acme"
    assert edge.to_id == "alice"
    assert edge.relationship == "EMPLOYS"
    assert edge.properties == {"since": 2020}


def test_parse_graph_defaults():
    data = {"nodes": [{"id": "x", "name": "X"}], "edges": []}
    graph = parse_graph(data)
    assert graph.nodes[0].type == "Node"
    assert graph.nodes[0].properties == {}


# ---------------------------------------------------------------------------
# convert
# ---------------------------------------------------------------------------


def test_convert_creates_files(tmp_path):
    graph = parse_graph(SAMPLE_GRAPH)
    written = convert(graph, tmp_path)
    names = {p.name for p in written}
    assert "Alice.md" in names
    assert "Acme Corp.md" in names


def test_convert_frontmatter(tmp_path):
    graph = parse_graph(SAMPLE_GRAPH)
    convert(graph, tmp_path)
    content = (tmp_path / "Alice.md").read_text()
    assert "type: Person" in content
    assert "id: alice" in content
    assert "age: 30" in content


def test_convert_outgoing_link(tmp_path):
    graph = parse_graph(SAMPLE_GRAPH)
    convert(graph, tmp_path)
    acme_content = (tmp_path / "Acme Corp.md").read_text()
    # Acme has an outgoing EMPLOYS edge to Alice
    assert "**EMPLOYS**" in acme_content
    assert "[[Alice]]" in acme_content
    assert "since=2020" in acme_content


def test_convert_incoming_link(tmp_path):
    graph = parse_graph(SAMPLE_GRAPH)
    convert(graph, tmp_path)
    alice_content = (tmp_path / "Alice.md").read_text()
    # Alice has an incoming EMPLOYS edge from Acme Corp
    assert "**EMPLOYS**" in alice_content
    assert "[[Acme Corp]]" in alice_content


def test_convert_no_relationships_section_when_isolated(tmp_path):
    graph = Graph(nodes=[Node(id="lone", name="Lone Wolf")], edges=[])
    convert(graph, tmp_path)
    content = (tmp_path / "Lone Wolf.md").read_text()
    assert "## Relationships" not in content


def test_convert_empty_graph(tmp_path):
    graph = Graph()
    written = convert(graph, tmp_path)
    assert written == []


def test_convert_creates_output_dir(tmp_path):
    graph = parse_graph(SAMPLE_GRAPH)
    out = tmp_path / "nested" / "vault"
    convert(graph, out)
    assert out.is_dir()
