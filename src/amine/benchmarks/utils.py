#!/usr/bin/env python

"""Module containing some preprocessing for using Louvain method."""

# import community as community_louvain
# import networkx as nx
from random import Random

from ..amine_exception import AmineException


def proportion_of_interesting(G, cluster):
    interesting = [x for x in cluster if is_interesting(G, x)]
    return len(interesting) / len(cluster)


def is_interesting(G, n):
    if G.nodes[n]["weight"] < 0.01:
        return True
    else:
        return False


def remove_isolated_ininteresting(G):
    nodes = [x for x in G.nodes]
    for n in nodes:
        if not is_interesting(G, n):
            neigh = [1 if is_interesting(G, x) else 0 for x in G.neighbors(n)]
            if sum(neigh) == 0:
                G.remove_node(n)


def preprocess_network(G, method="keep_edges", alpha=0.5):
    if method == "keep_edges":
        for e in G.edges:
            if is_interesting(G, e[0]) and is_interesting(G, e[1]):
                G.edges[e]["weight"] = (
                    1
                    - alpha
                    + (1 - alpha)
                    * max(0, 1 - G.nodes[e[0]]["weight"] * G.nodes[e[1]]["weight"])
                )
            else:
                G.edges[e]["weight"] = float(alpha)
    elif method == "merge":
        for e in G.edges:
            G.edges[e]["weight"] = alpha
        for v in G.nodes:
            for w in G.nodes:
                if v == w:
                    continue
                weight = (1 - alpha) * max(
                    0, 1 - G.nodes[v]["weight"] * G.nodes[w]["weight"]
                )
                # weight = max(0, 1-alpha-G.nodes[v]['weight']-G.nodes[w]['weight'])
                if w in G.neighbors(v):
                    G.edges[v, w]["weight"] = alpha + weight
                else:
                    if weight > 0.9:
                        G.add_edge(v, w, weight=weight)
    elif method == "original":  # method used in original amine (change node weight)
        for node in G.nodes():
            for nbr in sorted(G.neighbors(node)):
                # #                    G[node][nbr]['weight'] = 1 - ( abs(G.nodes[node]['weight']
                # #                                - G.nodes[nbr]['weight']) - G.nodes[node]['weight'] ) / 2
                G[node][nbr]["weight"] = 1 - abs(
                    G.nodes[node]["weight"] - G.nodes[nbr]["weight"]
                )
    # #                    G[node][nbr]['weight'] = min(1, max(0, 1 - \
    # #                        abs(G.nodes[node]['weight'] - G.nodes[nbr]['weight'])))

    elif method == "none":
        pass
    else:
        raise AmineException(f"preprocessing method {method} not known.")


def remove_edges(G, remove_ratio, seed=None):
    if remove_ratio > 0:
        nbtoremove = int(G.number_of_edges() * remove_ratio)
        if seed:
            rng = Random(seed)
        else:
            rng = Random()
        edges_to_remove = rng.sample(G.edges, nbtoremove)
        G.remove_edges_from(edges_to_remove)
        G.graph["nb_edges"] = G.number_of_edges()


def convert_to_amine_format(G, communities, fitness_fun):
    res = {}
    for node, com in communities.items():
        try:
            res[com].append(node)
        except KeyError:
            res[com] = [node]
    results = sorted(
        [(x, fitness_fun(G, x), 0) for _, x in res.items() if len(x) > 2],
        key=lambda x: x[1],
        reverse=True,
    )
    return results


def my_louvain(G, fitness_fun):
    """Greedy Louvain-like community detection scored by ``fitness_fun``.

    The historical experimental code referenced a ``my_louvain`` helper that
    was never committed. This lightweight replacement uses NetworkX's Louvain
    implementation to obtain a partition and then scores each community with
    ``fitness_fun`` so that the ``alouvain`` back-end can be benchmarked
    alongside the others.
    """
    import networkx as nx

    communities = nx.community.louvain_communities(G, weight="weight", seed=0)
    res = {ctr: list(com) for ctr, com in enumerate(communities)}
    results = sorted(
        [(x, fitness_fun(G, x), 0) for _, x in res.items() if len(x) > 2],
        key=lambda x: x[1],
        reverse=True,
    )
    return results
