"""Unit tests for the scoring methods (structural / range assertions)."""

import networkx as nx
import pytest

from amine.scores import Scores


def _clique_graph(nb_nodes: int = 10) -> nx.Graph:
    G = nx.complete_graph(nb_nodes)
    for node in G.nodes:
        G.nodes[node]["weight"] = 0.01
    for u, v in G.edges:
        G.edges[u, v]["weight"] = 0.9
    G.graph["nb_nodes"] = nb_nodes
    return G


def test_density_of_clique_is_one():
    G = _clique_graph()
    assert Scores.density(G, set(G.nodes)) == pytest.approx(1.0)


def test_clustering_of_clique_is_one():
    G = _clique_graph()
    assert Scores.clustering(G, set(G.nodes)) == pytest.approx(1.0)


def test_aggregation_from_pvalue_is_finite():
    G = _clique_graph()
    value = Scores.aggregation_from_pvalue(G, set(G.nodes), "weight")
    assert value == value  # not NaN
    assert value > 0


def test_measure_f1_perfect_prediction():
    G = _clique_graph()
    cluster = set(G.nodes)
    assert Scores.measure_f1(G, cluster, cluster) == pytest.approx(1.0)


def test_measure_f1_disjoint_prediction():
    G = _clique_graph(20)
    real = set(list(G.nodes)[:10])
    pred = set(list(G.nodes)[10:])
    assert Scores.measure_f1(G, real, pred) == pytest.approx(0.0)
