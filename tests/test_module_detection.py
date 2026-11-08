"""End-to-end test of the module-detection algorithm on a synthetic graph.

Two dense cliques are joined by a single edge so that the whole graph is a
single connected component (required by the background-correction step). The
nodes of the first clique are given very small p-values, so the algorithm is
expected to recover that clique as its top module.
"""

import networkx as nx

from amine import models
from amine.module_detection import ModuleDetection
from amine.scores import Scores

CLIQUE_SIZE = 10


def _two_cliques() -> nx.Graph:
    G = nx.Graph()
    clique_a = list(range(CLIQUE_SIZE))
    clique_b = list(range(CLIQUE_SIZE, 2 * CLIQUE_SIZE))
    G.add_nodes_from(clique_a + clique_b)
    for clique in (clique_a, clique_b):
        for i, u in enumerate(clique):
            for v in clique[i + 1 :]:
                G.add_edge(u, v, weight=0.9)
    # single bridge edge -> one connected component
    G.add_edge(clique_a[0], clique_b[0], weight=0.9)
    for node in clique_a:
        G.nodes[node]["weight"] = 0.001
    for node in clique_b:
        G.nodes[node]["weight"] = 0.5
    G.graph["nb_nodes"] = 2 * CLIQUE_SIZE
    return G


def test_predict_modules_recovers_planted_clique():
    G = _two_cliques()
    model = models.SVD()
    model.init(G)
    fitness_fun = lambda the_graph, clus: Scores.aggregation_from_pvalue(
        the_graph, clus, "weight"
    )
    detection = ModuleDetection(G, model, fitness_fun, background_correction=False)
    results = detection.predict_modules(cutoff=None)

    assert results, "at least one module should be predicted"
    top_module = set(results[0][0])
    clique_a = set(range(CLIQUE_SIZE))
    clique_b = set(range(CLIQUE_SIZE, 2 * CLIQUE_SIZE))
    # the top module must be dominated by the low-p-value clique
    assert len(top_module & clique_a) > len(top_module & clique_b)


def test_max_nb_modules_limits_results():
    G = _two_cliques()
    model = models.SVD()
    model.init(G)
    fitness_fun = lambda the_graph, clus: Scores.aggregation_from_pvalue(
        the_graph, clus, "weight"
    )
    detection = ModuleDetection(G, model, fitness_fun, background_correction=False)
    results = detection.predict_modules(max_nb_modules=1, cutoff=None)
    assert len(results) <= 1
