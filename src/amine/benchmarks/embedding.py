#!/usr/bin/env python

"""
Various embedding models.

Each class defined here is instanciated with a networkx graph
After instanciation, it is possible to get, according to the embedding,
the closest nodes to a specific node with the method 'get_most_similar'
"""

import os
import pathlib
import subprocess
import time
from abc import ABC

import networkx as nx
import numpy as np
import scipy
from gensim.models import FastText, Word2Vec
from sklearn import manifold

# from . import utils
from .. import datasets
from ..amine_exception import AmineException
from ..dimension_reduction import node2vec
from ..dimension_reduction.pecanpy import node2vec as n2v


class Embedding(ABC):
    """
    abstract class.

    Three implementation are proposed:
        - SpectralEmbedding
        - Node2vec,
        - RandomWalk
        - SVD.
    """

    def __init__(self, G: nx.Graph, ordered_nodes: list = None):
        """initalization

        Parameters
        ----------
        G : nx.Graph
            the graph
        ordered_nodes : list, optional
            the list of ordered node, by default None

        Note
        ----
        if ordered_nodes is not specified, the order of nodes is the same as in the graph
        """

        self.reduced_matrix = None
        if ordered_nodes:
            self.ordered_nodes = ordered_nodes
        else:
            self.ordered_nodes = list(G.nodes())
        self.node_to_index = {y: x for x, y in enumerate(self.ordered_nodes)}
        # print(f"ordered nodes= {self.ordered_nodes}")
        # print(self.node_to_index)

    def get_vectors(self) -> np.array:
        """get the reduced matrix

        Returns
        -------
        numpy.array
            the reduced matrix
        """
        return self.reduced_matrix

    def get_most_similar(
        self, elt: int, number: int = None, metric: str = "cosine"
    ) -> list:
        """Collect similar nodes

        Parameters
        ----------
        elt : int
            node identifier
        number : _type_, optional
            number of most similar nodes to collect, by default None
        metric : str, optional
            the metric used to compute the distance, by default 'cosine'

        Returns
        -------
        list
            the list of closest nodes
        """
        index_of_elt = self.node_to_index[str(elt)]
        dist = scipy.spatial.distance.cdist(
            self.reduced_matrix[index_of_elt : index_of_elt + 1],
            self.reduced_matrix,
            metric=metric,
        )[0]
        similars = [x[0] for x in sorted(enumerate(dist), key=lambda x: x[1])[1:]]
        if number:
            return similars[:number]

    def get_distance(self, elt1: int, elt2: int, metric: str = "cosine") -> float:
        """
        Return the distance between two elements.

        Parameters
        ----------
        elt1 : int
            first element
        elt2 : int
            second element
        metric : str, optional
            the metric used to compute the distance, by default 'cosine'

        Returns
        -------
        float
            the distance between elt1 and elt2

        """
        index_of_elt1 = self.node_to_index[str(elt1)]
        index_of_elt2 = self.node_to_index[str(elt2)]
        return scipy.spatial.distance.cdist(
            self.reduced_matrix[index_of_elt1 : index_of_elt1 + 1],
            self.reduced_matrix[index_of_elt2 : index_of_elt2 + 1],
            metric,
        )[0][0]


class SpectralEmbedding(Embedding):
    """SpectralEmbedding model."""

    def __init__(
        self, G: nx.Graph, ordered_nodes: list = None, precomputed: bool = None
    ):
        """initalization

        Parameters
        ----------
        G : nx.Graph
            the graph
        ordered_nodes : list, optional
            the list of ordered node, by default None
        precomputed : bool, optional
            a precomputed model to be loaded, by default None

        Note
        ----
        if ordered_nodes is not specified, the order of nodes is the same as in the graph
        """
        super().__init__(G, ordered_nodes=ordered_nodes)

        self.dimensions = 16

        matrix = nx.adjacency_matrix(G, nodelist=self.ordered_nodes)
        embedding = manifold.SpectralEmbedding(
            n_components=self.dimensions, affinity="precomputed"
        )
        self.reduced_matrix = embedding.fit_transform(matrix)

    def get_most_similar(self, elt: int, number=None, metric: str = "cosine") -> list:
        """Collect similar nodes

        Parameters
        ----------
        elt : int
            node identifier
        number : _type_, optional
            number of most similar nodes to collect, by default None
        metric : str, optional
            the metric used to compute the distance, by default 'cosine'

        Returns
        -------
        list
            the list of closest nodes
        """
        index_of_elt = self.node_to_index[elt]
        dist = scipy.spatial.distance.cdist(
            self.reduced_matrix[index_of_elt : index_of_elt + 1],
            self.reduced_matrix,
            metric=metric,
        )[0]
        similars = [x[0] for x in sorted(enumerate(dist), key=lambda x: x[1])[1:]]
        if number:
            return similars[:number]


