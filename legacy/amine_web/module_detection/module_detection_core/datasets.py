#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module creating and initializing various datasets.

The created graphs are networkx graphs with the following additional characteristics:
    - each node can have a weight which is specified with the attribute 'weight'
    - each graph can be associated with ground truth information that can be
    - a clustering or a specific module. The attribute storing the ground truth is specified
      with the graph attribute 'groups'
"""

import pandas as pd
import networkx as nx
import os
import numpy as np
from scipy.stats import truncnorm
from zipfile import ZipFile
from random import Random
from numpy.random import RandomState
from .parameters import Param

from typing import Dict, Set
try:
    import toml
    TOML_INSTALLED = True
except ImportError:
    TOML_INSTALLED = False


"""
the directory where all included datasets are located
"""
DATADIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "data")

"""
co publication network: 5242 edges & 14496 nodes
details at http://snap.stanford.edu/data/ca-GrQc.html
"""
COPUBLICATION_FILE = os.path.join(DATADIR, "ca-GrQc.txt.gz")


class Datasets:
    """Class for accessing datasets."""

    @staticmethod
    def get_graph(name=None, filename=None) -> nx.Graph:
        """
        Get a graph by its name.

        Parameters
        ----------
        name           : str
                         the name of the graph (can be dolphins, netscience)
        filename       : str or file-like object
                         path to a graph file

        """
        if not filename:
            if not name:
                return None
            for (dirpath, _, filenames) in os.walk(DATADIR):
                files = [x for x in filenames if x.startswith(name+'.')]
                for f in files:
                    if f[-4:] == ".gml":
                        filename = os.path.join(dirpath, f)
                        break
        if not filename:
            return None
        G = nx.read_gml(filename, label='id')
        return Datasets.init_graph(G, name=name)

    @staticmethod
    def get_zachary_graph() -> nx.Graph:
        """
        Get the graph of Zachary karate club network.

        The network is defined in:
            W. W. Zachary
            An information flow model for conflict and fission in small groups
            Journal of Anthropological Research 33, 452-473 (1977).
        """
        zachary_file = os.path.join(DATADIR, "zachary.gdf")
        G: nx.Graph = Datasets.import_gdf(zachary_file)
        return Datasets.init_graph(G, node_weight=None, edge_weight=None, default_groups='group_Zachary1977')

    @staticmethod
    def get_copublication_graph() -> nx.Graph:
        """Get copublication graph."""
        df = pd.read_csv(COPUBLICATION_FILE, sep='\t', usecols=[
                         0, 1], header=None, comment='#')
        elist = list(df.itertuples(index=False, name=None))
        G = Datasets.create_graph(elist)
        return G

    @staticmethod
    def get_ppi_string_graph(specie,
                             min_neighborhood: int = 0,
                             min_fusion: int = 0,
                             min_cooccurence: int = 0,
                             min_coexpression: int = 0,
                             min_experimental: int = 0,
                             min_database: int = 0,
                             min_textmining: int = 0,
                             min_combined_score: int = 0,
                             weight = 1):
        """
        Read a String PPI graph, applying various filters on the interaction scores.

        Parameters
        ----------
        specie             : str
                             the specie modeled by the interaction graph
        min_neighborhood   : int
                             minimum neighborhood score
        min_fusion         : int
                             minimum fusion score
        min_cooccurence    : int
                             minimum cooccurence score
        min_coexpression   : int
                             minimum coexpression score
        min_experimental   : int
                             minimum experimental score
        min_database       : int
                             minimum database score
        min_textmining     : int
                             minimum textmining score
        min_combined_score : int
                             minimum combined score
        weight             : int or a string
                             the value of weight between nodes, specified as
                             an int or an attribute name
        Returns
        -------
         the graph as an nx.Graph instance

        """
        df = pd.read_csv(Param.get_string_ppi_file(specie), sep=' ', header=0)
        df = df[df.neighborhood >= min_neighborhood]
        df = df[df.fusion >= min_fusion]
        df = df[df.cooccurence >= min_cooccurence]
        df = df[df.coexpression >= min_coexpression]
        df = df[df.experimental >= min_experimental]
        df = df[df.database >= min_database]
        df = df[df.textmining >= min_textmining]
        df = df[df.combined_score >= min_combined_score]
        columns = list(df.columns)[2:]
        if weight in columns:
            columns = list(set(columns) - set([weight]))
        df = df.drop(columns=columns)

        df2 = pd.read_csv(Param.get_string_info_file(specie), sep='\t', header=0)
        df2 = df2.drop(columns=['protein_size', 'annotation'])
        mapping = {str(x[0]): str(x[1]) for x in list(df2.itertuples(index=False, name=None))}
        df['protein1'] = df['protein1'].map(mapping)
        df['protein2'] = df['protein2'].map(mapping)
        if weight in list(df.columns):
            df['weight'] = df[weight].map(lambda x: x/1000)
            del df[weight]
        else:
            sLength = len(df['protein1'])
            df['weight'] = pd.Series([weight] * sLength, index=df.index)
        print(df.head())
        elist = [(x[0], x[1], {'weight': x[2]}) for x in list(df.itertuples(index=False, name=None))]
        G = Datasets.create_graph(elist)
        return G

    @staticmethod
    def set_nodes_value(G, attr, node2value, default_value=None, case_sensitive=True):
        """
        Set values to nodes.

        Parameters
        ----------
        G              : nx.Graph
                         the graph to weight
        attr           : str
                         the name of the attribute storing the value
        node2value     : dict
                         a dict mapping node ids to values
        default_value  : float
                         a default value for nodes not in node2value
        case_sensitive : bool
                         indicate if the mapping of node ids is case sensitive

        """
        nb_mapped = 0
        print(len(G.nodes))
        if not case_sensitive:
            node2value = {x.upper():y for x, y in node2value.items()}
            node2id = {n:G.nodes[n]['label'].upper() for n in G.nodes}
        else:
            node2id = {n:G.nodes[n]['label'] for n in G.nodes}
        for n, label in node2id.items():
            if label in node2value:
                nb_mapped += 1
                G.nodes[n][attr] = node2value[label]
            else:
                if default_value:
                    G.nodes[n][attr] = default_value
                else:
                    pass
        print('nb mapped=', nb_mapped, 'out of', len(list(node2value.keys())))
        return G

    @staticmethod
    def map_query_to_gene_name(query, specie):
        """
        Replace gene node with node name.

        Parameters
        ----------
        query          : iterable
                         query terms
        specie         : str
                         the specie modeled by the interaction graph

        Returns
        -------
        the mapping between query terms and gene names
        """
        df = pd.read_csv(Param.get_string_alias_file(specie), sep='\t', header=1)
        lst = list(df.itertuples(index=False, name=None))
        
        """Identification of source."""
        id2source = {x[1]:x[2].split() for x in lst}
        sources = {}
        for node in query:
            try:
                for src in id2source[node]:
                    try:
                        sources[src] += 1
                    except KeyError:
                        sources[src] = 1
            except KeyError:
                pass
        """Selected source is the one that allows to map the largest number of ids""" 
        source = sorted([(x,y) for x,y in sources.items()], key=lambda x : x[1], reverse=True)[0]
        query2stringid = {x[1]:x[0] for x in lst if source[0] in x[2]}
        
        df = pd.read_csv(Param.get_string_info_file(specie), sep='\t', header=0, names=['id', 'name', 'size', 'annotation'])
        df = df.astype({'name': 'str'})
        lst = list(df.itertuples(index=False, name=None))

        stringid2name = {x[0]:x[1] for x in lst}
        mapping = {}
        for node in query:
            try:
                mapping[node] = stringid2name[query2stringid[node]]
            except KeyError:
                pass
        return mapping 

#     @staticmethod
#     def set_gene_name(node2value, specie, merging):
#         """
#         Replace gene node with node name.
# 
#         Parameters
#         ----------
#         node2value     : dict
#                          a dict mapping node ids to values
#         specie         : str
#                          the specie modeled by the interaction graph
#         merging        : str
#                          action to perform in case of multiple mappings
#                          sum = add the values
#                          avg = average the values
#                          no = no merging
# 
#         Returns
#         -------
#         the mapping with gene ids replaced with gene names
#         """
#         df = pd.read_csv(Param.get_string_alias_file(specie), sep='\t', header=1)
#         lst = list(df.itertuples(index=False, name=None))
#         
#         """Identification of source."""
#         id2source = {x[1]:x[2].split() for x in lst}
#         sources = {}
#         for node in node2value.keys():
#             try:
#                 for src in id2source[node]:
#                     try:
#                         sources[src] += 1
#                     except KeyError:
#                         sources[src] = 1
#             except KeyError:
#                 pass
#         """Selected source is the one that allows to map the largest number of ids""" 
#         source = sorted([(x,y) for x,y in sources.items()], key=lambda x : x[1], reverse=True)[0]
#         id2stringid = {x[1]:x[0] for x in lst if source[0] in x[2]}
#         
#         df = pd.read_csv(Param.get_string_info_file(specie), sep='\t', header=0, names=['id', 'name', 'size', 'annotation'])
#         df = df.astype({'name': 'str'})
#         lst = list(df.itertuples(index=False, name=None))
# 
# #         stringid2name = {x[0]:x[1] for x in lst if 'Ensembl_EntrezGene' in x[2] and 'Ensembl_EntrezGene_' not in x[2]}
#         stringid2name = {x[0]:x[1] for x in lst}
# 
#         new_mapping = {}
#         for node, value in node2value.items():
#             try:
#                 name = stringid2name[id2stringid[node]]
#                 try:
#                     new_mapping[name].append(value)
#                 except KeyError:
#                     new_mapping[name] = [value]
#             except KeyError:
#                 pass
#         for node in new_mapping.keys():
#             if merging == "no":
#                 # in case of several mappings, use the first one
#                 new_value = new_mapping[node][0]
#             elif merging == 'sum':
#                 new_value = np.sum(new_mapping[node])
#             elif merging == 'avg':
#                 new_value = np.mean(new_mapping[node])
#             else:
#                 raise Exception("This part of code should not be reached")
#             new_mapping[node] = new_value
#         return new_mapping 
    
    @staticmethod
    def get_guyon_graph(nb):
        """
        Get a Guyon's graph.

        Parameters
        ----------
        nb : int
             the identifier of the graph

        Returns
        -------
         the graph as an nx.Graph instance

        """
        zip_file = ZipFile(os.path.join(DATADIR, "guyon.zip"))
        df = pd.read_csv(zip_file.open(
            "pp1_" + str(nb) + ".csv"), sep=',', header=0)
        df = df.drop(df.columns[0], axis=1)
        A = df.values
        G = nx.from_numpy_matrix(A)
        df = pd.read_csv(zip_file.open("pvalues.csv"), sep=',', header=0)
        df = df.drop(df.columns[0], axis=1)
        for ctr in range(G.number_of_nodes()):
            G.nodes[ctr]['weight'] = df.iloc[ctr, nb - 1]

        df = pd.read_csv(zip_file.open("truehits.csv"), sep=',', header=0)
        df = df.drop(df.columns[0], axis=1)
        for ctr in range(G.number_of_nodes()):
            G.nodes[ctr]['truehit'] = df.iloc[ctr, nb - 1]

        return Datasets.init_graph(G, edge_weight=None, default_groups='truehit')

    @staticmethod
    def get_leandro_graph(nb, module_size, removed_edges):
        """
        Get a Leandro's graph.

        Parameters
        ----------
        nb : int
             the identifier of the graph
        module_size : int
             the size of the module
        removed_edges : float
             the preportion of removed edges

        Returns
        -------
         the graph as an nx.Graph instance

        """
        filename = "size" + str(module_size) + ("_p" + str(int(removed_edges*100)) if removed_edges > 0 else "") + ".zip"
        zip_file = ZipFile(os.path.join("..", "sim_networks", filename))
        df = pd.read_csv(zip_file.open("size" + str(module_size) + "/" +
            "sim" + str(nb) + "._connection_list.csv"), sep=',', header=None)
        G = nx.from_pandas_adjacency(df)

        df = pd.read_csv(zip_file.open("size" + str(module_size) + "/" + "sim" + str(nb) + "_weight.csv"), sep=',', header=None)
        for ctr in range(G.number_of_nodes()):
            G.nodes[ctr]['weight'] = 1 - df.iloc[ctr, 0]

        df = pd.read_csv(zip_file.open("size" + str(module_size) + "/" + "sim" + str(nb) + "_hittrue.csv"), sep=',', header=None)
        assert df.size == module_size
        for ctr in range(G.number_of_nodes()):
            G.nodes[ctr]['truehit'] = 0
        for ctr in range(df.size):
            G.nodes[df.iloc[ctr, 0]]['truehit'] = 1

        return Datasets.init_graph(G, edge_weight=None, default_groups='truehit')

    @staticmethod
    def get_scale_free_graph(nb_nodes, nb_initial_nodes, nb_modules, module_size, p_prob, q_prob, rng_seed):
        """
        Get a scale free graph based on the extended_barabasi_albert_graph.

        Parameters
        ----------
        nb_nodes         : int
                           number of nodes in the graph
        nb_initial_nodes : int
                           number of initial nodes used by barabasi method
        nb_modules       : int
                           number of modules
        module_size      : int
                           size of each module
        p_prob           : float
                           probability value for adding an edge between existing nodes. p + q < 1
        q_prob           : float
                           probability value of rewiring of existing edges. p + q < 1
        rng_seed         : int or None
                           seed for the random number generator. If None, then global default RNG is used

        Returns
        -------
        the graph as an nx.Graph instance

        """
        def neighbors_order(G, start, k):
            """
            Get the neighbors of a node.

            Parameters
            ----------
            G       : nx.Graph
                      the simulated Network
            start   : node id
                      node that we want to know the neighborhood
            k       : int
                      neighborhood order

            Returns
            -------
            the neighborhood of "start" at order=k

            """

            nbrs = set([start])
            for _ in range(k):
                nbrs = set((nbr for n in nbrs for nbr in G[n]))
            return nbrs

        def knbrs(G, start, k):
            """
            :param G: Simulated Network
            :param start: node that we want to know the neighborhood
            :param k: Neighborhood Order
            :return: neighborhood of "start"
            """
            neighbohood = set()
            while k >= 1:
                nbrs = set([start])
                for _ in range(k):
                    nbrs = set((nbr for n in nbrs for nbr in G[n]))
                neighbohood.update(nbrs)
                k -= 1
            return neighbohood

        def get_seeds(G: nx.Graph, number_seeds, min_distance):
            """
            G: Graph containing simulated network
            number_of_seeds: Number of centers of groups
            min_distance: distance that each seed should be from each other
            """
            seeds = [] # type: List[int]
            list_deg = []
            deg = G.degree()
            for d in deg:
                list_deg.append(d[1])
            ndegree = np.quantile(list_deg, .8)
            # The variable "select" stores the vertices that can be chosen
            selected = []
            for d in deg:
                # Excludes vertices with a high degree of connectivity
                if d[1] <= ndegree:
                    selected.append(d[0])

            for _ in range(number_seeds):
                sel = []
                # Chooses a node randomly in the "selected" set
                rdn = np_rng.choice(selected, size=1)[0]
                sel.append(rdn)
                # check the neighborhood of the chosen node
                neighbors = knbrs(G, rdn, min_distance)
                # Removes the neighbors of the selected seed from the set "selected"
                selected = list(set(selected).difference(neighbors))
                # The function returns false if the set "selected" is empty, that is,
                # if the chosen minimum distance is very high
                if selected.__len__() == 0:
                    return False

                seeds = list(set().union(seeds, sel))

            return seeds

        if rng_seed is None:
            rng = Random()
            np_rng = RandomState()
        else:
            rng = Random(rng_seed)
            np_rng = RandomState(rng_seed)

        G = nx.extended_barabasi_albert_graph(nb_nodes, nb_initial_nodes, p_prob, q_prob, rng_seed)

        vertex_end = set(list(G.nodes))
        vertex_ini = set(range(nb_nodes))
        vertex_exc = vertex_ini.difference(vertex_end)
        assert not vertex_exc

        G.add_nodes_from(vertex_exc)
        for i in vertex_exc:
            j = int(np_rng.choice(list(vertex_end), size=1))
            G.add_edge(i, j)

        batra_method = False
        if batra_method:
            clusters = []
            k = 3
            from scores import Scores
            selected_nodes = set()
            while len(clusters) < nb_modules:
                group = set([rng.choice(list(G))])
                selected_nodes.update(group)
                while len(group) < module_size:
                    best_avg = 1000
                    best_node = None
                    for n in G.nodes:
                        if n in selected_nodes:
                            continue
