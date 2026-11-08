#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Entry point for the processing of real networks.

Example of call:
> python process_real_network.py -x ../bio_dataset/Hmga2_positive_vs_negative_moderated_log2FoldChanges.csv -g 0 -v 4 -s mouse -p

"""

from .module_detection import ModuleDetection
from .datasets import Datasets
from .scores import Scores
from . import models
import pandas as pd
import numpy as np
import argparse
import pathlib
import sys
from .parameters import Param
import xlrd

def parse_arguments():
    """Parse arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument('-x', '--expvalue', dest='expvalue_file', type=pathlib.Path, required=True, help="specifies the file with expression values")
    parser.add_argument('-g', '--gene_col', dest='gene_col', type=int, required=True, help="specifies the index (in expvalue_file) of the column with gene ids (first columns=0)")
    parser.add_argument('-l', '--log2fc_col', dest='log2fc_col', type=int, required=False, help="specifies the index (in expvalue_file) of the column with log2 fold change values (first columns=0)")
    parser.add_argument('-p', '--pvalue_col', dest='pvalue_col', type=int, required=False, help="specifies the index (in expvalue_file) of the column with pvalues (first columns=0)")
    parser.add_argument('-a', '--aggreg', dest='aggregation_method', type=str, required=False, choices=["pvalue", "log2fc", "pivalue"], help="specifies the method used to aggregate scores")
    parser.add_argument('-s', '--specie', dest='specie', type=str, required=True, choices=["human", "mouse", "drosophila"], help="specifies the specie")
    parser.add_argument('-f', '--focus', dest='focus_genes_file', type=pathlib.Path, required=False, help="specifies the file with the list of important genes")
    parser.add_argument('-m', '--model', dest='precomputed', required=False, default=False, action='store_true', help="indicates if precomputed model must be used")
    parser.add_argument('-o', '--output', dest='output_file', required=False, type=pathlib.Path, help="specifies the name of the output file")
    return parser.parse_args()

def process(expvalue_file, nb_modules_to_find, specie, gene_col, log2fc_col, pvalue_col, output_file, focus_genes_file=None, aggregation_method=None, precomputed=None):
    """
    Check arguments and call the module detection method

    Parameters
    ----------
    expvalue_file     : path
                        path to the file with expression values
    nb_modules_to_find: int
                        maximum number of modules to return
    specie            : str
                        the specie
    gene_col          : int
                        index (in expvalue_file) of the column with gene ids (first columns=0)
    log2fc_col        : int
                        index (in expvalue_file) of the column with log2 fold change values (first columns=0)
    pvalue_col        : int
                        index (in expvalue_file) of the column with pvalues (first columns=0)
    output_file       : path
                        pathof the output file
    focus_genes_file  : path
                        file with the list of important genes
    aggregation_method: string
                        method used to aggregate scores, one of ["pvalue", "log2fc", "pivalue"]
    precomputed       : path
                        indicates if precomputed model must be used
    """

    if output_file:

        output_file = pathlib.Path(output_file)
        groups_output_file = output_file.with_suffix(".groups")

    """Use Node2vec model"""
    model = models.Node2vec()

    """Read gene associated values."""
    if not ( log2fc_col or pvalue_col ):
        raise Exception("At least one columns with quantification must be specified (log2fc_col or pvalue_col")

    if not aggregation_method:
        if pvalue_col:
            aggregation_method = "pvalue"
        else:
            aggregation_method = "log2fc"


    ##########
    ###DEBUG
    print("aggregation method")
    print(aggregation_method)
    ##########
    
    if ( not log2fc_col ) and ( aggregation_method in ["log2fc", "pivalue"] ):
            raise Exception("{} aggregation method can only be used when a column with log2 fold change values is specified".format(aggregation_method))

    if ( not pvalue_col ) and ( aggregation_method in ["pvalue", "pivalue"] ):
            raise Exception("{} aggregation method can only be used when a column with p-values is specified".format(aggregation_method))

    col_indexes = [gene_col]
    col_titles = ["geneid"]
    if log2fc_col:
        col_indexes.append(log2fc_col)
        col_titles.append("log2foldchange")
    if pvalue_col:
        col_indexes.append(pvalue_col)
        col_titles.append("pvalue")

    ##########
    ###DEBUG
    print("trace1")
    ##########

    # sort columns
    z = sorted(zip(col_indexes, col_titles))
    col_indexes, col_titles = zip(*z)
    try:
        df = pd.read_excel(expvalue_file, usecols=col_indexes, header=0, names=col_titles, engine='openpyxl')
    except (xlrd.biffh.XLRDError, ValueError):
        try:
            df = pd.read_csv(expvalue_file, usecols=col_indexes, header=0, sep=None, engine="python", names=col_titles)
        except pd.errors.ParserError:
            raise Exception("Unable to open '{}'".format(expvalue_file))

    """Set the type of the geneid column to string"""
    df = df.astype({'geneid': 'str'})
    """Replace NA with pvalues of 1"""
    if log2fc_col:
        df[["log2foldchange"]] = df[["log2foldchange"]].fillna(value=0)
    if pvalue_col:
        df[["pvalue"]] = df[["pvalue"]].fillna(value=1)

    """get the list of important genes"""
    relevant_genes = None
    if focus_genes_file:
        relevant_genes = []
        try:
            with open(focus_genes_file, 'r') as infile:
                for line in infile:
                    gene_name = line.strip()
                    if gene_name:
                        relevant_genes.append(gene_name)
        except FileNotFoundError:
            raise Exception("Error: file not found '{}'".format(focus_genes_file))
    
    ##########
    ###DEBUG
    print("trace2")
    ##########

    """
    from the dataframe, a dictionary is built, a default_value and a fitness function is set
    The fitness function and the value associated with each gene depends on the aggregation method.
    epsilon is the smallest value that can be handled in python in order that 1-epsilon < 1
    """
    epsilon = 1e-16
    geneid_indx = col_titles.index("geneid")
    df["geneid"] = df["geneid"].apply(lambda x : x.strip()) # remove spaces in ids
    if aggregation_method == "pvalue":
        pval_indx = col_titles.index("pvalue")
        df['pvalue'] = np.where((df.pvalue == 0),epsilon,df.pvalue)
        query2value = {x[geneid_indx]: float(x[pval_indx]) for x in list(df.itertuples(index=False, name=None))}
        """replace 1 to 1-epsilon"""
        query2value = {x: y if y != 1 else 1-epsilon for x, y in query2value.items()}
        """replace 0 to epsilon"""
        query2value = {x: y if y > epsilon else epsilon for x, y in query2value.items()}
        query2value = {x: y for x, y in query2value.items()}
        fitness_fun = lambda the_graph, clus: Scores.aggregation_zscore(the_graph, clus, 'weight')
        default_value = 1 - epsilon
        query2pvalue = query2value
        if log2fc_col:
            fc_indx = col_titles.index("log2foldchange")
            query2log2fc = {x[geneid_indx]: float(x[fc_indx]) for x in list(df.itertuples(index=False, name=None))}
