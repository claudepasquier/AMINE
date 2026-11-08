#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Implementation of OPTICS clustering algorithm.

defined in:
Ankerst, M., Breunig, M. M., Kriegel, H. P., & Sander, J. (1999).
OPTICS: Ordering points to identify the clustering structure.
ACM Sigmod record, 28(2), 49-60.

see: https://fr.wikipedia.org/wiki/OPTICS

"""

from networkx.classes.function import neighbors


class Optics:
    """Optics class for clustering."""

    def __init__(self, G, minPts, maxDistance, caller):
        """Declare variables."""
        self.processed = set()  # list of processed nodes
        self.reachability_distance = {}
        self.core_distance = {}
        self.max_size = 10
        self.G = G
        self.minPts = minPts
        self.maxDistance = maxDistance
        self.caller = caller

    def clustering(self):
        ordered_list = []
        #     max_size = 10 #G.graph['nb_nodes'] - 1
        for n in self.G.nodes:
            if n not in self.processed:
                self.expandClusterOrder(
                    self.G,
                    n,
                    self.minPts,
                    self.maxDistance,
                    self.max_size,
                    ordered_list,
                    self.caller,
                )
        ordered_list = [x for x in ordered_list if x[1]]  # excluding outliers
        print(ordered_list)
        #     ordered_list.sort(key=lambda x: x[1])
        #         clusters = self.extract_clusters_xi_mine(ordered_list, self.minPts, self.maxDistance)
        clusters = self.extract_clusters_amine(
            ordered_list, self.minPts, self.maxDistance
        )
        print(clusters)
        return clusters

    def expandClusterOrder(
        self, G, node, minPts, maxDistance, max_size, ordered_list, caller
    ):
        neighbors = self.get_neighbors(node, maxDistance, max_size, caller)
        assert node not in self.processed
        self.processed.add(node)
        self.core_distance[node] = self.get_core_distance(
            node, neighbors, minPts, caller
        )
        ordered_list.append([node, self.core_distance[node], self.core_distance[node]])
        orderedSeeds = []
        if self.core_distance[node]:
            orderedSeeds = []
            self.update_seeds(orderedSeeds, node, neighbors, caller)
            while orderedSeeds:
                seed = orderedSeeds.pop(0)
                current_node = seed[0]
                r_dist = seed[1]
                neighbors = self.get_neighbors(
                    current_node, maxDistance, max_size, caller
                )
                assert current_node not in self.processed
                self.processed.add(current_node)
                self.core_distance[current_node] = self.get_core_distance(
                    current_node, neighbors, minPts, caller
                )
                ordered_list.append(
                    [current_node, self.core_distance[current_node], r_dist]
                )
                if self.core_distance[current_node]:
                    self.update_seeds(orderedSeeds, current_node, neighbors, caller)

    def update_seeds(self, orderedSeeds, node, neighbors, caller):
        c_dist = self.core_distance[node]
        for n in neighbors:
            if not n in self.processed:
                new_r_dist = max(c_dist, self.get_distance(node, n, caller))
                if (
                    n not in self.reachability_distance
                    or self.reachability_distance == None
                ):
                    self.reachability_distance[n] = new_r_dist
                    orderedSeeds.append([n, new_r_dist])
                    orderedSeeds.sort(key=lambda x: x[1])
                else:
                    if new_r_dist < self.reachability_distance[n]:
                        self.reachability_distance[n] = new_r_dist
                        for indx in range(len(orderedSeeds)):
                            if orderedSeeds[indx][0] == n:
                                break
                        orderedSeeds[indx][1] = new_r_dist
                        orderedSeeds.sort(key=lambda x: x[1])

    def get_core_distance(self, node, neighbors, minPts, caller):
        if len(neighbors) < minPts - 1:
            return None
        #         min_distance = 1e6
        #         for n in neighbors[minPts-1:]:
        #             min_distance = min(min_distance, self.get_distance(node, n, caller))
        #         return min_distance
        return self.get_distance(node, neighbors[minPts - 2], caller)

    def get_distance(self, n1, n2, caller):
        distance = "zscore"  # choice between 'cosine', 'module_pvalue', 'sum_of_pvalues', 'zscore'
        if distance == "cosine":
            distance = caller.mod.get_distance(n1, n2)
        elif distance == "module_pvalue":
            neighbors = caller.mod.get_most_similar(n1, caller.G.graph["nb_nodes"] - 1)
            indx = neighbors.index(n2)
            cluster = neighbors[: indx + 1]
            cluster.append(n1)
            _, distance = caller.get_score(cluster)
        elif distance == "sum_of_pvalues":
            neighbors = caller.mod.get_most_similar(n1, caller.G.graph["nb_nodes"] - 1)
            distance = self.G.nodes[n1]["weight"]
            previous_node = n1
            for n in neighbors:
                distance += (self.G.nodes[n]["weight"]) * caller.mod.get_distance(
                    previous_node, n
                )
                previous_node = n
                if n == n2:
                    break
        elif distance == "zscore":
            attr = "weight"
            if "z" not in caller.G.graph:
                from scipy.stats import norm

                scores = {}
                for n in caller.G.nodes:
                    if attr in caller.G.nodes[n]:
                        scores[n] = norm.ppf(1 - caller.G.nodes[n][attr])
                caller.G.graph["z"] = scores
            neighbors = caller.mod.get_most_similar(n1, caller.G.graph["nb_nodes"] - 1)
            distance = caller.G.nodes[n1][attr]
            previous_node = n1
            for n in neighbors:
                distance += (1 - caller.G.graph["z"][n]) * caller.mod.get_distance(
                    previous_node, n
                )
                previous_node = n
                if n == n2:
                    break
        return distance

    def get_neighbors(self, node, maxDistance, max_size, caller):
        neighbors = caller.mod.get_most_similar(node, max_size - 1)
        #     if neighbors and maxDistance:
        #         for indx_of_excluded_elt in range(len(neighbors)):
        #             if get_distance(node, neighbors[indx_of_excluded_elt], caller) > maxDistance:
        #                 break
        #         neighbors = neighbors[:indx_of_excluded_elt]
        return neighbors

    def extract_clusters_mine(self, ordered_list, minPts, maxDistance):
        cluster_id = 0
        clustering = {}
        clustering[-1] = []  # noise
        previous_core_distance = 1e6
        for elt in ordered_list:
            n = elt[0]
            core_distance = elt[1]
            if core_distance <= previous_core_distance:
                cluster_id += 1
            previous_core_distance = core_distance
            try:
                clustering[cluster_id].append(n)
            except KeyError:
                clustering[cluster_id] = [n]
        clustering = {x: y for x, y in clustering.items() if len(y) >= minPts}
        return clustering

    def extract_clusters_dbscan(self, ordered_list, minPts, maxDistance):
        cluster_id = 0
        clustering = {}
        clustering[-1] = []  # noise
        for elt in ordered_list:
            n = elt[0]
            if (
                n not in self.reachability_distance
                or self.reachability_distance == None
            ):
                clustering[-1].append(n)
            elif maxDistance and self.reachability_distance[n] > maxDistance:
                if self.core_distance[n] <= maxDistance:
                    cluster_id += 1
                    clustering[cluster_id] = [n]
                else:
                    clustering[-1].append(n)
            else:
                try:
                    clustering[cluster_id].append(n)
                except KeyError:
                    clustering[cluster_id] = [n]
        return clustering

    def extract_clusters_xi(self, ordered_list, minPts, maxDistance):
        xi = 0.05
        setOfSteepDownAreas = set()
        setOfClusters = set()
        index = 0
        mib = 0
        while index < len(ordered_list) - 1:
            reachability = self.reachability_distance[ordered_list[index]]
            reachability_next = self.reachability_distance[ordered_list[index + 1]]
            mib = max(mib, reachability)
            startOfSteepDown = reachability * (1 - xi) >= reachability_next
            startOfSteepUp = reachability_next * (1 - xi) >= reachability
            if startOfSteepDown:
                setOfSteepDownAreas = set(
                    [
                        [x[0], x[1], max(x[2], reachability)]
                        for x in setOfSteepDownAreas
                        if x[1] * (1 - xi) < mib
                    ]
                )
                mib = reachability
                setOfSteepDownAreas.add([index, reachability, mib])
                index += 1
            elif startOfSteepUp:
                while (
                    self.reachability_distance[ordered_list[index]]
                    < self.reachability_distance[ordered_list[index + 1]]
                ):
                    index += 1
                mib = self.reachability_distance[ordered_list[index]]
                setOfSteepDownAreas = set(
                    [
                        [x[0], x[1], max(x[2], reachability)]
                        for x in setOfSteepDownAreas
                        if mib * (1 - xi) > x[2]
                    ]
                )
                for d in setOfSteepDownAreas:
                    if index - d[0] < minPts:
                        continue
                    if d[1] * (1 - xi) >= mib:  # condition 4b

                        s = max()
                        e = index
            else:
                index += 1

    def extract_clusters_xi_mine(self, ordered_list, minPts, maxDistance):
        xi = 0.05
        listOfSteepDownAreas = []
        listOfClusters = []
        index = 0
        endsOfSteepUp = None
        print(self.reachability_distance)
        listOfSteepDownAreas.append(
            [index, 0, ordered_list[index][2]]
        )  # start, end, reachability

        while index < len(ordered_list) - 1:
            reachability = ordered_list[index][2]
            reachability_next = ordered_list[index + 1][2]
            #             try:
            #                 reachability = self.reachability_distance[ordered_list[index][0]]
            #             except KeyError:
            #                 reachability = 1e6
            #             try:
            # #                 print(self.reachability_distance[ordered_list[index+1][0]])
            #                 reachability_next = self.reachability_distance[ordered_list[index+1][0]]
            #             except KeyError:
            #                 reachability_next = 1e6
            startOfSteepDown = reachability * (1 - xi) >= reachability_next
            startOfSteepUp = reachability_next * (1 - xi) >= reachability
            print(
                "index",
                index,
                ordered_list[index],
                reachability,
                reachability_next,
                startOfSteepDown,
                startOfSteepUp,
            )
            if endsOfSteepUp and (
                startOfSteepDown or index == len(ordered_list) - 2
            ):  # or startOfSteepUp):
                endsOfSteepUp.append(index + 1)
                print("listOfSteepDownAreas", listOfSteepDownAreas)
                for d in listOfSteepDownAreas:
                    s = d[0]
                    e = index + 1
                    if d[2] * (1 - xi) >= reachability:  # condition 4b
                        while s + 1 < e and ordered_list[s + 1][2] >= reachability:
                            s += 1
                    elif reachability * (1 - xi) >= d[2]:
                        endsOfSteepUp.reverse()
                        for index in endsOfSteepUp:
                            if ordered_list[index][2] >= d[2]:
                                e = index
                            else:
                                break
                    #                         while e+1 > s and ordered_list[e-1][1] >= d[2]:
                    #                             e -= 1
                    print("s,e=", s, e)
                    listOfClusters.append([s, e])
                listOfSteepDownAreas = []
                endsOfSteepUp = None
            if startOfSteepDown:
                #                 if lastSteepUp:
                #                     listOfSteepDownAreas = []
                #                     lastSteepUp = None
                listOfSteepDownAreas.append(
                    [index, 0, reachability]
                )  # start, end, reachability
            elif startOfSteepUp:
                if listOfSteepDownAreas:  # if some steepdown have already been found
                    if (
                        not endsOfSteepUp
                    ):  # this is the lowest point, just before the steepUp
                        for D in listOfSteepDownAreas:  # update the end of steepDown
                            D[1] = index + 1
                        endsOfSteepUp = [index + 1]
            index += 1
        clusters = {}
        print("list_ofclusters", listOfClusters)
        for i in range(len(listOfClusters)):
            clusters[i] = [
                x[0] for x in ordered_list[listOfClusters[i][0] : listOfClusters[i][1]]
            ]
        return clusters

    def extract_clusters_amine(self, ordered_list, minPts, maxDistance):
        reachability = 1e6
        clusters = {}
        for index in range(len(ordered_list)):
            print(index, ordered_list[index])
            reachability_previous = reachability
            reachability = ordered_list[index][2]
            if reachability > reachability_previous:
                continue
            if index == len(ordered_list) - 1:
                reachability_next = 1e6
            else:
                reachability_next = ordered_list[index + 1][2]
            if reachability > reachability_next:
                continue
            # found a low point at index
            start = index - 1
            end = index + 2
            if start < 0:
                start += 1
                end += 1
            elif end == len(ordered_list) - 1:
                start -= 1
                end -= 1
            best_score = 0
            cluster = [x[0] for x in ordered_list[start:end]]
            score, _ = self.caller.get_score(cluster)
            while score > best_score:
                best_score = score
                best_cluster = cluster
                score_left = score_right = score_both = 0
                if start > 0:
                    cluster_left = [x[0] for x in ordered_list[start - 1 : end]]
                    score_left, _ = self.caller.get_score(cluster_left)
                if end < len(ordered_list) - 1:
                    cluster_right = [x[0] for x in ordered_list[start : end + 1]]
                    score_right, _ = self.caller.get_score(cluster_right)
                if start > 0 and end < len(ordered_list) - 1:
                    cluster_both = [x[0] for x in ordered_list[start - 1 : end + 1]]
                    score_both, _ = self.caller.get_score(cluster_both)
                if score_left > max(score, score_right, score_both):
                    score = score_left
                    cluster = cluster_left
                    start -= 1
                elif score_right > max(score, score_both):
                    score = score_right
                    cluster = cluster_right
                    end += 1
                elif score_both > score:
                    score = score_both
                    cluster = cluster_both
                    start -= 1
                    end += 1

            if best_score > 0:
                clusters[index] = best_cluster
        return clusters
