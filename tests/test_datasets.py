"""Unit tests for deterministic graph generation in :mod:`amine.datasets`."""

import networkx as nx

from amine.datasets import Datasets


def test_scale_free_graph_node_count():
    G = Datasets.get_scale_free_graph(100, 3, 2, 10, 0.09, 0.70, 42)
    assert isinstance(G, nx.Graph)
    assert len(G.nodes) == 100


def test_scale_free_graph_is_deterministic():
    G1 = Datasets.get_scale_free_graph(80, 3, 2, 10, 0.09, 0.70, 7)
    G2 = Datasets.get_scale_free_graph(80, 3, 2, 10, 0.09, 0.70, 7)
    assert set(G1.nodes) == set(G2.nodes)
    assert {frozenset(e) for e in G1.edges} == {frozenset(e) for e in G2.edges}


def test_scale_free_graph_has_weights():
    G = Datasets.get_scale_free_graph(60, 3, 1, 10, 0.09, 0.70, 1)
    assert all("weight" in data for _, data in G.nodes(data=True))
