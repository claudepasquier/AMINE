# Migration notes

This document records the decisions taken while modernizing the code base.

## Source copies

| Copy                                   | Role                                   | Decision                          |
| -------------------------------------- | -------------------------------------- | --------------------------------- |
| `legacy/amine/`                        | published GitHub release               | **reference** for the core        |
| `legacy/amine_web/.../module_detection_core` | forked copy used by the Django server | discarded, web logic re-implemented |

The experimental benchmark workspace was ported into `src/amine/benchmarks`. The remaining historical copies are kept under `legacy/` (see [`legacy/README.md`](../legacy/README.md)).

## Core reconciliation

The only web-specific behaviour worth keeping was the ability to limit the
number of returned modules. It was folded into the unified core as an optional
parameter:

```python
def process(..., nb_modules_to_find: Optional[int] = None):
    ...
    results = module_detection.predict_modules(
        relevant_nodes, max_nb_modules=nb_modules_to_find, cutoff=0.05
    )
```

It is exposed on the CLI as `-k/--nb_modules` and used by the web front-end.
The default (`None`) preserves the published behaviour exactly.

## Modernization changes

| Change                                   | Rationale                                            |
| ---------------------------------------- | ---------------------------------------------------- |
| `progressbar2` → `tqdm`                  | `progressbar2` is unmaintained                       |
| `np.float_` → `np.float64`               | `np.float_` was removed in NumPy 2.0                 |
| `Optional[...]` type hints               | the functions already accepted `None`                |
| seeded RNG in `get_scale_free_graph`     | the global `random` module broke reproducibility     |
| removed dead gencat config variables     | they were never passed to `gencat_active`            |
| removed a no-op comparison               | `aggregation_method == "pvalue"` had no effect       |
| `pyproject.toml` + Python >= 3.10        | modern packaging and supported interpreter           |

## Web stack replacement

The Django + Huey + SQLite stack was replaced by FastAPI + a
`ProcessPoolExecutor` with JSON job files. The rationale is documented in
[`docs/architecture.md`](architecture.md) and [`web/README.md`](../web/README.md).

## What was *not* changed

The numerical core (scoring, module search, embedding) is intentionally
untouched. The golden tests in `tests/test_parity_github.py` assert bit-for-bit
equality with the published version, so any future change to the core that
alters results will be caught immediately.
