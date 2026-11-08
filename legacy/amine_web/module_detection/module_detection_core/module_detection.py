#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Module containing the ModuleDetection class."""

from random import Random
from .scores import Scores
from .datasets import Datasets
from . import models
import statistics
import networkx as nx
import sys
import os
from scipy.stats import norm
import itertools

class ModuleDetection():
    """A class representing the module detection algorithm."""

    def __init__(self, G, model, fitness_function, background_correction=True):
        """
        Class initialization.

        Parameters
        ----------
        G                     : nx.Graph
                                the graph
        model                 : models.Model
                                the model
        fitness_function      : a function
                                the fitness function must accept two parameters
                                (a graph and a set of nodes) and return a float
        background_correction : bool
                                specify is a background correction must be performed

        """
        self.rng = Random()
        self.G = G
        self.mod = model
        self.fitness_function = fitness_function
        self.background_correction = background_correction
        self.bkg_scores_by_cluster_size = {}

    def get_bkg_score(self, size, ensure_connected=True):
        """
        Calculate the mean and standard deviation of the score of random nodes.

        Parameters
        ----------
        size : int
               the number of node in the set
        ensure_connected : bool
               indicates if the set of nodes must constitutes a connected module

        """
        try:
            return self.bkg_scores_by_cluster_size[size]
        except KeyError:
            scores_for_random_cluster = []
            if ensure_connected:
                components = [self.G.subgraph(c).copy() for c in nx.connected_components(self.G) if len(c) >= size]
                possible_seeds = []
                for component in components:
                    possible_seeds.extend(component.nodes)

                """
                    by uncommenting the code below, we restrict the seeds to be in the 10% more expressed nodes,
                    resulting in an increase of the mean background zscore
                """
                # list_nodes = sorted([x for x in self.G.nodes], key=lambda x: self.G.nodes[x]['weight'], reverse=True)
                # list_nodes = list_nodes[:len(list_nodes)//10]
                # possible_seeds = list(set(possible_seeds).intersection(list_nodes))


            for _ in range(10000):
                if ensure_connected:
                    seed = self.rng.choice(possible_seeds)
                    random_cluster = set([seed])
                    seeds = set([seed])
                    neighbors = set([n for n in self.G[seed]])
                    while len(random_cluster) < size:
                        random_cluster.update(self.rng.sample(neighbors, min(size-len(random_cluster), len(neighbors))))
                        seed = self.rng.sample(random_cluster - seeds, 1)[0]
                        seeds.add(seed)
                        neighbors = set([n for n in self.G[seed]]) - random_cluster
                else:
                    random_cluster = self.rng.sample(self.G.nodes, size)
                scores_for_random_cluster.append(
                    self.fitness_function(self.G, random_cluster))
            mean = statistics.mean(scores_for_random_cluster)
            dev = statistics.pstdev(scores_for_random_cluster)
            self.bkg_scores_by_cluster_size[size] = (mean, dev)
        return (mean, dev)

    def get_score(self, cluster, ensure_connected_bgmodule=True):
        """
        Get the score of a cluster.

        Parameters
        ----------
        cluster : iterable
                  set of nodes
        ensure_connected_bgmodule : bool
               indicates if the set of background nodes must constitutes a connected module

        """
        score = self.fitness_function(self.G, cluster)
        pvalue = 0
        if self.background_correction:
            mean, dev = self.get_bkg_score(len(cluster), ensure_connected_bgmodule)
            score = (score - mean) / dev
            pvalue = 1-norm.cdf(score)
        return score, pvalue

    def predict_modules(self, relevant_nodes=None, max_nb_modules=None, cutoff=None):
        """
        Predict a list of active module.

        Parameters
        ----------
        relevant_nodes : iterable
                         nodes on which research will be focused
        max_nb_modules : int
                         maximum number of modules to return. if None, returns all modules
        cutoff         : float
                         cutoff used for pvalue

        """
        """
        memorization of the best clusters

        each solution is a tuple composed of:
            - the center node
            - the diameter (number of closest nodes)
            - the list of nodes in the cluster
            - the fitness
            - the pvalue of the fitness is background correction is used
        """
        best = []

        # max and min size of a module
        max_size = self.G.graph['nb_nodes'] - 1
        min_size = 3

        relevant_nodes_id = set([]) 
        if relevant_nodes:
            relevant_nodes_id = set([x for x in self.G.nodes if self.G.nodes[x]['label'] in relevant_nodes])
        prioritary_nodes = sorted([x for x in self.G.nodes if x in relevant_nodes_id], key=lambda x: self.G.nodes[x]['weight'], reverse=True)
        other_nodes = sorted([x for x in self.G.nodes if x not in relevant_nodes_id], key=lambda x: self.G.nodes[x]['weight'], reverse=True)
        """
		uncommenting the lines below allows to speed up things by processing only a part of the nodes
        """
