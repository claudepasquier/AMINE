# AMINE architecture

## One core, two front-ends

The unified code base follows a strict "one core, two front-ends" design:

```
                    ┌──────────────────────────┐
                    │        src/amine         │
                    │  (numerical core + CLI)  │
                    └────────────┬─────────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              │                                     │
     ┌────────▼────────┐                   ┌────────▼────────┐
     │  CLI (__main__) │                   │  web/ (FastAPI) │
     │  python -m amine│                   │  uvicorn ...    │
     └─────────────────┘                   └─────────────────┘
```

Both front-ends call the same function,
[`amine.process_real_network.process()`](../src/amine/process_real_network.py),
so there is a single implementation of the algorithm and a single place to fix
bugs.

## Core package (`src/amine`)

| Module                       | Responsibility                                        |
| ---------------------------- | ----------------------------------------------------- |
| `process_real_network.py`    | end-to-end pipeline for real expression data          |
| `process_artificial_network.py` | pipeline for synthetic graphs                      |
| `module_detection.py`        | greedy module search + background correction          |
| `models.py`                  | embedding models (node2vec, random walk, SVD)         |
| `scores.py`                  | fitness functions and accuracy measures               |
| `datasets.py`                | network loading and synthetic graph generation        |
| `parameters.py`              | configuration (`config.yaml`)                         |
| `download_data.py`           | download STRING / BioGRID / IntAct networks           |
| `arg_parser.py`              | CLI argument parsing                                  |
| `benchmarks/`                | alternative back-ends and the benchmark grid          |

## Web application (`web/`)

The historical Django + Huey + SQLite server was replaced by a single FastAPI
process:

* **HTTP** — FastAPI + uvicorn.
* **Background work** — a `ProcessPoolExecutor`; the event loop is never
  blocked.
* **State** — one JSON file per job under `jobs/`; no database.
* **Front-end** — a single Jinja2 page with vanilla JavaScript polling.

This design is stateless and therefore trivial to deploy on free container
hosts. See [`web/README.md`](../web/README.md) for the endpoint reference.

## Benchmarks (`benchmarks/`)

The benchmark workspace is preserved separately from the production core:

* `competitors/` — third-party tools (BioNet, COSINE, GIGA) kept verbatim for
  reproducibility, with provenance in `SOURCES.md`;
* `run_grid.py` — driver for the preprocessing × embedding × clustering grid;
* `update_methods_table.py` — regenerates `methods.xlsx`.

The alternative back-ends themselves live in `src/amine/benchmarks/` so that
they can be imported and unit-tested, but they are excluded from linting to
stay close to their original source.

## Testing strategy

* **Golden / parity tests** (`tests/test_parity_github.py`) load the published
  `old_code/amine_github/amine/scores.py` and assert that the unified core
  produces identical scores. This guarantees the refactoring did not change the
  numerical behaviour.
* **Unit tests** cover graph generation, scoring, module detection and the CLI.
* **Web tests** exercise the HTTP surface with FastAPI's `TestClient`.
