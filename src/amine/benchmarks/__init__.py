"""
Benchmark subpackage for AMINE.

This package groups the alternative clustering back-ends (Louvain, DBSCAN,
OPTICS, FLAME, affinity propagation, ...), the alternative embedding models
(node2vec, fastText, PecanPy, spectral, SVD, random walk) and the
preprocessing strategies (original, keep_edges, merge, none) that were used
to produce the comparison table ``methods.xlsx``.

The code here is a faithful port of the experimental code that lived in
``old_code/active_module_detection/amine``. It is kept separate from the
production core (``amine``) so that the reference implementation used by the
CLI and the web application stays small and auditable, while the benchmark
grid remains fully reproducible.
"""