#        """use 10% of the nodes + their 3 closest nodes"""
#         list_nodes = list_nodes[:len(list_nodes)//10]
#         closest_nodes = set(list_nodes)
#         for n in list_nodes:
#             similar = self.mod.get_most_similar(n, 3)
#             closest_nodes.update(set(similar))
#         list_nodes = list(closest_nodes)
        list_nodes = prioritary_nodes + other_nodes

        for n in list_nodes:
            similar = self.mod.get_most_similar(n, max_size - 1)
            clus = [n]
            best_for_this_node = (0, 0, None, 0, 1)

            for x in range(max_size - 1):
                clus = clus + [similar[x]]
                if len(clus) < min_size:
                    continue
                score, pvalue = self.get_score(clus)

                if score > best_for_this_node[3]:
                    best_for_this_node = (n, x + 1, clus, score, pvalue)
                else:
                    break

            if best_for_this_node == (0, 0, None, 0, 1):
                continue

            best.append(best_for_this_node)

        # Sort the best modules by their scores
        best = sorted([x for x in best], key=lambda x: x[3], reverse=True)

        # enlarge the clusters and put the results in predicted
        predicted = []
        while best:
            predicted.append(best[0])
            best = best[1:]
            # collect solutions centered on nodes belonging to the processed module
            while "the score of the module is increasing":
                """
                Collect in other_modules, the set of nodes belonging to other modules whose center is in predicted
                """
                other_modules = set([frozenset(x[2]) for x in best if x[0] in set(predicted[-1][2])])
                """
                uncommenting the line below allows to use another strategy to get possible modules
                by looking only at the intersection of the modules
                """
#                 other_modules = set([frozenset(x[2]) for x in best if set(x[2]) & set(predicted[-1][2])])

                # collect in 'candidates' the list of potential additions to the current module
                candidates = set()
                strategy = 1
                if strategy == 1:
                    # Union with other modules
                    candidates = other_modules
                elif strategy == 2:
                    # Union with a combination of other modules
                    for size in range(3):
                        for combination in itertools.combinations(other_modules, size+1):
                            new_clus = set(predicted[-1][2])
                            for solution in combination:
                                new_clus |= solution
                            candidates.add(frozenset(new_clus))
                elif strategy == 3:
                    # Union with neighborood
                    for x, _ in self.G.adj.items():
                        if x not in predicted[-1][2]:
                            continue
                elif strategy == 4:
                    # Union with the genes belonging to other modules
                    for x in other_modules:
                        candidates.add(frozenset(x))
                elif strategy == 5:
                    # Union with combination of at most 3 genes from other modules
                    for x in other_modules:
                        for size in range(3):
                            for combination in itertools.combinations(x, min(len(x), size+1)):
                                new_clus = set(predicted[-1][2]) | set(combination)
                                candidates.add(frozenset(new_clus))
                elif strategy == 6:
                    # Union with combination of the genes in other modules
                    for x in other_modules:
                        new_genes = set(predicted[-1][2]) - set(x)
                        for size in range(len(new_genes)):
                            for combination in itertools.combinations(new_genes, size+1):
                                new_clus = set(predicted[-1][2]) | set(combination)
                                candidates.add(frozenset(new_clus))

                best_combination = predicted[-1]

                for candidate in candidates:
                    if set(predicted[-1][2]).issuperset(candidate):
                        continue
                    new_clus = set(predicted[-1][2]) | candidate
                    score, pvalue = self.get_score(new_clus)
                    if score > best_combination[3]:
                        best_combination = (0, 0, sorted(new_clus), score, pvalue)

                # put in new best all modules that doesn't intersect with the processed one
                try_another_combination = False
                if best_combination[3] > predicted[-1][3]:
                    predicted[-1] = best_combination
                    try_another_combination = True
                # recompute new best
                if relevant_nodes_id:
                    best = [x for x in best if not (set(x[2]) & set(predicted[-1][2])) or (set(x[2]) & relevant_nodes_id)]
                else:
                    best = [x for x in best if not (set(x[2]) & set(predicted[-1][2]))]
                if not try_another_combination:
                    break

        sorted_modules = [x[2:] for x in sorted(predicted, key=lambda x: x[3], reverse=True)]
        """remove duplicates"""
        predicted_modules = []
        last = set()
        for x in sorted_modules:
            if set(x[0]) != last:
                predicted_modules.append((sorted(x[0]), x[1], x[2]))
                last = set(x[0])
        
        predicted_modules = [x for x in predicted_modules if set(x[0]) & relevant_nodes_id] \
            + [x for x in predicted_modules if not (set(x[0]) & relevant_nodes_id)]

        if max_nb_modules:
            predicted_modules = predicted_modules[:max_nb_modules]
        if cutoff:
            predicted_modules = [x for x in predicted_modules if x[2] <= cutoff]
        """
            output format for each predicated module
            1 - list of nodes (space separated)
            2 - zscore
            3 - pvalue
        """
        return predicted_modules