#     elif arg.aggregation_method == "log2fc":
#         fc_indx = col_titles.index("log2foldchange")
#         query2value = {x[0]: float(x[fc_indx]) for x in list(df.itertuples(index=False, name=None))}
#         fitness_fun = lambda the_graph, clus: Scores.aggregation_from_normdist(the_graph, clus, 'weight')
#         default_value = 0
#     elif arg.aggregation_method == "pivalue":
#         pval_indx = col_titles.index("pvalue")
#         fc_indx = col_titles.index("log2foldchange")
#         query2value = {x[0]: abs(float(x[fc_indx])) * -math.log10( float(x[pval_indx]) ) for x in list(df.itertuples(index=False, name=None))}
#         fitness_fun = lambda the_graph, clus: Scores.aggregation_from_normdist(the_graph, clus, 'weight')
#         default_value = min(query2value.values())


    ##########
    ###DEBUG
    print("trace3")
    ##########


    """ map query term to gene name"""
    query2name = Datasets.map_query_to_gene_name(query2value.keys(), specie)

    """get the location of precomputed model if needed"""
    precomputed_model = Param.get_node2vec_model(specie) if precomputed else None

    """read the PPI graph"""
    G = Datasets.get_ppi_string_graph(specie, min_coexpression=0, min_combined_score=700, weight=1)

    """set the values to each nodes on the graph"""
    node2value = {query2name[x]: y for x, y in query2value.items() if x in query2name}
    Datasets.set_nodes_value(G, 'weight', node2value, default_value=default_value, case_sensitive=False)

    """initialize the model"""
    model.init(G, precomputed=precomputed_model)

    """call module detection method"""
    module_detection = ModuleDetection(G, model, fitness_fun)

    ##########
    ###DEBUG
    print("trace4")
    ##########

    """do the prediction"""
    if relevant_genes:
        relevant_nodes = [query2name[x] for x in relevant_genes if x in query2name]
    else:
        relevant_nodes = None
    results = module_detection.predict_modules(relevant_nodes, max_nb_modules=None, cutoff=0.05)
    
    """
        output format
        1 - list of nodes (space separated)
        2 - s score
        3 - pvalue
    """

    ##########
    ###DEBUG
    print("trace5")
    ##########


    name2query = {y:x for x, y in query2name.items()}
    if output_file.suffix == '.xlsx':
        with pd.ExcelWriter(output_file) as excel_writer:  
            sheet1 = []
            sheet2 = []
            for ctr in range(len(results)):
                sheet1.append((ctr+1, ' '.join([G.nodes[x]['label'] for x in sorted(results[ctr][0])]), results[ctr][1], results[ctr][2]))
                for x in sorted(results[ctr][0]):
                    gene_name = G.nodes[x]['label']
                    try:
                        query = name2query[gene_name]
                        pvalue = query2pvalue[query]
                    except KeyError:
                        query = ""
                        pvalue = ""
                    row = [gene_name, ctr+1, query, pvalue]
                    if log2fc_col:
                        if query:
                            log2fc = query2log2fc[query]
                            row.append(log2fc)
                        else:
                            log2fc = ""
                    sheet2.append(row)
            if sheet1 == []:
                sheet1.append([''] * 4)
            if sheet2 == []:
                if log2fc_col:
                    sheet2.append([''] * 5)
                else:
                    sheet2.append([''] * 4)
            df1 = pd.DataFrame(data=sheet1)
            df1.columns = ['module_nb', 'genes', 's score', 'pvalue']
            df1.set_index('module_nb')
            df1.to_excel(excel_writer, sheet_name="list of modules", index=False)
            df2 = pd.DataFrame(data=sheet2)
            columns = ['gene', '#module', "query", "pvalue"]
            if log2fc_col:
                columns.append("log2foldchange")
            df2.columns = columns 
            df2.set_index('gene')
            df2.to_excel(excel_writer, sheet_name="genes to modules", index=False)

                ##########
            ###DEBUG
            print("trace6")
            ##########

    else:
        with open(output_file, "w") as outfile, open(groups_output_file, "w") as outfile_groups:
            outfile.write("module_nb, genes, s score,pvalue\n")
            for ctr in range(len(results)):
                outfile.write("{},{},{},{}\n".format(ctr+1, ' '.join([G.nodes[x]['label'] for x in sorted(results[ctr][0])]), results[ctr][1], results[ctr][2]))
                columns = ['gene', '#module', "query", "pvalue"]
                if log2fc_col:
                    columns.append("log2foldchange")
                outfile_groups.write('\t'.join(columns) + '\n')    
                for x in sorted(results[ctr][0]):
                    gene_name = G.nodes[x]['label']
                    try:
                        query = name2query[gene_name]
                        pvalue = query2pvalue[query]
                    except KeyError:
                        query = ""
                        pvalue = ""
                    row = [gene_name, str(ctr+1), query, str(pvalue)]
                    if log2fc_col:
                        if query:
                            log2fc = query2log2fc[query]
                            row.append(str(log2fc))
                        else:
                            log2fc = ""
                    outfile_groups.write('\t'.join(row)+'\n')