class WordEmbeddingBased(Embedding):
    """
    class grouping the methods based on word embedding
    i.e : word2vec, fasttext and pecanpy implementation
    """

    def __init__(
        self, G: nx.Graph, ordered_nodes: list = None, precomputed: bool = None
    ):
        """initalization

        Parameters
        ----------
        G : nx.Graph
            the graph
        ordered_nodes : list, optional
            the list of ordered node, by default None
        precomputed : bool, optional
            a precomputed model to be loaded, by default None

        Note
        ----
        if ordered_nodes is not specified, the order of nodes is the same as in the graph
        """
        super().__init__(G, ordered_nodes=ordered_nodes)

        self.model = None
        self.num_walks = 10  # 20  # 10
        self.walk_length = 80  # 100  # 80
        self.directed = False
        self.param_p = 1  # 4  # 0.15
        self.param_q = 1  # 2
        self.dimensions = 128  # 64  # 128
        self.window_size = 10  # 20  # 10
        self.workers = 4
        self.epoch = 1  # 20 #10
        self.node_to_index = {str(y): x for x, y in enumerate(self.ordered_nodes)}
        # print(f"ordered nodes2= {self.ordered_nodes}")

        # print(self.node_to_index)

    def get_most_similar(
        self, elt: int, number: int = None, metric: str = "cosine"
    ) -> list:
        """Collect similar nodes

        Parameters
        ----------
        elt : int
            node identifier
        number : _type_, optional
            number of most similar nodes to collect, by default None
        metric : str, optional
            the metric used to compute the distance, by default 'cosine'

        Returns
        -------
        list
            the list of closest nodes
        """
        index_of_elt = self.node_to_index[str(elt)]
        dist = scipy.spatial.distance.cdist(
            self.reduced_matrix[index_of_elt : index_of_elt + 1],
            self.reduced_matrix,
            metric=metric,
        )[0]
        # print(f"dist = {dist}")
        # print(f"node_to_index = {self.node_to_index}")
        similars = [
            self.ordered_nodes[x[0]]
            for x in sorted(enumerate(dist), key=lambda x: x[1])[1:]
        ]
        # similars = [ x[0] for x in sorted(enumerate(dist),
        #     key = lambda x : x[1])][1:]
        # print(f"ordered nodes3= {self.ordered_nodes}")
        # print(self.model.wv.index_to_key)
        # similars = [self.model.wv.index_to_key[x] for x in similars]
        if number:
            return similars[:number]
        else:
            return similars


