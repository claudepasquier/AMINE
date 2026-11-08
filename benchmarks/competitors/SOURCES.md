# Competitor tools — provenance and usage

This directory preserves, for **legacy and reproducibility purposes**, the
sources of the competing active-module-identification tools that were used to
produce the comparison table `methods.xlsx` (see
`old_code/active_module_detection/methods.xlsx`).

The files were originally authored by **Leandro Correa (25.09.2019)** and lived
in `old_code/active_module_detection/other_tools/`. They are copied here
verbatim so that the benchmark can be re-run and the published comparison
reproduced. They are **not** part of the AMINE package and are not installed by
`pip install amine`.

## Inventory

| File             | Tool   | Language | Role                                        |
| ---------------- | ------ | -------- | ------------------------------------------- |
| `BIONET_test.R`  | BioNet | R        | driver script for the BioNet method         |
| `COSINE_test.R`  | COSINE | R        | driver script for the COSINE method         |
| `GIGA_test.R`    | GIGA   | R        | driver script for the GIGA method           |
| `GiGA.pl`        | GIGA   | Perl     | GIGA implementation (by L. Correa)          |
| `genes_hugo.csv` | —      | CSV      | HUGO gene symbol mapping used by the drivers |

## Upstream projects

| Tool   | Upstream / reference                                                                 |
| ------ | ------------------------------------------------------------------------------------ |
| BioNet | Beisser et al., *BioNet: an R-Package for the functional analysis of biological networks*, Bioinformatics 26(8), 2010. CRAN: `BioNet`. |
| COSINE | Ma et al., *COSINE: Condition-Specific sub-Network identification using a global optimization method*, Bioinformatics 27(9), 2011. |
| GIGA   | Breitling et al., *Iterative Group Analysis (iGA): a simple tool to enhance sensitivity and facilitate interpretation of microarray experiments*, BMC Bioinformatics 5:34, 2004. |

> The exact upstream versions used in the original study are not pinned in the
> historical sources. When re-running the benchmark, record the versions of the
> R packages (`BioNet`, `COSINE`, ...) and of Perl in the run log.

## Running the drivers

Each R driver exposes a `--help` flag:

```bash
Rscript COSINE_test.R --help
Rscript BIONET_test.R --help
Rscript GIGA_test.R --help
```

The GIGA Perl implementation is invoked by `GIGA_test.R`; it can also be run
directly:

```bash
perl GiGA.pl --help
```

## Reproducibility notes

* These scripts expect the simulated networks and p-value files produced by the
  AMINE benchmark grid (see `src/amine/benchmarks/process_artificial_network.py`).
* The R drivers write their predictions in a format that can be compared with
  AMINE's output using the F1 / recall measures implemented in
  `amine.scores.Scores`.
* Because the tools are third-party, their licences are governed by their
  respective upstream projects. They are redistributed here only as part of the
  research record; consult the upstream projects before reuse.
