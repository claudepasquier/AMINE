# AMINE — Active Module Identification through Network Embedding

[![Koda CI](https://src.koda.cnrs.fr/i3s-research/amine/badges/main/pipeline.svg)](https://src.koda.cnrs.fr/i3s-research/amine/-/pipelines)
[![GitHub CI](https://github.com/claudepasquier/amine/actions/workflows/ci.yml/badge.svg)](https://github.com/claudepasquier/amine/actions/workflows/ci.yml)
[![License: GPL v3+](https://img.shields.io/badge/License-GPLv3%2B-blue.svg)](LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.0000000.svg)](https://doi.org/10.5281/zenodo.0000000)

AMINE identifies active modules (connected sets of genes) in biological
interaction networks by combining network embedding (node2vec) with a greedy
module search and a statistical background correction. It was introduced in:

> A network embedding approach to identify active modules in biological
> interaction networks. C. Pasquier, V. Guerlais, D. Pallez, R. Rapetti-Mauss,
> O. Soriani. *Life Science Alliance* 6(9), 2023.
> <https://doi.org/10.26508/lsa.202201550>

This repository is the unified, modernized version of the software. It merges
the published GitHub release, the former Django web server, and the benchmark
workspace used to compare AMINE with competing tools.

## Modernization at a glance

| Area              | Before                                   | After                                             |
| ----------------- | ---------------------------------------- | ------------------------------------------------- |
| Packaging         | `environment.yml` + `setup` scripts      | `pyproject.toml`, `pip install -e ".[web,dev]"`   |
| Python            | 3.6                                      | >= 3.10 (tested on 3.10–3.12)                     |
| Progress bars     | `progressbar2` (unmaintained)            | `tqdm`                                            |
| Web server        | Django + Huey + SQLite                   | FastAPI + `ProcessPoolExecutor` (JSON job state)  |
| Deployment        | dedicated server                         | any free container host (Docker image provided)   |
| Tests             | ad-hoc scripts                           | `pytest` suite incl. golden parity vs. the paper  |
| CI                | none                                     | Koda (master) + GitHub mirror (lint, tests, Docker) |
| Benchmarks        | scattered experimental code              | `benchmarks/` + reproducible grid driver          |
| Comparison table  | `methods.xlsx` (46 tools)                | `benchmarks/methods.xlsx` (51 tools, regenerable) |

The numerical core is unchanged: a golden test-suite asserts that the unified
`scores` module reproduces the published `amine_github` results bit-for-bit.

## Features

- **Active module identification** from condition-specific gene sets
  (transcriptomic experiments) in protein–protein interaction networks.
- **Network embedding** via node2vec (vendored `pecanpy` implementation) with
  configurable walks, walk length, dimensions, window size and epochs.
- **Greedy module search** with statistical background correction; module size
  is not a fixed parameter — it adjusts to the data.
- **Multiple data sources**: STRING, BioGRID and IntAct networks for human,
  mouse, drosophila and *C. elegans*.
- **CLI and web application** for running analyses on your own data.
- **Reproducible benchmarks** against 51 competing tools (BioNet, COSINE, GIGA,
  MCODE, ClusterONE, MEGENA, PCSF, SIGNET, …).
- **Golden parity tests** guaranteeing bit-for-bit agreement with the published
  results.

## Repository layout

```
src/amine/          Core library (single source of truth) + CLI entry points
web/                FastAPI web application (replaces the old Django + Huey stack)
benchmarks/         Benchmark drivers, competitor sources, methods.xlsx
docs/               Documentation and archived paper references
tests/              Unit and golden tests
legacy/             Original Django app and old scripts, kept for provenance
```

## Installation

Python >= 3.10 is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

For the web application:

```bash
pip install -e ".[web]"
```

Conda users can still use the pinned `environment.yml`.

## Downloading the interaction networks

```bash
python -m amine.download_data
```

Networks are written to `data/real/ppi/`. Supported sources: STRING, BioGRID,
IntAct, for human, mouse, drosophila and *C. elegans*.

## Command-line usage

### Real data

```bash
python -m amine \
  --expvalue ./data/real/expression/chiou_2017/Hmga2_positive_vs_negative.csv \
  -g 0 -l 2 -p 6 -s mouse -n string \
  -o ./data/results/Hmga2_positive_vs_negative_string_network.xlsx -v
```

### Artificial networks

```bash
python -m amine.process_artificial_network -g guyondata -r 1000 -m 10 -n 3 \
  -o ./data/results/guyon.txt -v
```

### Web application

```bash
uvicorn web.api.main:app --reload
```

Then open <http://localhost:8000>. Upload an expression file, choose the
species and network, and download the resulting `.xlsx`.

A step-by-step guide for running and deploying the application (local test,
generic server deployment, Koda/CNRS GitLab) is in
[`docs/operator-guide.md`](docs/operator-guide.md). Deployment requirements and
options are described provider-neutrally in
[`docs/deployment.md`](docs/deployment.md).

## Benchmarks

The `benchmarks/` directory preserves the sources of the competing tools
(BioNet, COSINE, GIGA) and provides reproducible drivers for the artificial
network grid and the real TCGA runs:

```bash
python benchmarks/run_grid.py --dry-run     # inspect the preproc × embed × cluster grid
python benchmarks/update_methods_table.py   # regenerate benchmarks/methods.xlsx
```

The comparison table `benchmarks/methods.xlsx` lists 51 tools (the 46 from the
original study plus MCODE, ClusterONE, MEGENA, PCSF and SIGNET). See
[`benchmarks/README.md`](benchmarks/README.md) and
[`benchmarks/competitors/SOURCES.md`](benchmarks/competitors/SOURCES.md).

## Citation

If you use AMINE, please cite the Life Science Alliance paper above. In APA
format:

> Pasquier, C., Guerlais, V., Pallez, D., Rapetti-Mauss, R., & Soriani, O.
> (2023). A network embedding approach to identify active modules in biological
> interaction networks. *Life Science Alliance*, 6(9), e202201550.
> https://doi.org/10.26508/lsa.202201550

A machine-readable citation is provided in [`CITATION.cff`](CITATION.cff).

## Authors

AMINE was developed by Claude Pasquier, Vincent Guerlais, Denis Pallez,
Raphaël Rapetti-Mauss and Olivier Soriani. See [`AUTHORS.md`](AUTHORS.md) for
the full list of contributors, affiliations and roles.

## License

GPL-3.0-or-later. See [`LICENSE`](LICENSE). The vendored `pecanpy` code keeps
its own license (`src/amine/dimension_reduction/pecanpy/LICENCE.md`).
