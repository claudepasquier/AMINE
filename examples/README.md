# Example data

Small files used to smoke-test the pipeline without waiting for a full STRING
run.

| File | Description |
| ---- | ----------- |
| `example_expression.csv` | 20 human genes with log2 fold-change and p-value |
| `example_network.tsv` | a 319-node / 4016-edge sub-network of STRING (human), tab-separated `source<TAB>target` |

`example_expression.csv` columns:

| Column | Meaning |
| ------ | ------- |
| `gene` | gene symbol (mappable through the STRING aliases) |
| `log2foldchange` | log2 fold-change |
| `pvalue` | p-value |

## Fast test (recommended)

The custom network keeps the run to about a minute. The STRING alias/info files
are still required for gene mapping, so download the human data first:

```bash
python -m amine.download_data --specie human --skip-biogrid --skip-intact

python -m amine \
  -x examples/example_expression.csv \
  -g 0 -l 1 -p 2 -s human -n examples/example_network.tsv \
  -o examples/example_result.xlsx -k 5 -v
```

This writes `examples/example_result.xlsx` (two sheets: modules and
gene-to-module mapping).

## Full STRING run (slow)

Using the whole STRING human network (`-n string`) works too, but the pure-Python
node2vec embedding takes **15–30 minutes** on ~17 000 nodes:

```bash
python -m amine \
  -x examples/example_expression.csv \
  -g 0 -l 1 -p 2 -s human -n string \
  -o examples/example_result.xlsx -k 5 -v
```

## Web form

Upload `example_expression.csv` with `gene column = 0`, `log2fc column = 1`,
`pvalue column = 2`, and (for a fast run) `example_network.tsv` as the
**custom network file**.

> The example is intentionally small; it exercises the full pipeline but is not
> a biologically meaningful analysis.
