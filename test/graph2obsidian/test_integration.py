"""Integration test: load demo fixture JSON → convert → inspect output files."""

from pathlib import Path

from graph2obsidian.converter import convert
from graph2obsidian.parser import load_graph

FIXTURE = Path(__file__).parent.parent / "fixtures" / "demo.json"


def test_demo_fixture_loads():
    graph = load_graph(FIXTURE)
    assert len(graph.nodes) == 4
    assert len(graph.edges) == 4


def test_demo_fixture_converts(tmp_path):
    graph = load_graph(FIXTURE)
    written = convert(graph, tmp_path)
    names = {p.name for p in written}

    assert "Senator Jane Doe.md" in names
    assert "Big Oil PAC.md" in names
    assert "Meridian Energy Corp.md" in names
    assert "Clean Future NGO.md" in names


def test_demo_senator_frontmatter(tmp_path):
    graph = load_graph(FIXTURE)
    convert(graph, tmp_path)
    content = (tmp_path / "Senator Jane Doe.md").read_text()

    assert "type: Person" in content
    assert "id: senator_doe" in content
    assert "state: CA" in content
    assert "party: Independent" in content
    assert "graph/Person" in content


def test_demo_senator_incoming_donations(tmp_path):
    graph = load_graph(FIXTURE)
    convert(graph, tmp_path)
    content = (tmp_path / "Senator Jane Doe.md").read_text()

    assert "DONATED_TO" in content
    assert "[[Big Oil PAC]]" in content
    assert "amount_usd:: 250000" in content

    assert "EMPLOYED_BEFORE" in content
    assert "[[Meridian Energy Corp]]" in content
    assert "role:: Board Advisor" in content


def test_demo_senator_outgoing_endorsement(tmp_path):
    graph = load_graph(FIXTURE)
    convert(graph, tmp_path)
    content = (tmp_path / "Senator Jane Doe.md").read_text()

    assert "ENDORSED" in content
    assert "[[Clean Future NGO]]" in content
    assert "year:: 2023" in content


def test_demo_meridian_funds_pac(tmp_path):
    graph = load_graph(FIXTURE)
    convert(graph, tmp_path)
    content = (tmp_path / "Meridian Energy Corp.md").read_text()

    assert "FUNDS" in content
    assert "[[Big Oil PAC]]" in content
    assert "amount_usd:: 5000000" in content


def test_demo_ngo_has_no_outgoing(tmp_path):
    graph = load_graph(FIXTURE)
    convert(graph, tmp_path)
    content = (tmp_path / "Clean Future NGO.md").read_text()

    assert "### Outgoing" not in content
    assert "### Incoming" in content
    assert "[[Senator Jane Doe]]" in content


def test_demo_index_notes_created(tmp_path):
    graph = load_graph(FIXTURE)
    convert(graph, tmp_path)
    assert (tmp_path / "_index" / "Person.md").exists()
    assert (tmp_path / "_index" / "Organization.md").exists()


def test_demo_vault_note_created(tmp_path):
    graph = load_graph(FIXTURE)
    convert(graph, tmp_path)
    vault = (tmp_path / "_VAULT.md").read_text()
    assert "**Nodes:** 4" in vault
    assert "**Edges:** 4" in vault
    assert "Dataview" in vault
