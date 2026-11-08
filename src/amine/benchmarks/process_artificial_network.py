#!/usr/bin/env python

# pylint: disable=line-too-long
# pylint: disable=invalid-name
# pylint: disable=unnecessary-lambda-assignment

"""
Entry point for the processing of real networks.

"""

import argparse
import statistics
import time

import community as community_louvain
import networkx as nx
import numpy as np
from sklearn.cluster import DBSCAN, OPTICS, AffinityPropagation

from ..amine_exception import AmineException
from ..datasets import Datasets
from ..module_detection import ModuleDetection
from ..scores import Scores
from . import embedding, utils
from .algorithms.FLAME import FLAME


def parse_arguments():
    """Parse arguments."""
    line_parser = argparse.ArgumentParser()
    line_parser.add_argument(
        "-r",
        "--nbruns",
        dest="number_of_runs",
        type=int,
        required=False,
        default=1,
        help="specifies the number of runs (default=1000)",
    )
    line_parser.add_argument(
        "-n",
        "--nbmodules",
        dest="nb_modules",
        type=int,
        required=False,
        default=1,
        help="specifies the number of modules to generate (default=1)",
    )
    line_parser.add_argument(
        "-m",
        "--modulesize",
        dest="module_size",
        type=int,
        required=False,
        default=10,
        help="specifies the size of each modules (default=10)",
    )
    line_parser.add_argument(
        "-t",
        "--targetmodulesize",
        dest="target_module_size",
        type=int,
        required=False,
        default=None,
        help="specifies the expected size of each modules (default=None, i.e. no expected size)",
    )
    line_parser.add_argument(
        "-s",
        "--networksize",
        dest="network_size",
        type=int,
        required=False,
        default=1000,
        help="specifies the number of vertices in graph (default=1000)",
    )
    line_parser.add_argument(
        "-d",
        "--deledges",
        dest="removed_edges",
        type=float,
        required=False,
        default=0.0,
        help="proportion of edges to remove (default = 0.0",
    )
    line_parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        required=False,
        action="store_true",
        default=False,
        help="displays results on screen",
    )
    line_parser.add_argument(
        "-o",
        "--outfile",
        dest="outfile",
        required=False,
        default=None,
        help="name of the output file (default=no output)",
    )
    line_parser.add_argument(
        "-g",
        "--graphgen",
        dest="graph_generation",
        required=False,
        default=None,
        choices=["guyondata", "guyon", "batra", "gencat"],
        help="""Specify the data to use.
                        If 'guyondata' is chosen the predictions are done on the dataset specified in Guyon's paper and all other graph parameters are ignored.
                        If 'guyon' is chosen, the method described in Guyon's paper is used for data generation.
                        If 'batra' is chosen, data are generated using the method described in Batra's paper. In this case, additional parameters might be specified: param_k, param_mean_bg, param_mean_fg, param_std_bg and param_std_bg.
                        If 'gencat' is chosen, data are generated using the gencat method.""",
    )
    line_parser.add_argument(
        "-c",
        "--clustering",
        dest="clustering_method",
        required=False,
        default="amine",
        choices=[
            "affinity",
            "amine",
            "in_progress",
            "alouvain",
            "louvain",
            "bestvalues",
            "dbscan",
            "flame",
            "optics",
            "my_flame",
        ],
        help="Specify the method to use (default='amine')",
    )
    line_parser.add_argument(
        "-e",
        "--embedding",
        dest="embedding_method",
        required=False,
        default="node2vec",
        choices=[
            "pecanpy",
            "node2vec",
            "fasttext",
            "spectral",
            "svd",
            "randomwalk",
            "mane",
            "none",
        ],
        help="Specify the embedding method to use (default='node2vec')",
    )
    line_parser.add_argument(
        "-p",
        "--preprocessing",
        dest="preprocessing_method",
        required=False,
        choices=["original", "keep_edges", "merge", "none"],
        default="original",
        help="Specify the preprocessing method to use (default='keep_edges')",
    )
    line_parser.add_argument(
        "--preproc_alpha",
        dest="preprocessing_alpha",
        required=False,
        type=float,
        default=0.5,
        help="Specify the balance between edge weights and node similarities (default=0.5)",
    )
    line_parser.add_argument(
        "--param_k",
        dest="param_k",
        required=False,
        default=2,
        help="K parameter used by Batra method to specify the average shortest path length in a module (default=2)",
    )
    line_parser.add_argument(
        "--param_mean_bg",
        dest="param_mean_bg",
        required=False,
        default=0,
        help="mean of the background used by Batra method (default=0)",
    )
    line_parser.add_argument(
        "--param_mean_fg",
        dest="param_mean_fg",
        required=False,
        default=1,
        help="mean of the foreground used by Batra method (default=1)",
    )
    line_parser.add_argument(
        "--param_std_bg",
        dest="param_std_bg",
        required=False,
        default=0,
        help="mean of the background used by Batra method (default=0)",
    )
    line_parser.add_argument(
        "--param_std_fg",
        dest="param_std_fg",
        required=False,
        default=1,
        help="mean of the foreground used by Batra method (default=1)",
    )
    line_parser.add_argument(
        "--edges_list",
        dest="edges_list",
        required=False,
        default=None,
        help="path to graph's edges list",
    )
    line_parser.add_argument(
        "--pvalues",
        dest="pvalues",
        required=False,
        default=None,
        help="path to nodes' associated pvalues",
    )
    line_parser.add_argument(
        "--output",
        dest="output",
        required=False,
        default=None,
        help="path to output file",
    )
    return line_parser.parse_args()