#        for ctr in range(len(results)):
#            print("{},{},{},{}".format(ctr+1, ' '.join([G.nodes[x]['label'] for x in sorted(results[ctr][0])]), results[ctr][1], results[ctr][2]))

    out = []
    for ctr in range(min(len(results), nb_modules_to_find)):
        print("{},{},{},{}".format(ctr+1, ' '.join([G.nodes[x]['label'] for x in sorted(results[ctr][0])]), results[ctr][1], results[ctr][2]))
        module = []
        module.append(ctr)
        genes_names = []
        for x in sorted(results[ctr][0]):
            gene_name = G.nodes[x]['label']
            if gene_name in name2query:
                gene_name = name2query[gene_name]
            genes_names.append(gene_name)
        #module_node = (','.join([G.nodes[x]['label'] for x in sorted(results[ctr][0])]))
        module_node = (','.join(genes_names))
        module.append(module_node)
        module.append(results[ctr][1])
        module.append(results[ctr][2])
        out.append(module)

        ##########
        ###DEBUG
        print("module")
        print(module)
        ##########

    return out


if __name__ == '__main__':
    """Entry point."""
    arg = parse_arguments()
    process(arg.expvalue_file, arg.specie, arg.gene_col, arg.log2fc_col, arg.pvalue_col, arg.focus_genes_file, arg.output_file, arg.aggregation_method, arg.precomputed)