class Node2vec(WordEmbeddingBased):
    """Node2vec model."""

    def __init__(
        self, G: nx.Graph, ordered_nodes: list = None, precomputed: bool = None
    ):
        """initalization

        Parameters
        ----------
        G : nx.Graph
            the graph
        ordered_nodes : list, optional
            the list of ordered node, by default None
        precomputed : bool, optional
            a precomputed model to be loaded, by default None

        Note
        ----
        if ordered_nodes is not specified, the order of nodes is the same as in the graph
        """
        super().__init__(G, ordered_nodes=ordered_nodes)

        if precomputed and pathlib.Path(precomputed).is_file():
            self.model = Word2Vec.load(precomputed)
        else:
            self.compute_embedding(G)
            if precomputed:
                self.save(precomputed)

    def compute_embedding(self, G: nx.Graph):
        """Compute the embedding

        Parameters
        ----------
        G : nx.Graph
            the graph
        """
        graph = node2vec.Graph(G, self.directed, self.param_p, self.param_q)
        graph.preprocess_transition_probs()
        walks = graph.simulate_walks(
            self.num_walks, self.walk_length, nodes=self.ordered_nodes
        )

        # Learn embeddings by optimizing the Skipgram objective using SGD.
        walks = [list(map(str, walk)) for walk in walks]
        self.model = Word2Vec(
            walks,
            vector_size=self.dimensions,  # size=self.dimensions,
            window=self.window_size,
            min_count=5,
            negative=5,
            sg=1,
            workers=self.workers,
            epochs=self.epoch,
        )  # iter=self.epoch)
        matrix = self.model.wv.get_normed_vectors()

        # print(matrix)
        # nodes have been transformed to string to perform Word2Vec
        # we need now to use the mapping with nodes expressed as strings
        node_to_index = {str(x[0]): x[1] for x in self.node_to_index.items()}
        # print(node_to_index)
        # print(sorted(enumerate(self.model.wv.index_to_key)))
        new_order = [
            x[0]
            for x in sorted(
                enumerate(self.model.wv.index_to_key),
                key=lambda x: self.node_to_index[x[1]],
            )
        ]
        # new_order = [self.node_to_index[x] for x in self.model.wv.index_to_key]
        self.reduced_matrix = matrix[new_order][:]
        # print(self.model.wv.index_to_key)
        # print(new_order)
        # print(self.reduced_matrix)
        # print(f"ordered nodes 4= {self.ordered_nodes}")

        ### added for tests
        # elt = '3'
        # print(f"most similar to '{elt}' (node2vec)")
        # print([int(x[0]) for x in self.model.wv.similar_by_word(str(elt))])
        # print("most similar to '3' (with matrix)")
        # print(self.get_most_similar(elt))
        # dd

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

    # def get_distance(self, elt1, elt2):
    #     """
    #     Return the distance between two elements.

    #     Parameters
    #     ----------
    #     elt1 : str
    #         first element
    #     elt2 : str
    #         second element

    #     """
    #     return self.model.wv.distance(str(elt1), str(elt2))


class Fasttext(WordEmbeddingBased):
    """Fasttext model."""

    def __init__(
        self, G: nx.Graph, ordered_nodes: list = None, precomputed: bool = None
    ):
        """initalization

        Parameters
        ----------
        G : nx.Graph
            the graph
        ordered_nodes : list, optional
            the list of ordered node, by default None
        precomputed : bool, optional
            a precomputed model to be loaded, by default None

        Note
        ----
        if ordered_nodes is not specified, the order of nodes is the same as in the graph
        """
        super().__init__(G, ordered_nodes=ordered_nodes)
        self.compute_embedding(G)

    def compute_embedding(self, G: nx.Graph):
        """Compute the embedding

        Parameters
        ----------
        G : nx.Graph
            the graph
        """
        graph = node2vec.Graph(G, self.directed, self.param_p, self.param_q)
        graph.preprocess_transition_probs()
        walks = graph.simulate_walks(
            self.num_walks, self.walk_length, nodes=self.ordered_nodes
        )

        # Learn embeddings by optimizing the Skipgram objective using SGD.
        walks = [list(map(str, walk)) for walk in walks]
        self.model = FastText(
            vector_size=self.dimensions,
            window=self.window_size,
            min_count=1,
            sentences=walks,
            epochs=self.epoch,
            max_n=0,
            sg=1,
        )
        matrix = self.model.wv.get_normed_vectors()
        # nodes hav been transformed to string to perform Word2Vec
        # we need now to use the mapping with nodes expressed as strings
        node_to_index = {str(x[0]): x[1] for x in self.node_to_index.items()}
        new_order = [
            x[0]
            for x in sorted(
                enumerate(self.model.wv.index_to_key), key=lambda x: node_to_index[x[1]]
            )
        ]
        self.reduced_matrix = matrix[new_order][:]


