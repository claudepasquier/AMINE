# Artificial-network benchmark

This directory holds the results of the parameterised artificial-network grid
used to evaluate AMINE and its variants.

## Generating the grid

```bash
python benchmarks/run_grid.py --dry-run          # inspect the commands
python benchmarks/run_grid.py --runs 10          # run the full grid
```

Results are written to `artificial/results/<preproc>_<embed>_<cluster>.txt`,
one file per combination. Each file contains one line per run with the columns:

```
#graph,time(s),nb found,real size,true hits,pvalue
```

## Graph generators

The grid can be run on several synthetic graph families (`-g`):

* `gencat` — the gencat generator (default);
* `guyon` — scale-free graphs following Guyon's protocol;
* `guyondata` — the dataset from Guyon's paper;
* `batra` — graphs following Batra's protocol.

## Metrics

The F1 score of each prediction is computed with
`amine.scores.Scores.measure_f1` and aggregated (mean, standard deviation,
quartiles) by the benchmark processor. The aggregated values feed the
comparison table `benchmarks/methods.xlsx`.
