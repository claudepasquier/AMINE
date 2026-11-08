"""Golden / parity tests against the published ``amine_github`` version.

The unified core in ``src/amine`` is derived from the version published on
GitHub (``old_code/amine_github/amine``). These tests load the historical
``scores.py`` as a standalone module and assert that the unified core produces
bit-for-bit identical scores on the same graphs. This is the "golden test"
strategy described in ``plans/amine-modernization-plan.md``: the published
version is the reference, and the refactoring must not change its numerical
behaviour.
"""

import importlib.util
import pathlib

import networkx as nx
import pytest

from amine.scores import Scores as NewScores

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
# The reference implementation is bundled under tests/reference/ so that the
# golden tests run without the (large, git-ignored) old_code/ directory. If the
# bundled copy is absent we fall back to the original location.
REFERENCE_SCORES = (
    pathlib.Path(__file__).resolve().parent / "reference" / "old_amine_scores.py"
)
LEGACY_SCORES = REPO_ROOT / "old_code" / "amine_github" / "amine" / "scores.py"
OLD_SCORES_PATH = REFERENCE_SCORES if REFERENCE_SCORES.is_file() else LEGACY_SCORES


def _load_old_scores():
    """Load the historical ``scores.py`` under a private module name."""
    spec = importlib.util.spec_from_file_location("old_amine_scores", OLD_SCORES_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Scores


@pytest.fixture(scope="module")
def old_scores():
    if not OLD_SCORES_PATH.is_file():
        pytest.skip("historical amine_github sources are not available")
    return _load_old_scores()


def _make_graph(seed: int = 0, nb_nodes: int = 40) -> nx.Graph:
    """Build a deterministic weighted graph with a planted dense module."""
    G = nx.barabasi_albert_graph(nb_nodes, 2, seed=seed)
    rng = __import__("random").Random(seed)
    for node in G.nodes:
        G.nodes[node]["weight"] = rng.uniform(0.001, 0.999)
    for u, v in G.edges:
        G.edges[u, v]["weight"] = rng.uniform(0.1, 1.0)
    G.graph["nb_nodes"] = nb_nodes
    G.graph["nb_edges"] = G.number_of_edges()
    return G


def test_aggregation_from_pvalue_matches(old_scores):
    G = _make_graph()
    cluster = set(list(G.nodes)[:8])
    assert NewScores.aggregation_from_pvalue(G, cluster, "weight") == pytest.approx(
        old_scores.aggregation_from_pvalue(G, cluster, "weight")
    )


def test_modularity_matches(old_scores):
    G = _make_graph()
    cluster = set(list(G.nodes)[:8])
    assert NewScores.modularity(G, cluster) == pytest.approx(
        old_scores.modularity(G, cluster)
    )


def test_density_matches(old_scores):
    G = _make_graph()
    cluster = set(list(G.nodes)[:8])
    assert NewScores.density(G, cluster) == pytest.approx(
        old_scores.density(G, cluster)
    )


def test_clustering_matches(old_scores):
    G = _make_graph()
    cluster = set(list(G.nodes)[:8])
    assert NewScores.clustering(G, cluster) == pytest.approx(
        old_scores.clustering(G, cluster)
    )


def test_normalized_cut_matches(old_scores):
    G = _make_graph()
    cluster = set(list(G.nodes)[:8])
    assert NewScores.normalized_cut(G, cluster) == pytest.approx(
        old_scores.normalized_cut(G, cluster)
    )


def test_average_shortest_path_matches(old_scores):
    G = _make_graph()
    cluster = set(list(G.nodes)[:8])
    assert NewScores.average_shortest_path(G, cluster) == pytest.approx(
        old_scores.average_shortest_path(G, cluster)
    )


def test_nina_metrics_matches(old_scores):
    G = _make_graph()
    cluster = set(list(G.nodes)[:8])
    assert NewScores.nina_metrics(G, cluster, "weight") == pytest.approx(
        old_scores.nina_metrics(G, cluster, "weight")
    )


def test_fisher_on_edges_matches(old_scores):
    G = _make_graph()
    cluster = set(list(G.nodes)[:8])
    assert NewScores.fisher_on_edges(G, cluster, "weight") == pytest.approx(
        old_scores.fisher_on_edges(G, cluster, "weight")
    )


def test_aggregation_from_normdist_matches(old_scores):
    G = _make_graph()
    cluster = set(list(G.nodes)[:8])
    assert NewScores.aggregation_from_normdist(G, cluster, "weight") == pytest.approx(
        old_scores.aggregation_from_normdist(G, cluster, "weight")
    )


def test_hypergeometric_score_matches(old_scores):
    G = _make_graph()
    cluster = set(list(G.nodes)[:8])
    assert NewScores.hypergeometric_score(G, cluster, "weight") == pytest.approx(
        old_scores.hypergeometric_score(G, cluster, "weight")
    )


def test_measure_f1_matches(old_scores):
    G = _make_graph()
    real = set(list(G.nodes)[:8])
    pred = set(list(G.nodes)[4:12])
    assert NewScores.measure_f1(G, real, pred) == pytest.approx(
        old_scores.measure_f1(G, real, pred)
    )
