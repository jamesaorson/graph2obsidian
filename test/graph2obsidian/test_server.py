"""Tests for the graph2obsidian MCP server tools."""

import json
from pathlib import Path

import pytest

from graph2obsidian.server import (
    _load,
    find_node,
    find_path,
    graph_stats,
    node_neighbors,
    query_edges,
    search,
)

FIXTURE = Path(__file__).parent.parent / "fixtures" / "demo.json"


@pytest.fixture(autouse=True)
def load_demo():
    _load(FIXTURE)


# ---------------------------------------------------------------------------
# graph_stats
# ---------------------------------------------------------------------------


def test_graph_stats_node_count():
    data = json.loads(graph_stats())
    assert data["node_count"] == 4


def test_graph_stats_edge_count():
    data = json.loads(graph_stats())
    assert data["edge_count"] == 4


def test_graph_stats_node_types():
    data = json.loads(graph_stats())
    assert data["node_types"]["Person"] == 1
    assert data["node_types"]["Organization"] == 3


def test_graph_stats_relationship_types():
    data = json.loads(graph_stats())
    assert "DONATED_TO" in data["relationship_types"]
    assert "FUNDS" in data["relationship_types"]


# ---------------------------------------------------------------------------
# find_node
# ---------------------------------------------------------------------------


def test_find_node_by_name():
    results = json.loads(find_node("senator"))
    assert len(results) == 1
    assert results[0]["name"] == "Senator Jane Doe"


def test_find_node_by_id():
    results = json.loads(find_node("big_oil_pac", search_type="id"))
    assert len(results) == 1
    assert results[0]["id"] == "big_oil_pac"


def test_find_node_by_type():
    results = json.loads(find_node("Organization", search_type="type"))
    assert len(results) == 3


def test_find_node_no_match():
    results = json.loads(find_node("xyzzy"))
    assert results == []


# ---------------------------------------------------------------------------
# node_neighbors
# ---------------------------------------------------------------------------


def test_node_neighbors_both():
    data = json.loads(node_neighbors("senator_doe"))
    assert data["node"]["id"] == "senator_doe"
    assert len(data["outgoing"]) == 1  # ENDORSED
    assert len(data["incoming"]) == 2  # DONATED_TO + EMPLOYED_BEFORE


def test_node_neighbors_outgoing_only():
    data = json.loads(node_neighbors("senator_doe", direction="outgoing"))
    assert "incoming" not in data
    assert len(data["outgoing"]) == 1


def test_node_neighbors_incoming_only():
    data = json.loads(node_neighbors("senator_doe", direction="incoming"))
    assert "outgoing" not in data
    assert len(data["incoming"]) == 2


def test_node_neighbors_by_name():
    data = json.loads(node_neighbors("Senator Jane Doe"))
    assert data["node"]["id"] == "senator_doe"


def test_node_neighbors_not_found():
    data = json.loads(node_neighbors("ghost_node"))
    assert "error" in data


# ---------------------------------------------------------------------------
# query_edges
# ---------------------------------------------------------------------------


def test_query_edges_by_relationship():
    edges = json.loads(query_edges("DONATED_TO"))
    assert len(edges) == 1
    assert edges[0]["relationship"] == "DONATED_TO"


def test_query_edges_numeric_gt():
    edges = json.loads(query_edges("DONATED_TO", "amount_usd", "100000", "gt"))
    assert len(edges) == 1


def test_query_edges_numeric_gt_no_match():
    edges = json.loads(query_edges("DONATED_TO", "amount_usd", "1000000", "gt"))
    assert len(edges) == 0


def test_query_edges_string_contains():
    edges = json.loads(query_edges("EMPLOYED_BEFORE", "role", "Advisor", "contains"))
    assert len(edges) == 1


def test_query_edges_no_match_relationship():
    edges = json.loads(query_edges("NONEXISTENT"))
    assert edges == []


# ---------------------------------------------------------------------------
# find_path
# ---------------------------------------------------------------------------


def test_find_path_direct():
    data = json.loads(find_path("senator_doe", "clean_future_ngo"))
    assert data["hops"] == 1
    ids = [n["id"] for n in data["path"]]
    assert "senator_doe" in ids
    assert "clean_future_ngo" in ids


def test_find_path_two_hops():
    data = json.loads(find_path("meridian_energy", "clean_future_ngo"))
    assert data["hops"] == 2


def test_find_path_same_node():
    data = json.loads(find_path("senator_doe", "senator_doe"))
    assert data["hops"] == 0


def test_find_path_not_found():
    # Load a disconnected node scenario by querying a nonexistent node
    data = json.loads(find_path("senator_doe", "ghost_999"))
    assert "error" in data


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


def test_search_by_name():
    results = json.loads(search("oil"))
    names = [r["name"] for r in results]
    assert "Big Oil PAC" in names
    assert "Meridian Energy Corp" in names


def test_search_by_property():
    results = json.loads(search("climate"))
    assert len(results) >= 1
    assert results[0]["id"] == "clean_future_ngo"


def test_search_no_match():
    results = json.loads(search("xyzzy_no_match"))
    assert results == []


def test_search_name_ranks_higher():
    # "pac" appears in Big Oil PAC name — should score higher than
    # something that only matches in a property
    results = json.loads(search("pac"))
    assert results[0]["name"] == "Big Oil PAC"