class Pecanpy(WordEmbeddingBased):
    """Pecanpy model."""

    def __init__(
        self, G: nx.Graph, ordered_nodes: list = None, precomputed: bool = None
    ):
        """initalization

        Parameters
        ----------
        G : nx.Graph
            the graph
        ordered_nodes : list, optional
            the list of ordered node, by default None
        precomputed : bool, optional
            a precomputed model to be loaded, by default None

        Note
        ----
        if ordered_nodes is not specified, the order of nodes is the same as in the graph
        """
        super().__init__(G, ordered_nodes=ordered_nodes)
        self.compute_embedding(G)

    def compute_embedding(self, G: nx.Graph):
        """Compute the embedding

        Parameters
        ----------
        G : nx.Graph
            the graph
        """
        use_pecanpy_cmdline = False
        if use_pecanpy_cmdline:
            timestamp = time.time_ns()
            edges_file = f"{datasets.TEMPDIR}/edges_{timestamp}.txt"
            with open(edges_file, "w") as outfile:
                for u, v, att in G.edges(data=True):
                    source = u if isinstance(u, int) else f"'{u}'"
                    target = v if isinstance(v, int) else f"'{v}'"
                    outfile.write(f"{source}\t{target}\t{att['weight']}\n")

            embedding_file = f"{datasets.TEMPDIR}/embedding_{timestamp}.txt"

            command = f"pecanpy --input {edges_file} --output {embedding_file} --mode SparseOTF \
                --weighted --dimensions {self.dimensions} --walk-length {self.walk_length} \
                --num-walks {self.num_walks} --window-size {self.window_size} --epochs {self.epoch} \
                --p {self.param_p} --q {self.param_q} --extend"
            subprocess.call(command, shell=True, stdout=subprocess.PIPE)
            with open(embedding_file, "r") as infile:
                rows, columns = infile.readline().strip().split()
                self.reduced_matrix = np.zeros((int(rows), int(columns)))
                for line in infile:
                    tokens = line.split()
                    try:
                        key = int(tokens[0])
                    except ValueError:
                        key = tokens[0][1:-1]
                    try:
                        self.reduced_matrix[self.node_to_index[key]][:] = np.array(
                            [float(x) for x in tokens[1:]]
                        )
                    except IndexError:
                        print(tokens[0])
                        print(self.node_to_index[tokens[0]])
            os.remove(edges_file)
            os.remove(embedding_file)
        else:
            graph = n2v.SparseOTF(
                p=self.param_p,
                q=self.param_q,
                workers=self.workers,
                verbose=False,
                extend=True,
            )
            A = np.array(
                nx.adjacency_matrix(
                    G, nodelist=self.ordered_nodes, weight="weight"
                ).todense(),
                dtype=np.float64,
            )
            graph.from_mat(A, self.ordered_nodes)
            self.reduced_matrix = graph.embed(
                dim=self.dimensions,
                num_walks=self.num_walks,
                walk_length=self.walk_length,
                window_size=self.window_size,
                epochs=self.epoch,
            )