#                         print(group, n)
                        avg = Scores.average_shortest_path(G, group | set([n]))
                        if abs(avg-k) < abs(best_avg-k):
                            best_avg, best_node = avg, n
                    group.add(best_node)
                    selected_nodes.add(best_node)
                clusters.append(group)
        else:
            # Guyon method

            # We chose a distance 10 between the seeds
            seeds = False
            distance = 10
            # If the distance is too high the algorithm decreases it and tries to identify the seeds again
            while type(seeds) == type(bool()):
                seeds = get_seeds(G, nb_modules, distance)
                distance -= 1
            neigh = set()
            clusters = []
            # The variable "neigh" stores the neighbors of the nodes that compose each group
            # Neighbors as well as seeds can not be selected.
            neigh.update(seeds)
            module_size -= 1
            count = 1
            for n in seeds:
                group = set()
                conect = set()
                group.add(n)
                nb_selected = 0
                while nb_selected < module_size:
                    finish = False
                    order = 0
                    rnd = rng.random()
                    # checks to neighborhood order 4 according with the function 1/pow(10, dist)
                    if rnd > 0.1 and rnd <= 1:
                        order = 1
                    elif 0.01 < rnd <= 0.1:
                        order = 2
                    elif 0.001 < rnd <= 0.01:
                        order = 3
                    elif 0.0001 < rnd <= 0.001:
                        order = 4
                    # neighbors_order returns all neighbors of the node n of a specific order
                    population = neighbors_order(G, n, order)
