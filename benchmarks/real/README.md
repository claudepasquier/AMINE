# Real-data benchmark

This directory holds the real-data runs used to evaluate AMINE on biological
questions (as opposed to the synthetic grid in `../artificial/`).

## Data

Real runs use expression tables (gene id, log2 fold-change, p-value) together
with a protein–protein interaction network. The networks are downloaded on
demand by the core:

```bash
python -m amine.download_data
```

## Running AMINE on real data

```bash
python -m amine \
    -x data/real/expression/<dataset>.csv \
    -g 0 -l 2 -p 6 \
    -s human \
    -n string \
    -o results/<dataset>.xlsx
```

The `-k/--nb_modules` flag limits the number of returned modules (useful for
the web front-end and for large networks).

## Datasets used in the paper

The datasets referenced in the AMINE paper (e.g. the TCGA cohorts) are not
redistributed here; download them from their original sources and record the
accession numbers in the run log. The `data/real/` directory is git-ignored so
that large expression tables are not committed.
