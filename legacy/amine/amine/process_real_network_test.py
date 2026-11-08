from goatools.anno.gaf_reader import GafReader

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
+-------------------------------------------------------------------------------------+
| This file is part of AMINE                                                          |
|                                                                                     |
| AMINE is free software: you can redistribute it and/or modify it under the terms of |
| the GNU General Public License as published by the Free Software Foundation, either |
| version 3 of the License, or (at your option) any later version.                    |
| You should have received a copy of the GNU General Public License along with AMINE. |
| If not, see <http://www.gnu.org/licenses/>.                                         |
|                                                                                     |
| Author: Claude Pasquier (I3S Laboratory, CNRS, Université Côte d'Azur)              |
| Contact: claude.pasquier@univ-cotedazur.fr                                          |
| Created on decembre 20, 2022                                                        |
+-------------------------------------------------------------------------------------+
"""

import pathlib
import sys
import statistics
import xlrd
import pandas as pd
import numpy as np
from scipy.stats import norm
# from .module_detection import ModuleDetection
from .datasets import Datasets
from .scores import Scores
from .amine_exception import AmineException
# from . import models
from .parameters import Param


def process(
    expvalue_file: str,
    network: str,
    specie: str,
    gene_col: int,
    log2fc_col: int,
    pvalue_col: int,
    output_file: str,
    focus_genes_file: str = None,
    aggregation_method: str = "pvalue",
    precomputed: bool = None,
):
    """
    Check arguments and call the module detection method

    Parameters
    ----------
    expvalue_file     : str
                        path to the file with expression values
    network           : str
                        a path to a network file in edge list format
                        or an item in ['string', 'biogrid', 'intact']
    specie            : str
                        the specie
    gene_col          : int
                        index (in expvalue_file) of the column with gene ids (first columns=0)
    log2fc_col        : int
                        index (in expvalue_file) of the column with log2 fold change values
                        (first columns=0)
    pvalue_col        : int
                        index (in expvalue_file) of the column with pvalues (first columns=0)
    output_file       : str
                        pathof the output file
    focus_genes_file  : str
                        file with the list of important genes
    aggregation_method: str
                        method used to aggregate scores, one of ["pvalue", "log2fc", "pivalue"]
    precomputed       : bool
                        indicates if precomputed model must be used
    """

    if output_file:
        output_file = pathlib.Path(output_file)
        groups_output_file = output_file.with_suffix(".groups")

    # Read gene associated values.
    if not (log2fc_col or pvalue_col):
        raise Exception(
            "At least one columns with quantification must be specified (log2fc_col or"
            " pvalue_col"
        )

    if not aggregation_method:
        if pvalue_col:
            aggregation_method = "pvalue"
        else:
            aggregation_method = "log2fc"

    if (not log2fc_col) and (aggregation_method in ["log2fc", "pivalue"]):
        raise Exception(
            f"{aggregation_method} aggregation method can only be used when a column"
            " with log2 fold change values is specified"
        )

    if (not pvalue_col) and (aggregation_method in ["pvalue", "pivalue"]):
        raise Exception(
            f"{aggregation_method} aggregation method can only be used when a column"
            " with p-values is specified"
        )

    col_indexes = [gene_col]
    col_titles = ["geneid"]
    if log2fc_col:
        col_indexes.append(log2fc_col)
        col_titles.append("log2foldchange")
    if pvalue_col:
        col_indexes.append(pvalue_col)
        col_titles.append("pvalue")

    # sort columns
    z = sorted(zip(col_indexes, col_titles))
    col_indexes, col_titles = zip(*z)
    try:
        df = pd.read_excel(
            expvalue_file, usecols=col_indexes, header=0, names=col_titles
        )
    except (xlrd.biffh.XLRDError, ValueError):
        try:
            df = pd.read_csv(
                expvalue_file,
                usecols=col_indexes,
                header=0,
                sep=None,
                engine="python",
                names=col_titles,
            )
        except pd.errors.ParserError as e:
            raise Exception("Unable to open '{}'".format(expvalue_file)) from e

    if Param.verbose:
        print(f"{len(df)} values retrieved from data file")

    # Set the type of the geneid column to string
    df = df.astype({"geneid": "str"})
    # Replace NA with pvalues of 1
    if log2fc_col:
        df[["log2foldchange"]] = df[["log2foldchange"]].fillna(value=0)
    if pvalue_col:
        df[["pvalue"]] = df[["pvalue"]].fillna(value=1)

    # get the list of important genes
    relevant_genes = None
    if focus_genes_file:
        relevant_genes = []
        try:
            with open(focus_genes_file, "r") as infile:
                for line in infile:
                    gene_name = line.strip()
                    if gene_name:
                        relevant_genes.append(gene_name)
        except FileNotFoundError as e:
            raise AmineException(
                "Error: file not found '{}'".format(focus_genes_file)
            ) from e

    # read the PPI graph

    if network == "string":
        G = Datasets.get_ppi_string_graph(
            specie,
            Param.ppi_string_graph["min_neighborhood"],
            Param.ppi_string_graph["min_fusion"],
            Param.ppi_string_graph["min_cooccurence"],
            Param.ppi_string_graph["min_coexpression"],
            Param.ppi_string_graph["min_experimental"],
            Param.ppi_string_graph["min_database"],
            Param.ppi_string_graph["min_textmining"],
            Param.ppi_string_graph["min_combined_score"],
            weight=1,
        )
    elif network == "biogrid":
        G = Datasets.get_ppi_biogrid_graph(
            specie, Param.ppi_biogrid_graph["inter_type"]
        )
    elif network == "intact":
        G = Datasets.get_ppi_intact_graph(
            specie, Param.ppi_intact_graph["min_confidence"]
        )
    else:
        try:
            G = Datasets.get_custom_graph(
                network,
                Param.ppi_custom_graph["source_col"],
                Param.ppi_custom_graph["target_col"],
                Param.ppi_custom_graph["header"],
            )
        except AmineException as e:
            print(e.args)
            sys.exit(1)

    nb_nodes = len(G.nodes)
    print(f"retrieved network with {len(G.nodes)} nodes and {len(G.edges)} edges")

    # From the dataframe, a dictionary is built, a default_value and a fitness function is set.
    # The fitness function & the value associated with each gene depends on the aggregation method.
    # Epsilon is the smallest value that can be handled in python in order that 1-epsilon < 1.
    epsilon = 1e-16
    if log2fc_col:
        fc_indx = col_titles.index("log2foldchange")
    if pvalue_col:
        pval_indx = col_titles.index("pvalue")
    geneid_indx = col_titles.index("geneid")
    df["geneid"] = df["geneid"].apply(lambda x: x.strip())  # remove spaces in ids
    if aggregation_method == "pvalue":
        df["pvalue"] = np.where((df.pvalue == 0), epsilon, df.pvalue)
        pval_indx = col_titles.index("pvalue")
        query2value = {
            x[geneid_indx]: float(x[pval_indx])
            for x in list(df.itertuples(index=False, name=None))
        }
        # replace 1 to 1-epsilon
        query2value = {x: y if y != 1 else 1 - epsilon for x, y in query2value.items()}
        # replace 0 to epsilon
        query2value = {x: y if y > epsilon else epsilon for x, y in query2value.items()}
        query2value = {x: y for x, y in query2value.items()}
        fitness_fun = lambda the_graph, clus: Scores.aggregation_from_pvalue(
            the_graph, clus, "weight"
        )
        default_value = 1 - epsilon
        query2pvalue = query2value
        if log2fc_col:
            fc_indx = col_titles.index("log2foldchange")
            query2log2fc = {
                x[geneid_indx]: float(x[fc_indx])
                for x in list(df.itertuples(index=False, name=None))
            }
    elif aggregation_method == "log2fc":
        fc_indx = col_titles.index("log2foldchange")
        if pvalue_col:
            raise Exception(
                "pvalue_col cannot be specified when log2fc aggregation method is used"
            )
        query2log2fc = {
            x[geneid_indx]: float(x[fc_indx])
            for x in list(df.itertuples(index=False, name=None))
        }
        values = list(query2log2fc.values()) + [0] * (nb_nodes - len(query2log2fc))

        mean = statistics.mean(values)
        dev = statistics.pstdev(values)

        query2value = {
            x: (1 - norm.cdf(abs((y - mean) / dev))) * 2
            for x, y in query2log2fc.items()
        }
        # replace 1 to 1-epsilon
        query2value = {x: y if y != 1 else 1 - epsilon for x, y in query2value.items()}
        # replace 0 to epsilon
        query2value = {x: y if y != 0 else epsilon for x, y in query2value.items()}
        fitness_fun = lambda the_graph, clus: Scores.aggregation_from_pvalue(
            the_graph, clus, "weight"
        )
        default_value = 1 - epsilon
        query2pvalue = query2value
        aggregation_method == "pvalue"
    # elif aggregation_method == "count":
    #     fc_indx = col_titles.index("log2foldchange")
    #     query2value = {
    #         x[geneid_indx]: abs(float(x[fc_indx]))
    #         for x in list(df.itertuples(index=False, name=None))
    #     }
    #     fitness_fun = lambda the_graph, clus: Scores.aggregation_from_count(
    #         the_graph, clus, "weight"
    #     )
    #     query2log2fc = query2value
    #     default_value = 0
    #     query2pvalue = {}
    #     if pvalue_col:
    #         query2pvalue = {
    #             x[geneid_indx]: float(x[pval_indx])
    #             for x in list(df.itertuples(index=False, name=None))
    #         }
    # elif aggregation_method == "pivalue":
    #     df["pvalue"] = np.where((df.pvalue == 0), epsilon, df.pvalue)
    #     pval_indx = col_titles.index("pvalue")
    #     fc_indx = col_titles.index("log2foldchange")
    #     query2value = {
    #         x[geneid_indx]: abs(float(x[fc_indx])) * -math.log10(float(x[pval_indx]))
    #         for x in list(df.itertuples(index=False, name=None))
    #     }
    #     query2pvalue = query2value
    #     fitness_fun = lambda the_graph, clus: Scores.aggregation_from_normdist(
    #         the_graph, clus, "weight"
    #     )
    #     default_value = min(query2value.values())
    #     query2log2fc = {
    #         x[geneid_indx]: float(x[fc_indx])
    #         for x in list(df.itertuples(index=False, name=None))
    #     }

    # map query term to gene name
    query2name = Datasets.map_query_to_gene_name(query2value.keys(), specie)

    # get the location of precomputed model if needed
    precomputed_model = Param.get_node2vec_model(specie) if precomputed else None

    # set the values to each nodes on the graph
    node2value = {query2name[x]: y for x, y in query2value.items() if x in query2name}
    Datasets.set_nodes_value(
        G, "weight", node2value, default_value=default_value, case_sensitive=False
    )

    ogaf = GafReader("mgi.gaf")

    symbol2GOs = {}
    nts = ogaf.associations
    for nt_line in nts[:10]:
        if nt_line.NS != "BP":
            continue
        if nt_line.Evidence_Code != "TAS":
            continue
        if nt_line.nt_line.DB_Symbol not in symbol2GOs:
            symbol2GOs[nt_line.DB_Symbol] = set([])
        symbol2GOs[nt_line.DB_Symbol].add(nt_line.GO_ID)

    found = 0
    tot_nodes = 0
    for node in G.nodes:
        tot_nodes += 1
        if node in symbol2GOs:
            found += 1
    print(nodes, tot_nodes)



