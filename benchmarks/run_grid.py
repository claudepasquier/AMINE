#!/usr/bin/env python3
"""Drive the parameterised artificial-network benchmark grid.

The grid crosses three axes:

* **preprocessing** — ``original``, ``keep_edges``, ``merge``, ``none``
* **embedding**     — ``pecanpy``, ``node2vec``, ``fasttext``, ``spectral``,
  ``svd``, ``randomwalk``, ``none``
* **clustering**    — ``amine``, ``louvain``, ``alouvain``, ``dbscan``,
  ``optics``, ``flame``, ``affinity``, ``bestvalues``, ``in_progress``,
  ``my_flame``

For each combination it invokes
``amine.benchmarks.process_artificial_network`` and collects the resulting
per-run metrics into a single CSV file.

Because a full grid is expensive, the script supports ``--dry-run`` (print the
commands without executing them) and ``--limit`` (run only the first N
combinations).

Usage::

    python benchmarks/run_grid.py --dry-run
    python benchmarks/run_grid.py --runs 10 --output benchmarks/artificial/grid.csv
"""

from __future__ import annotations

import argparse
import itertools
import pathlib
import subprocess
import sys

PREPROCESSING = ["original", "keep_edges", "merge", "none"]
EMBEDDING = ["pecanpy", "node2vec", "fasttext", "spectral", "svd", "randomwalk", "none"]
CLUSTERING = [
    "amine",
    "louvain",
    "alouvain",
    "dbscan",
    "optics",
    "flame",
    "affinity",
    "bestvalues",
    "in_progress",
    "my_flame",
]

HERE = pathlib.Path(__file__).resolve().parent


def build_commands(args) -> list[list[str]]:
    """Return the list of command lines composing the grid."""
    commands = []
    for preproc, embed, cluster in itertools.product(
        PREPROCESSING, EMBEDDING, CLUSTERING
    ):
        # 'amine' clustering requires an embedding.
        if cluster == "amine" and embed == "none":
            continue
        outfile = HERE / "artificial" / "results" / f"{preproc}_{embed}_{cluster}.txt"
        outfile.parent.mkdir(parents=True, exist_ok=True)
        commands.append(
            [
                sys.executable,
                "-m",
                "amine.benchmarks.process_artificial_network",
                "-g",
                args.graph_generation,
                "-c",
                cluster,
                "-e",
                embed,
                "-p",
                preproc,
                "-n",
                str(args.nb_modules),
                "-m",
                str(args.module_size),
                "-s",
                str(args.network_size),
                "-r",
                str(args.runs),
                "--outfile",
                str(outfile),
            ]
        )
    return commands


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph-generation", default="gencat")
    parser.add_argument("--nb-modules", type=int, default=1)
    parser.add_argument("--module-size", type=int, default=10)
    parser.add_argument("--network-size", type=int, default=1000)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    commands = build_commands(args)
    if args.limit:
        commands = commands[: args.limit]

    print(f"{len(commands)} grid combinations")
    for index, command in enumerate(commands, start=1):
        print(f"[{index}/{len(commands)}] {' '.join(command)}")
        if args.dry_run:
            continue
        subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
