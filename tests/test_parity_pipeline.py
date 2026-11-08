"""End-to-end parity test of the module-detection pipeline.

The golden tests in :mod:`tests.test_parity_github` compare the individual
scoring functions. This module goes one step further and runs the *whole*
``ModuleDetection.predict_modules`` pipeline with both the historical
``old_code/amine_github`` implementation and the refactored ``src/amine``
implementation on the same deterministic graph, asserting that they return
exactly the same modules (same node sets, same z-scores, same p-values).

The historical package is loaded under the private name ``old_amine`` so that
its relative imports resolve to its own bundled ``models``/``scores`` modules
without clashing with the installed ``amine`` package.
"""

import importlib
import importlib.util
import pathlib
import sys
from random import Random

import networkx as nx
import numpy as np
import pytest

# The historical sources use ``np.float_``, an alias for ``np.float64`` that was
# removed in NumPy 2.0. The refactoring replaced it with ``np.float64`` (an exact
# rename, no behavioural change). Restore the alias so the reference code can run
# unchanged on a modern NumPy and be compared fairly.
if not hasattr(np, "float_"):
    np.float_ = np.float64

from amine import models as new_models
from amine import module_detection as new_module_detection
from amine.scores import Scores as NewScores

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
OLD_PACKAGE_DIR = REPO_ROOT / "old_code" / "amine_github" / "amine"

CLIQUE_SIZE = 10
SEED = 1234


def _load_old_package():
    """Import ``old_code/amine_github/amine`` as the private package ``old_amine``."""
    if not OLD_PACKAGE_DIR.is_dir():
        pytest.skip("historical amine_github sources are not available")
    if "old_amine" in sys.modules:
        return sys.modules["old_amine"]
    spec = importlib.util.spec_from_file_location(
        "old_amine",
        OLD_PACKAGE_DIR / "__init__.py",
        submodule_search_locations=[str(OLD_PACKAGE_DIR)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["old_amine"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def old_amine():
    _load_old_package()
    return {
        "module_detection": importlib.import_module("old_amine.module_detection"),
        "models": importlib.import_module("old_amine.models"),
        "scores": importlib.import_module("old_amine.scores"),
    }


def _two_cliques() -> nx.Graph:
    """Two dense cliques joined by a single edge (one connected component)."""
    G = nx.Graph()
    clique_a = list(range(CLIQUE_SIZE))
    clique_b = list(range(CLIQUE_SIZE, 2 * CLIQUE_SIZE))
    G.add_nodes_from(clique_a + clique_b)
    for clique in (clique_a, clique_b):
        for i, u in enumerate(clique):
            for v in clique[i + 1 :]:
                G.add_edge(u, v, weight=0.9)
    G.add_edge(clique_a[0], clique_b[0], weight=0.9)
    for node in clique_a:
        G.nodes[node]["weight"] = 0.001
    for node in clique_b:
        G.nodes[node]["weight"] = 0.5
    G.graph["nb_nodes"] = 2 * CLIQUE_SIZE
    G.graph["nb_edges"] = G.number_of_edges()
    return G


def _run_pipeline(module_detection_mod, models_mod, scores_cls, G):
    """Run the full detection pipeline with a fixed RNG seed."""
    model = models_mod.SVD()
    model.init(G)
    fitness = lambda graph, clus: scores_cls.aggregation_from_pvalue(  # noqa: E731
        graph, clus, "weight"
    )
    detection = module_detection_mod.ModuleDetection(
        G, model, fitness, background_correction=False
    )
    # ``predict_modules`` uses ``self.rng`` for the final background correction;
    # seed it so both implementations are directly comparable.
    detection.rng = Random(SEED)
    return detection.predict_modules(cutoff=None)


def test_full_pipeline_matches_old_implementation(old_amine):
    G_new = _two_cliques()
    G_old = _two_cliques()

    new_results = _run_pipeline(new_module_detection, new_models, NewScores, G_new)
    old_results = _run_pipeline(
        old_amine["module_detection"],
        old_amine["models"],
        old_amine["scores"].Scores,
        G_old,
    )

    assert new_results, "the pipeline should predict at least one module"
    assert len(new_results) == len(old_results)

    for new_mod, old_mod in zip(new_results, old_results):
        new_nodes, new_zscore, new_pvalue = new_mod
        old_nodes, old_zscore, old_pvalue = old_mod
        assert new_nodes == old_nodes
        assert new_zscore == pytest.approx(old_zscore)
        assert new_pvalue == pytest.approx(old_pvalue)


def test_svd_embeddings_match_old_implementation(old_amine):
    """The SVD model must produce identical similarity rankings."""
    G_new = _two_cliques()
    G_old = _two_cliques()

    new_model = new_models.SVD()
    new_model.init(G_new)
    old_model = old_amine["models"].SVD()
    old_model.init(G_old)

    for node in G_new.nodes:
        assert new_model.get_most_similar(node, 5) == old_model.get_most_similar(
            node, 5
        )
