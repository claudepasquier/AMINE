#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Various graph models.

Each class defined here is instanciated with a networkx graph
After instanciation, it is possible to get, according to the model,
the closest nodes to a specific node with the method 'get_most_similar'
"""

from .dimension_reduction import node2vec
from gensim.models import Word2Vec
import networkx as nx
import numpy as np
from scipy.spatial import distance
import pathlib

from abc import ABC, abstractmethod


class Model(ABC):
    """
    abstract class.

    Three implementation are proposed:
        - Node2vec,
        - RandomWalk
        - SVD.
    """

    @abstractmethod
    def get_most_similar(self, elt, nb):
        """
        Collect similar nodes ; method implemented by each subclass.

        Parameters
        ----------
        elt : str
             node identifier
        nb : int
             number of most similar nodes to collect

        """
        pass


class Node2vec(Model):
    """Node2vec model."""

    def __init__(self):
        """Declare variables."""
        self.model = None
        self.num_walks = 10  # 10
        self.walk_length = 100  # 80
        self.directed = False
        self.param_p = 4  # 0.15
        self.param_q = 1  # 2
        self.dimensions = 64  # 128
        self.window_size = 5  # 10
        self.workers = 4
        self.epoch = 10

    def init(self, G, precomputed=None):
        """
        Initialize the model with a weighted graph.

        Parameters
        ----------
        G           : nx.Graph
                      the graph used to initialize the model
        precomputed : None, str or file-like object
                      None or path to the precomputed model that must be used

        """
        if precomputed and pathlib.Path(precomputed).is_file():
            self.model = Word2Vec.load(precomputed)
        else:
            for node in G.nodes():
                for nbr in sorted(G.neighbors(node)):
                    G[node][nbr]['weight'] = 1 - abs(G.nodes[node]['weight'] - G.nodes[nbr]['weight'])
            self.compute_embedding(G)
            if precomputed:
                self.save(precomputed)

    def compute_embedding(self, G):
        """
        Compute embedding.

        Parameters
        ----------
        G           : nx.Graph
                      the processed graph

        """
        Gr = node2vec.Graph(G, self.directed, self.param_p, self.param_q)
        Gr.preprocess_transition_probs()
        walks = Gr.simulate_walks(self.num_walks, self.walk_length)

        # Learn embeddings by optimizing the Skipgram objective using SGD.
        walks = [list(map(str, walk)) for walk in walks]
        self.model = Word2Vec(walks,
                              size=self.dimensions,
                              window=self.window_size,
                              min_count=0,
                              sg=1,
                              workers=self.workers,
                              iter=self.epoch)

    def save(self, fname_or_handle):
        """
            Save the model to file.

        Parameters
        ----------
        fname_or_handle : str or file-like object
                          path or handle to file where the model will be persisted

        """
        self.model.save(fname_or_handle)

    def load(self, fname_or_handle):
        """
        Load a previously saved model from a file.

        Parameters
        ----------
        fname_or_handle : str or file-like object
                          path or handle to file that contains the model

        """
        self.model = Word2Vec.load(fname_or_handle)

    def get_most_similar(self, elt, nb):
        """
        Collect similar nodes.

        Parameters
        ----------
        elt : str
              node identifier
        nb : int
             number of most similar nodes to collect

        """
        return [int(x[0]) for x in self.model.wv.similar_by_word(str(elt), topn=nb)]

    def get_distance(self, elt1, elt2):
        """
        Return the distance between two elements.

        Parameters
        ----------
        elt1 : str
            first element
        elt2 : str
            second element

        """
        return self.model.wv.distance(str(elt1), str(elt2))


class RandomWalk(Model):
    """RandomWalk model."""

    """
        convergence criterion - when vector L1 norm drops below 10^(-6)
        (this is the same as the original RWR paper)
    """
    conv_threshold = 0.000001

    def __init__(self):
        """Declare variables."""
        self.nodelist = None
        self.walkLength = 0
        self.restart_prob = 0
        self.T = None

    def init(self, G):
        """
        Initialize the model with a weighted graph.

        Parameters
        ----------
        G           : nx.Graph
                      the graph used to initialize the model

        """
        self.nodelist = sorted(G.nodes)
        self.walkLength = 200
        self.restart_prob = 0.7

        # Create the adjacency matrix of G
        A = np.array(nx.adjacency_matrix(G, nodelist=self.nodelist,
                                         weight=None).todense(), dtype=np.float_)
        # Create the degree matrix
        D = np.diag(np.sum(A, axis=0))

        # The Laplacian matrix L, not used here is equal to D - A

        """
            Compute the inverse of D
            Several solutions are possible
                - first solution: numpy.inverse
                  D_inv = numpy.linalg.inv(D)
                - second solution: numpy.solve
                  D_inv = numpy.linalg.solve(D, numpy.identity(len(nodes_list))
                - third solution, as the matrix is diagonal, one can use
                  the inverse of the diagonal values
                  D_inv = np.diag(1 / np.diag(D))
        """
        D_inv = np.diag(1 / np.diag(D))

        # compute the transition matrix
        self.T = np.dot(D_inv, A)

    def get_most_similar(self, elt, nb):
        """
        Collect similar nodes.

        Parameters
        ----------
        elt : str
              node identifier
        nb : int
             number of most similar nodes to collect

        """
        arr = [0] * len(self.nodelist)
        arr[elt] = 1
        p_0 = np.array(arr)  # reshape(-1,1)
        p = p_0
        for _ in range(self.walkLength):

            # evaluate the next state vector
            p_1 = (1 - self.restart_prob) * \
                np.dot(p, self.T) + self.restart_prob * p_0

            """
            calculate L1 norm of difference between p^(t + 1) and p^(t),
            for checking the convergence condition
            """
            diff_norm = np.linalg.norm(np.subtract(p_1, p), 1)
            if diff_norm < RandomWalk.conv_threshold:
                break
        p = p_1
        result = sorted(enumerate(p.tolist()),
                        key=lambda res: res[1], reverse=True)
        return [int(x[0]) for x in result][1:nb + 1]


class SVD(Model):
    """SVD model."""

    def __init__(self):
        """Declare variables."""
        self.nodelist = None
        self.most_similar = []

    def init(self, G):
        """
        Initialize the model with a weighted graph.

        Parameters
        ----------
        G           : nx.Graph
                      the graph used to initialize the model

        """
        self.nodelist = sorted(G.nodes)
        A = np.array(nx.adjacency_matrix(G, sorted(G.nodes),
                                         weight=None).todense(), dtype=np.float_)
        u, s, _ = np.linalg.svd(A, full_matrices=False)
        reduced_dimension = A.shape[0] // 5
        reduced_matrix = u * s
        reduced_matrix = reduced_matrix[:, 0:reduced_dimension]
        self.most_similar = []
        for ctr in range(reduced_matrix.shape[0]):
            dist = distance.cdist(
                reduced_matrix[ctr:ctr + 1], reduced_matrix[0:], 'cosine')
            self.most_similar.append([x[0] for x in sorted(
                list(enumerate(dist[0].tolist())), key=lambda x:x[1])][1:])

    def get_most_similar(self, elt, nb):
        """
        Collect similar nodes.

        Parameters
        ----------
        elt : str
              node identifier
        nb : int
             number of most similar nodes to collect

        """
        return self.most_similar[elt][:nb]
