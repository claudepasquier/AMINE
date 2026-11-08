#!/usr/bin/env python
# -*- coding: utf-8 -*-

import networkx as nx
import numpy as np
from . import utils
import scipy


def predict(G, emb, fitness_fun, neighbor_size=5):
    if emb:
        neighbors = {x: emb.get_most_similar(x, neighbor_size) for x in G.nodes}
    else:
        neighbors = {x: list(nx.neighbors(G, x)) for x in G.nodes}

    fitnesses = {x: fitness_fun(G, y + [x]) for x, y in neighbors.items()}
    csos = []
    outliers = []
    for node, neigh in neighbors.items():
        neigh_fitnesses = [fitnesses[x] for x in neigh]
        if fitnesses[node] > max(neigh_fitnesses):
            csos.append(node)
        elif fitnesses[node] < min(neigh_fitnesses):
            outliers.append(node)
    print(csos, outliers)
    # expanding outliers
    expanded = True
    while expanded:
        expanded = False
        for node, neigh in neighbors.items():
            if node in outliers or node in csos:
                continue
            neigh = [x for x in neigh if x not in outliers]
            if not neigh:
                outliers.append(node)
                expanded = True
                continue
            neigh_fitnesses = [fitnesses[x] for x in neigh]
            if fitnesses[node] < min(neigh_fitnesses):
                outliers.append(node)
                # print(f"outliers expanded with {node}")
                expanded = True
    print(f"csos= {csos}")
    print(f"outliers= {outliers}")
    nb_classes = len(csos) + len(outliers)
    memberships = {x: [1 / nb_classes] * nb_classes for x in G.nodes}
    for ctr in range(len(csos)):
        memberships[csos[ctr]] = [0] * nb_classes
        memberships[csos[ctr]][ctr] = 1
    for ctr in range(len(outliers)):
        memberships[outliers[ctr]] = [0] * nb_classes
        memberships[outliers[ctr]][len(csos) + ctr] = 1
    for n in G.nodes:
        memberships[n] = np.array(memberships[n])

    ctr = 0
    alpha = 0.5
    delta = 1e-4 * len(G.nodes)
    while True:
        # print(f"iteration {ctr} : {memberships}")
        new_memberships = {}
        for n, _ in memberships.items():
            if emb:
                theoretical_membership = np.mean(
                    [
                        (1 - emb.get_distance(n, x)) * np.array(memberships[x])
                        for x in neighbors[n]
                    ],
                    axis=0,
                )
            else:
                theoretical_membership = np.mean(
                    [np.array(memberships[x]) for x in neighbors[n]], axis=0
                )
            if n in csos:
                new_memberships[n] = memberships[n]
                # surrounding = [np.argmax(memberships[x]) for x in neighbors[n]]
                # if np.all(surrounding == surrounding[0]) and surrounding[0] != np.argmax(memberships[n]):
                #     print(f"englobing cso {n} in {surrounding[0]}")
                #     new_memberships[n] = alpha * memberships[n] + (1 - alpha) * theoretical_membership
                #     csos.remove(n)
                # else:
                #     new_memberships[n] = memberships[n]
                # print(surrounding)
                # ff
                # new_memberships[n] = memberships[n]
                # if np.argmax(memberships[n]) != np.argmax(theoretical_membership):
                #     new_memberships[n] = theoretical_membership
                # else:
                #     new_memberships[n] = memberships[n]
            elif n in outliers:
                new_memberships[n] = memberships[n]
            else:
                new_memberships[n] = theoretical_membership
            # new_memberships[n] = (alpha * memberships[n] + (1 - alpha) * np.mean([np.array(memberships[x]) for x in neighbors[n]], axis = 0))
            # print(neigh_memberships)
        change = 0
        for x, y in memberships.items():
            new_y = new_memberships[x]
            # print(scipy.spatial.distance.cdist([y], [new_y], metric='euclidean')[0])
            change += scipy.spatial.distance.cdist([y], [new_y], metric="euclidean")[0][
                0
            ]
        # print(ctr, change)
        memberships = new_memberships
        if change < delta:
            break
        # ctr += 1
        # if ctr == 100:
        #     break

    clustering = {}
    for n in G.nodes:
        clustering[n] = np.argmax(memberships[n])
    results = utils.convert_to_amine_format(G, clustering, fitness_fun)
    return results