# def write_matrix(G,file_name="adj_teste"):
#     FILE = os.getcwd() + "/results/graphs/"
#     A = nx.adjacency_matrix(G, nodelist=None, weight='weight')
#     size = len(G)
#     with open(FILE + file_name + '.tsv', 'w') as output_final:
#         for i in range(size):
#             outline = []
#             for j in range(size):
#                 outline.append(str(A[i, j]) + "\t")
#             output_final.write("".join(outline) + "\n")
# 
#     with open(FILE + file_name + '_weight.tsv', 'w') as output_finalw:
#         for node in G.nodes:
#             outline = []
#             outline.append(str(G.nodes[node]['weight']))
#             output_finalw.write("".join(outline) + "\n")
# 
#     with open(FILE + file_name + '_hittrue.tsv', 'w') as output_finalt:
#         k = 0
#         for node in G.nodes:
#             outline = []
#             if G.nodes[node]['truehit'] == 1:
#                 outline.append(str(k))
#                 output_finalt.write("".join(outline) + "\n")
#             k += 1

def test_zacchary():
    G = Datasets.get_zachary_graph()
#         data = np.array(nx.adjacency_matrix(G, sorted(G.nodes),
#                                          weight=None).todense(), dtype=np.float_)
#         P, D, Q = np.linalg.svd(data, full_matrices=False)
#         print(P)
#         print(P.shape, D.shape, Q.shape)
#         import scipy
#         P = P * D
#         P = P[:,0:3]
#         dist = scipy.spatial.distance.cdist(P[0:1], P[0:], 'cosine')
#         print(dist[0])
#         enum = sorted(list(enumerate(dist[0].tolist())), key=lambda x:x[1])
#         print(enum)
#         dd
    mod = models.Node2vec()
    mod.init(G)
#         print(mod.get_most_similar(0, 8))
#         mod = models.RandomWalk()
#         mod.init(G)
#         print(mod.get_most_similar(0, 8))
#         mod = models.SVD()
#         mod.init(G)
#         print(mod.get_most_similar(0, 8))
        # mod.save('foo.mod')
        # mod = models.Node2vec.load('foo.mod')
    fitness_function = Scores.modularity
    module_detection = ModuleDetection(G, mod, fitness_function)
    # do the prediction
    clustering = module_detection.predict_modules()

    total_modularity = 0
#     for comm in clustering.values():
#         print(Scores.modularity(G, set(comm)))
#         total_modularity += Scores.modularity(G, set(comm))
    print("community score obtained with 4 clusters={}".format(total_modularity))
    sys.exit(1)
        # get the optimal communities based on this paper:
        # Rizman Žalik, K., & Žalik, B. (2018).
        # Node attraction-facilitated evolution algorithm for community detection in networks.
        # Soft Computing, 1–9.
        # https://doi.org/10.1007/s00500-018-3267-x
    communities = Datasets.get_groups(G, "group_Zalik2018")
        # compare with the best modularity score specified in this paper:
        # Pattanayak, H. S., Sangal, A. L., & Verma, H. K. (2019).
        # Community detection in social networks based on fire propagation.
        # Swarm and Evolutionary Computation, 44(February 2018), 31–48.
        # https://doi.org/10.1016/j.swevo.2018.11.006
    best_modularity = 0.41880341
    total_modularity = 0
    for comm in communities.values():
        total_modularity += Scores.modularity(G, set(comm))
    print("community score obtained with 4 clusters={}".format(total_modularity))
    print("expected value =                         {}".format(best_modularity))
#         f1_score = predict_one_group(G, mod, fitness_fun)
#         print("f1_score = {}".format(f1_score))

# def detect_module():


if __name__ == '__main__':
    """
    The module cannot be executed with main.

    use process_real_network or process_artificial_network instead
    """
