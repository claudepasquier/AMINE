#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    various scoring methods

    A first group of functions computes the score of a set of nodes on a graph,
    optionnaly specifying the attribute that is used to store the nodes' weights

    A second group of functions measures the accuracy of a prediction given
    a predicted set of nodes and a set of nodes considered as ground truth
"""

from sklearn import metrics
import networkx as nx
from scipy.stats import norm
from scipy.stats import hypergeom
from typing import Set
import math
import statistics


class Scores:
    @staticmethod
    def modularity(G: nx.Graph, cluster: Set) -> float:
        edge_inside = 0
        total_degree = 0
        modularity = 0
        for n in cluster:
            neigh = set(list(G.neighbors(n)))
            total_degree += len(neigh)
            inside = len(neigh & cluster)
            edge_inside += inside
        modularity += (edge_inside / 2 /
                       G.graph['nb_edges']) - (total_degree / 2 / G.graph['nb_edges'])**2
        return modularity

    @staticmethod
    def clustering(G: nx.Graph, cluster: Set) -> float:
        cl = nx.clustering(G, nodes=cluster)
        return sum(list(cl.values())) / len(cluster)

    @staticmethod
    def density(G: nx.Graph, cluster: Set) -> float:
        subgraph = nx.subgraph(G, cluster)
        return nx.density(subgraph)

    @staticmethod
    def normalized_cut(G: nx.Graph, cluster: Set) -> float:
        '''
        David Gleich. Hierarchical Directed Spectral Graph Partitioning.
        <https://www.cs.purdue.edu/homes/dgleich/publications/Gleich%202005%20-%20hierarchical%20directed%20spectral.pdf>
        :param G:
        :param cluster:
        '''
        return nx.normalized_cut_size(G, cluster, G.nodes - cluster)

    @staticmethod
    def average_value(G: nx.Graph, cluster: Set, attr: str) -> float:
        score = 0
        nb_ghost_nodes = 0
        for n in cluster:
            s = G.nodes[n][attr]
            if s != -1:
                score += G.nodes[n][attr]
            else:
                nb_ghost_nodes += 1
        if nb_ghost_nodes == len(cluster):
            return 0
        return score / (len(cluster) - nb_ghost_nodes)

    @staticmethod
    def average_value2(G: nx.Graph, cluster: Set, attr: str) -> float:
        score = 0
        nb_ghost_nodes = 0
        for n in cluster:
            s = G.nodes[n][attr]
            if s != -1:
                score += G.nodes[n][attr]
            else:
                nb_ghost_nodes += 1
        if nb_ghost_nodes == len(cluster):
            return 0
        return score / math.sqrt((len(cluster) - nb_ghost_nodes))

    @staticmethod
    def average_shortest_path(G: nx.Graph, cluster: Set):
        """compute average shortest path in modules composed of vertices belonging to cluster"""
        sum_shortest_path_length = 0
        for n1 in cluster:
            for n2 in cluster:
                if n1 == n2:
                    continue
                sum_shortest_path_length += nx.shortest_path_length(G,source=n1,target=n2)
        nb_nodes = len(cluster)
        return sum_shortest_path_length/(nb_nodes*(nb_nodes-1))

    @staticmethod
    def aggregation_from_pvalue(G: nx.Graph, cluster: Set, attr: str) -> float:
        """
        Stouffer's Z method used in:
        Li, D., Pan, Z., Hu, G., Zhu, Z., & He, S. (2017).
        Active module identification in intracellular networks using a memetic algorithm with a new binary decoding scheme.
        BMC Genomics, 18(S2), 209. https://doi.org/10.1186/s12864-017-3495-y
        :param G:
        :type G:
        :param cluster:
        :type cluster:
        :param attr:
        :type attr:
        """
        if 'zscores' not in G.graph:
            scores = {}
            for n in G.nodes:
                if attr in G.nodes[n]:
                    scores[n] = norm.ppf(1 - G.nodes[n][attr])
            G.graph['zscores'] = scores
        score = 0
        len_cluster = 0
        for n in cluster:
            if n in G.graph['zscores']:
                score += G.graph['zscores'][n]
                len_cluster += 1
        return score / math.sqrt(len_cluster)

    @staticmethod
    def aggregation_from_normdist(G: nx.Graph, cluster: Set, attr: str) -> float:
        """
        Stouffer's Z method
        :param G:
        :type G:
        :param cluster:
        :type cluster:
        :param attr:
        :type attr:
        """
        if 'zscores' not in G.graph:
            values = []
            for n in G.nodes:
                if attr in G.nodes[n]:
                    values.append(G.nodes[n][attr])
            mean = statistics.mean(values)
            dev = statistics.pstdev(values)

            zscores = {}
            for n in G.nodes:
                if attr in G.nodes[n]:
                    zscores[n] = ( G.nodes[n][attr] - mean) / dev
            G.graph['zscores'] = zscores
        score = 0
        len_cluster = 0
        for n in cluster:
            if n in G.graph['zscores']:
                score += G.graph['zscores'][n]
                len_cluster += 1
        return score / math.sqrt(len_cluster)
    
    @staticmethod
    def aggregation_zscore(G: nx.Graph, cluster: Set, attr: str) -> float:
        """
        Stouffer's Z method used in:
        Li, D., Pan, Z., Hu, G., Zhu, Z., & He, S. (2017).
        Active module identification in intracellular networks using a memetic algorithm with a new binary decoding scheme.
        BMC Genomics, 18(S2), 209. https://doi.org/10.1186/s12864-017-3495-y
        :param G:
        :type G:
        :param cluster:
        :type cluster:
        :param attr:
        :type attr:
        """
        if 'aggregation_zscores' not in G.graph:
            scores = {}
            for n in G.nodes:
                if attr in G.nodes[n]:
                    scores[n] = norm.ppf(1 - G.nodes[n][attr])
            G.graph['aggregation_zscores'] = scores
        score = 0
        len_cluster = 0
        for n in cluster:
            if n in G.graph['aggregation_zscores']:
                score += G.graph['aggregation_zscores'][n]
                len_cluster += 1
        return score / math.sqrt(len_cluster)

    @staticmethod
    def aggregation_log2foldchange(G: nx.Graph, cluster: Set, attr: str) -> float:
        """
        aggregation score using the log2foldchange

        standard deviation of log2foldchanges are calculated and used as zscores
        The aggregation of zscores is calculated as in the Stouffer's Z method
        :param G:
        :type G:
        :param cluster:
        :type cluster:
        :param attr:
        :type attr:
        """
        if 'aggregation_zscores' not in G.graph:
            scores = {}
            for n in G.nodes:
                if attr in G.nodes[n]:
                    scores[n] = norm.ppf(G.nodes[n][attr])
            G.graph['aggregation_zscores'] = scores

        score = 0
        len_cluster = 0
        for n in G.nodes:
            if attr in G.nodes[n]:
                score += G.nodes[n][attr]
                len_cluster += 1
        return score / math.sqrt(len_cluster)

    @staticmethod
    def hypergeometric_score(G: nx.Graph, cluster: Set, attr: str) -> float:
        """
        inspired by
        Breitling, Rainer, Anna Amtmann, and Pawel Herzyk.
        Graph-based iterative Group Analysis enhances microarray interpretation.
        BMC bioinformatics 5.1 (2004): 100.
        :param G:
        :type G:
        :param cluster:
        :type cluster:
        :param attr:
        :type attr:

        Note: better used with no background correction
        """
        if 'ranking_scores' not in G.graph:
            scores = []
            for n in G.nodes:
                if attr in G.nodes[n]:
                    scores.append((n, G.nodes[n][attr]))
            scores.sort(key = lambda x: x[1], reverse=True)
            ranks = {y[0]:x+1 for x, y in enumerate(scores)}
            G.graph['ranking_scores'] = ranks

        score = 0
        len_cluster = 0
        worse_rank = 0
        for n in cluster:
            if n in G.graph['ranking_scores']:
                worse_rank = max(worse_rank, G.graph['ranking_scores'][n])
                len_cluster += 1
        return 1 - hypergeom.pmf(len_cluster, G.graph['nb_nodes'], worse_rank, len_cluster)

    @staticmethod
    def measure_f1(G: nx.Graph, real_cluster: Set, pred_cluster: Set) -> float:
        prediction = [0] * G.graph['nb_nodes']
        for x in pred_cluster:
            prediction[x] = 1
        real = [0] * G.graph['nb_nodes']
        for x in real_cluster:
            real[x] = 1
        return metrics.f1_score(real, prediction)

#     @staticmethod
    # faster way to compute recall
#     def measure_recall(G :nx.Graph, real_cluster :Set, pred_cluster :Set) -> float:
#         return len(pred_cluster & real_cluster) / len(real_cluster)

    @staticmethod
    def measure_recall(G: nx.Graph, real_cluster: Set, pred_cluster: Set) -> float:
        prediction = [0] * G.graph['nb_nodes']
        for x in pred_cluster:
            prediction[x] = 1
        real = [0] * G.graph['nb_nodes']
        for x in real_cluster:
            real[x] = 1
        return metrics.recall_score(real, prediction)