if __name__ == "__main__":
    # Entry point.
    arg = parse_arguments()

    if not arg.embedding_method and arg.clustering_method == "amine":
        raise AmineException("Amine method requires an embedding but none is specified")

    # Use aggregation_from_pvalue as fitness function.
    fitness_fun = lambda the_graph, clus: Scores.aggregation_from_pvalue(
        the_graph, clus, "weight"
    )

    f1_scores = []
    if arg.outfile:
        outfile = open(arg.outfile, "w", encoding="utf8")
        outfile.write("#graph,time(s),nb found,real size,true hits,pvalue\n")
    for ctr in range(arg.number_of_runs):
        if arg.graph_generation == "guyondata":
            G = Datasets.get_guyon_graph(ctr + 1)
        elif arg.graph_generation == "gencat":
            G = Datasets.get_gencat_graph(
                arg.network_size,
                arg.network_size * 16,
                arg.nb_modules,
                arg.nb_modules * [arg.module_size],
                ctr,
            )
        elif arg.graph_generation == "guyon":
            # The historical experimental code hard-coded these values; the
            # modernized core exposes them as explicit parameters.
            G = Datasets.get_scale_free_graph(
                arg.network_size, 3, arg.nb_modules, arg.module_size, 0.09, 0.70, ctr
            )
        elif arg.edges_list and arg.pvalues:
            G = nx.read_edgelist(arg.edges_list, create_using=None, data=False)
            for n in G.nodes():
                G.nodes[n]["weight"] = 1 - 1e-6  # default pvalue of 1 - epsilon
            # Datasets.init_graph(G)
            with open(arg.pvalues, "r", encoding="utf8") as infile:
                for line in infile:
                    tokens = line.strip().split(sep=" ")
                    try:
                        pvalue = float(tokens[1])
                        if pvalue == 1:
                            # pylint wants 'PVALUE'
                            pvalue -= 1e-6
                        elif pvalue == 0:
                            pvalue += 1e-6
                        G.nodes[tokens[0]]["weight"] = pvalue
                    except KeyError:
                        pass
            Datasets.init_graph(G)
        else:
            raise AmineException(
                "a graph generation method or path to files containing a graph must be specified"
            )

        if arg.removed_edges > 0:
            utils.remove_edges(G, arg.removed_edges, ctr)

        from networkx.algorithms.community import k_clique_communities

        # mod = list(G.nodes)[:5]
        # fitness_fun = lambda the_graph, clus: Scores.aggregation_from_pvalue(the_graph, clus, 'weight')
        # # fitness_fun = Scores.aggregation_from_pvalue
        # # fitness_fun = Scores.average_value
        # score = fitness_fun(G, mod)
        # print(f"score={score}")
        # score = Scores.get_bkg_score(fitness_fun, G, len(mod)+1)
        # print(f"score={score}")
        # score = Scores.get_score(fitness_fun, G, mod, True, True)
        # print(f"score={score}")
        # dd

        utils.preprocess_network(
            G, method=arg.preprocessing_method, alpha=arg.preprocessing_alpha
        )

        # create embedding model
        # print(f"starting embedding of {len(G.nodes)} nodes")
        emb = embedding.get_embedding_model(arg.embedding_method, G)
        # print("finished embedding")
        # call module detection method
        start_time = time.perf_counter()
        results = []

        if arg.clustering_method == "in_progress":
            from networkx.algorithms.community import k_clique_communities

            fitness_fun = lambda the_graph, clus: Scores.aggregation_from_pvalue(
                the_graph, clus, "weight"
            )
            c = list(k_clique_communities(G, 5))
            best_mod, best_score = None, 0
            for mod in c:
                score = fitness_fun(G, mod)
                if score > best_score:
                    best_mod = mod
                    best_score = score
            if best_mod:
                results = [(list(best_mod), score, 0)]
        elif arg.clustering_method == "alouvain":
            fitness_fun = lambda the_graph, clus: (
                Scores.aggregation_from_pvalue(the_graph, clus, "weight")
                + Scores.modularity(the_graph, clus)
            )
            results = utils.my_louvain(G, fitness_fun)
        elif arg.clustering_method == "louvain":
            communities = community_louvain.best_partition(
                G, resolution=1
            )  # , partition=partition)
            results = utils.convert_to_amine_format(G, communities, fitness_fun)
        elif arg.clustering_method == "amine":
            fitness_fun = lambda the_graph, clus: Scores.aggregation_from_pvalue(
                the_graph, clus, "weight"
            )  # + Scores.modularity(the_graph, set(clus))
            module_detection = ModuleDetection(G, emb, fitness_fun)
            results = module_detection.predict_modules(cutoff=0.05)
        elif arg.clustering_method in ["affinity", "dbscan", "flame", "optics"]:
            if arg.clustering_method == "dbscan":
                clustering = DBSCAN(min_samples=3, metric="cosine").fit(
                    emb.get_vectors()
                )
            elif arg.clustering_method == "optics":
                clustering = OPTICS(min_samples=3, metric="cosine").fit(
                    emb.get_vectors()
                )
            elif arg.clustering_method == "flame":
                clustering = FLAME(
                    metric="cosine",
                    cluster_neighbors=5,
                    iteration_neighbors=20,
                    verbose=1,
                ).fit(emb.get_vectors())
            elif arg.clustering_method == "affinity":
                clustering = AffinityPropagation(verbose=1).fit(emb.get_vectors())
            clusters = {}
            for ctr2, label in enumerate(clustering.labels_):
                try:
                    clusters[label].append(ctr2)
                except KeyError:
                    clusters[label] = [ctr2]
            results = sorted(
                [(x, fitness_fun(G, x), 0) for _, x in clusters.items() if len(x) > 2],
                key=lambda x: x[1],
                reverse=True,
            )
        elif arg.clustering_method == "bestvalues":
            results = []
            n = sorted(
                [(x[0], x[1]["weight"]) for x in G.nodes(data=True)], key=lambda x: x[1]
            )
            n = [x[0] for x in n]
            for ctr2 in range(arg.nb_modules):
                results.append(
                    (n[ctr2 * arg.module_size : (ctr2 + 1) * arg.module_size], 0, 0)
                )
        elif arg.clustering_method == "my_flame":
            from . import my_flame

            results = my_flame.predict(G, emb, fitness_fun, neighbor_size=5)
        else:
            raise AmineException(
                f"clustering method {arg.clustering_method} not known."
            )

        end_time = time.perf_counter()
        pvalue = 0
        if results:
            pvalue = results[0][2]

        separate_modules = False
        if arg.output:
            with open(arg.output, "w", encoding="utf8") as out_result:
                for ctr2 in range(min(arg.nb_modules, len(results))):
                    if ctr > 0 and separate_modules:
                        out_result.write("--\n")
                    try:
                        mod = results[ctr2][0]
                        out_result.writelines(f"{gene}\n" for gene in mod)
                    except IndexError:
                        break

        pred = set()
        nb_clust = 0
        for cl in results:
            if arg.target_module_size:
                if not pred:
                    pred.update(cl[0])
                    continue
                if len(pred) < arg.target_module_size:
                    if abs(arg.target_module_size - len(pred)) > abs(
                        arg.target_module_size - len(pred) - len(cl[0])
                    ):
                        pred.update(cl[0])
                        continue
                    else:
                        break
                else:
                    break
            else:
                nb_clust += 1
                if nb_clust > arg.nb_modules:
                    break
                pred.update(cl[0])
        print(f"{len(pred)} predicted={pred}")
        # print(results)
        # module = ['10333', '2131', '2132', '23643', '7097', '7099']
        # print(Scores.aggregation_from_pvalue(G, module, 'weight'))
        # module = ["637", "5606", "836", "596", "1432", "598", "842", "572"]
        # print("score for reference module")
        # print(Scores.aggregation_from_pvalue(G, module, 'weight'))

        try:
            truehits = Datasets.get_groups(G)
            if truehits:
                print("truehits", truehits)

                # merge the content of the true hits in a set
                th = set()
                for key, value in truehits.items():
                    th.update(value)

                nb_pred = len(pred)
                nb_th = len(th)
                nb_found = len(pred & th)

                if arg.outfile:
                    perf = end_time - start_time
                    outfile.write(
                        f"{ctr + 1},{perf:.2f},{nb_pred},{nb_th},{nb_found},{pvalue}\n"
                    )
                    outfile.flush()
                if not arg.verbose:
                    continue
                # calculate the F1 score
                res = []
                f1_score = Scores.measure_f1(G, th, pred)
                res.append((len(pred), len(pred & th), f1_score))

                f1_scores.append(f1_score)

                # compute the stats
                quartiles = np.percentile(f1_scores, [25, 50, 75])
                minim = min(f1_scores)
                maxim = max(f1_scores)
                iqr = quartiles[2] - quartiles[0]
                high = min(maxim, quartiles[2] + iqr * 1.5)
                low = max(minim, quartiles[0] - iqr * 1.5)
                out_high = [str(f"{x:.5f}") for x in f1_scores if x > high]
                out_low = [str(f"{x:.5f}") for x in f1_scores if x < low]
                print(
                    f"{ctr + 1} len={nb_pred} true_hits={nb_th} found={nb_found} f1_score={f1_scores[-1]:.5f}, mean={statistics.mean(f1_scores):.5f}, variance={statistics.pstdev(f1_scores):.5f}, Q25={quartiles[0]:.5f}, Q50={quartiles[1]:.5f}, Q75={quartiles[2]:.5f}, low={low:.5f}, high={high:.5f}, out_low=[{','.join(out_low)}], out_high=[{','.join(out_high)}] pvalue={pvalue}"
                )
        except KeyError:  # true hits are unknown
            pass

    if arg.outfile:
        outfile.close()