class RandomWalk(Embedding):
    """RandomWalk model."""

    # convergence criterion - when vector L1 norm drops below 10^(-6)
    # (this is the same as the original RWR paper)
    conv_threshold = 0.000001

    def __init__(
        self, G: nx.Graph, ordered_nodes: list = None, precomputed: bool = None
    ):
        """initalization

        Parameters
        ----------
        G : nx.Graph
            the graph
        ordered_nodes : list, optional
            the list of ordered node, by default None
        precomputed : bool, optional
            a precomputed model to be loaded, by default None

        Note
        ----
        convergence criterion is when vector L1 norm drops below 10^(-6)
        (this is the same as the original RWR paper)
        """
        super().__init__(G, ordered_nodes=ordered_nodes)

        self.walk_length = 0
        self.restart_prob = 0
        self.T = None

        """
        Initialize the model with a weighted graph.


        """
        self.walk_length = 200
        self.restart_prob = 0.7

        # Create the adjacency matrix of G
        A = np.array(
            nx.adjacency_matrix(
                G, nodelist=self.ordered_nodes, weight="weight"
            ).todense(),
            dtype=np.float64,
        )
        # Create the degree matrix
        D = np.diag(np.sum(A, axis=0))

        # The Laplacian matrix L, not used here is equal to D - A

        # Compute the inverse of D
        # Several solutions are possible
        #     - first solution: numpy.inverse
        #       inverse_of_d = numpy.linalg.inv(D)
        #     - second solution: numpy.solve
        #       inverse_of_d = numpy.linalg.solve(D, numpy.identity(len(nodes_list))
        #     - third solution, as the matrix is diagonal, one can use
        #       the inverse of the diagonal values
        #       inverse_of_d = np.diag(1 / np.diag(D))

        inverse_of_d = np.diag(1 / np.diag(D))

        # compute the transition matrix
        self.T = np.dot(inverse_of_d, A)

    def get_most_similar(
        self, elt: int, number: int = None, metric: str = "default"
    ) -> list:
        """Collect similar nodes

        Parameters
        ----------
        elt : int
            node identifier
        number : _type_, optional
            number of most similar nodes to collect, by default None
        metric : str, optional
            the metric used to compute the distance, this must be equal to default

        Returns
        -------
        list
            the list of closest nodes
        """
        if metric != "default":
            raise AmineException(
                "For randomWalk model, the metric must be equal to 'default'"
            )
        arr = [0] * len(self.ordered_nodes)
        arr[self.node_to_index[elt]] = 1
        p_0 = np.array(arr)
        state_matrix = p_0
        for _ in range(self.walk_length):
            # evaluate the next state vector
            p_1 = (1 - self.restart_prob) * np.dot(
                state_matrix, self.T
            ) + self.restart_prob * p_0

            # calculate L1 norm of difference between p^(t + 1) and p^(t),
            # for checking the convergence condition
            diff_norm = np.linalg.norm(np.subtract(p_1, state_matrix), 1)
            if diff_norm < RandomWalk.conv_threshold:
                break
        state_matrix = p_1
        result = sorted(
            enumerate(state_matrix.tolist()), key=lambda res: res[1], reverse=True
        )
        return [self.ordered_nodes[x[0]] for x in result][1 : number + 1]


class SVD(Embedding):
    """SVD model."""

    def __init__(
        self, G: nx.Graph, ordered_nodes: list = None, precomputed: bool = None
    ):
        """initalization

        Parameters
        ----------
        G : nx.Graph
            the graph
        ordered_nodes : list, optional
            the list of ordered node, by default None
        precomputed : bool, optional
            a precomputed model to be loaded, by default None
        """
        super().__init__(G, ordered_nodes=ordered_nodes)

        A = np.array(
            nx.adjacency_matrix(G, self.ordered_nodes, weight=None).todense(),
            dtype=np.float64,
        )
        U, S, _ = np.linalg.svd(A, full_matrices=False)
        reduced_dimension = 16  # A.shape[0] // 5
        matrix = U * S
        self.reduced_matrix = matrix[:, 0:reduced_dimension]

    def get_most_similar(self, elt: int, number=None, metric: str = "cosine") -> list:
        """Collect similar nodes

        Parameters
        ----------
        elt : int
            node identifier
        number : _type_, optional
            number of most similar nodes to collect, by default None
        metric : str, optional
            the metric used to compute the distance, by default 'cosine'

        Returns
        -------
        list
            the list of closest nodes
        """
        index_of_elt = self.node_to_index[elt]
        dist = scipy.spatial.distance.cdist(
            self.reduced_matrix[index_of_elt : index_of_elt + 1],
            self.reduced_matrix,
            metric=metric,
        )[0]
        similars = [x[0] for x in sorted(enumerate(dist), key=lambda x: x[1])[1:]]
        if number:
            return similars[:number]


def get_embedding_model(name: str, G: nx.Graph) -> Embedding:
    """Get an embedding of the graph by its name

    Parameters
    ----------
    name : str
        the name of the embedding
    G : nx.Graph
        the graph

    Returns
    -------
    Embedding
        the embedding

    Raises
    ------
    AmineException
        when the embedding is unknown
    """

    if name == "node2vec":
        return Node2vec(G)
    elif name == "fasttext":
        return Fasttext(G)
    elif name == "pecanpy":
        return Pecanpy(G)
    elif name == "spectral":
        return SpectralEmbedding(G)
    elif name == "svd":
        return SVD(G)
    elif name == "randomwalk":
        return RandomWalk(G)
    # elif name == "mane":
    #     return Mane(G)
    elif name == "none":
        return None
    else:
        raise AmineException(f"embedding method {name} not known.")