#                     print("population", population)
                    # Removes neighbors and nodes from other groups already identified
                    # besides the nodes of this same group that have already been chosen.
                    population = population - neigh
                    # After the phase above if there are no more nodes in the population
                    # the algorithm set the population using the next neighborhood order
                    while population.__len__() == 0:
                        order += 1
                        population = neighbors_order(G, n, order)
                        population = population - neigh
                        if order > 10:
                            finish = True
                            break
                    if not finish:
                        # one node is chosen randomly in the population
                        selected = np_rng.choice(list(population), size=1)[0]
                        group.add(selected)
                        # The variable neigh stores the node so that it is no more selected
                        neigh.add(selected)
                        # The entire neighborhood of the node (up to order 2) is saved so as
                        # not to be selected by a next seed
                        conect.update(knbrs(G, selected, 2))
                        nb_selected += 1
                    else:
                        print("pb: no selected module")
                        break # nothing selected

                neigh.update(conect)
                clusters.append(group)
                count += 1
        batra_method = False
        if batra_method:
            import scipy.stats
            for node in G.nodes:
                case = np_rng.normal(0, 1, 100)
                control = np_rng.normal(0, 1, 10)
                pvalue = scipy.stats.mannwhitneyu(case, control)[1]
                G.nodes[node]['weight'] = pvalue
                G.nodes[node]['truehit'] = 0

            for ctr in range(len(clusters)):
                for x in clusters[ctr]:
                    case = np_rng.normal(5, 1, 100)
                    control = np_rng.normal(2, 1, 10)
                    pvalue = scipy.stats.mannwhitneyu(case, control)[1]

                    G.nodes[x]['weight'] = pvalue
                    G.nodes[x]['truehit'] = ctr + 1

        else:
            # Guyon method
            # assign a uniform distribution for all nodes
            low, up = 0, 1
            for node in G.nodes:
                G.nodes[node]['weight'] = rng.uniform(low, up)
                G.nodes[node]['truehit'] = 0

            # assign a truncated normal distribution for each node in cluster
            mean, std = 0, 0.05
            a, b = (low - mean) / std, (up - mean) / std
            for ctr in range(len(clusters)):
                for x in clusters[ctr]:
                    G.nodes[x]['weight'] = truncnorm.rvs(
                        loc=mean, scale=std, a=a, b=b, random_state=np_rng)
                    G.nodes[x]['truehit'] = ctr + 1

        return Datasets.init_graph(G, edge_weight=None, default_groups='truehit')

    @staticmethod
    def get_barabasi_graph(nb_nodes: int, nb_initial_nodes: int, seed=None):
        """
        nb_nodes = number of nodes
        nb_initial_nodes = number of initial nodes
        """
        G = nx.barabasi_albert_graph(nb_nodes, nb_initial_nodes, seed=seed)
        return Datasets.init_graph(G)

    @staticmethod
    def create_graph(elist) -> nx.Graph:
        G = nx.Graph(elist)
        return Datasets.init_graph(G)

    @staticmethod
    def set_adjMatrix(df) -> nx.Graph:
        G = nx.from_pandas_adjacency(df)
        return Datasets.init_graph(G)

    @staticmethod
    def init_graph(G: nx.Graph, name="", node_weight='unchanged', edge_weight='unchanged', default_groups=None):
        """
        Initialize graph, nodes and edges attributes

        :param G: a graph
        :type G: networkx.Graph
        :param name: the name of the graph
        :type name: String
        :param node_weight: specify the weight of nodes
        :type node_weight: 'unchanged' or None for nodes with uniform weights equals to 1
        :param edge_weight: specify the weight of edges
        :type edge_weight: 'unchanged' or None for edges with uniform weights equals to 1
        :param default_groups: the node attribute representing the known group(s)
        :type default_groups: a string or None if the default_groups are unknown
        """

        # node labels must consist on consecutive integers starting at 0
        # if it is not the case, a mapping is necessary

        # convert nodes label to int if all labels are numbers and are
        # represented as strings

        # convert string labels to int values if possible
        try:
            if all([x.isdigit() for x in G.nodes]):
                mapping = {x: int(x) for x in G.nodes()}
                G = nx.relabel_nodes(G, mapping, copy=False)
        except AttributeError:
            pass

        mapping_needed = False

        if all(isinstance(n, int) for n in G.nodes()):
            if sorted([x for x in G.nodes()]) == list(range(G.number_of_nodes())):
                pass  # perfect
            else:
                mapping_needed = True
        else:
            mapping_needed = True

        if mapping_needed:
            nodes_mapping = dict(enumerate(sorted(G.nodes)))
            mapping = {y: x for x, y in nodes_mapping.items()}
            G = nx.relabel_nodes(G, mapping)
            for node in G.nodes:
                G.nodes[node]['label'] = nodes_mapping[node]
        for node in G.nodes:
            if 'weight' not in G.nodes[node] or node_weight is None:
                G.nodes[node]['weight'] = 1
        for edge in G.edges:
            if 'weight' not in G.edges[edge] or edge_weight is None:
                G.edges[edge]['weight'] = 1

        G.graph['default_groups'] = default_groups
        G.graph['nb_nodes'] = G.number_of_nodes()
        G.graph['nb_edges'] = G.number_of_edges()
        G.graph['name'] = name
        return G

    @staticmethod
    def get_groups(G: nx.Graph, groups_attribute=None) -> Dict[int, Set[int]]:
        """
        Return the groups identified in the graph.

        :param G: a graph
        :type G: networkx.Graph
        :param groups_attribute: the node attribute representing the known group(s)
        :type groups_attribute: a string of None to use default group
        """
        if not groups_attribute:
            groups_attribute = G.graph['default_groups']
        if not groups_attribute:
            return {}
        groups = {} # type: Map[int]
        for n in G.nodes:
            group_nb = int(G.nodes[n][groups_attribute])
            if group_nb == 0:
                continue
            try:
                groups[group_nb].add(n)
            except KeyError:
                groups[group_nb] = set([n])
        return groups

    @staticmethod
    def import_gdf(filename: str) -> nx.Graph:
        G = nx.Graph()
        with open(filename, 'r') as infile:
            nodedef = [] # type: List[str]
            edgedef = [] # type: List[str]
            in_toml_definition = False
            toml_desc = ""
            for line in infile:
                if not line or line.startswith('#'):
                    continue
                if line.startswith('nodedef>'):
                    nodedef = [x.strip() for x in line[8:].strip().split(',')]
                    edgedef = []
                    continue
                elif line.startswith('edgedef>'):
                    nodedef = []
                    edgedef = [x.strip() for x in line[8:].strip().split(',')]
                    continue
                elif line.strip() == '+++':
                    if in_toml_definition:
                        if TOML_INSTALLED:
                            data = toml.loads(toml_desc)
                            for key, value in data.items():
                                G.graph[key] = value
                        else:
                            print("toml is not installed. Ignoring metadata")
                        in_toml_definition = False
                    else:
                        in_toml_definition = True
                        continue
                if in_toml_definition:
                    toml_desc += line
                    continue
                if not (nodedef or edgedef):
                    continue
                tokens = [x.strip() for x in line.strip().split(',')]
                if nodedef:
                    node_id = tokens[0]
                    G.add_node(node_id)
                    for key, value in zip(nodedef[1:], tokens[1:]):
                        if key == 'weight':
                            G.nodes[node_id][key] = float(value)
                elif edgedef:
                    node_id1 = tokens[0]
                    node_id2 = tokens[1]
                    G.add_edge(node_id1, node_id2)
                    for key, value in zip(edgedef[2:], tokens[2:]):
                        if key == 'weight':
                            G[node_id1][node_id2][key] = float(value)
        return G
