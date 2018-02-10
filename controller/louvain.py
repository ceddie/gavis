# -*- coding: utf-8 -*-
"""
This module implements community detection.
"""
from __future__ import print_function
import random
from networkx import nx
import time

__author__ = """Thomas Aynaud (thomas.aynaud@lip6.fr)"""
#    Copyright (C) 2009 by
#    Thomas Aynaud <thomas.aynaud@lip6.fr>
#    All rights reserved.
#    BSD license.


def louvain(graph, k=-1, order=None, rand=True):
    start = time.time()
    status = Status.from_graph(graph)
    next_level = True
    levels = list()
    global_part = {i: i for i in graph.nodes()}
    while next_level:
        next_level, level_info = one_level(graph, status, k, order, rand)

        for v, com in global_part.items():
            global_part[v] = status.node2com[global_part[v]]
        levels.append(level_info)
        node_to_com = _renumber(status.node2com)
        renumber_dict = dict()
        for v, old_com in status.node2com.items():
            renumber_dict[old_com] = node_to_com[v]
        for v, com in global_part.items():
            global_part[v] = renumber_dict[global_part[v]]

        graph = merge(node_to_com, graph)
        status = Status.from_graph(graph)
    runtime = time.time() - start
    return {'levels': levels, 'final_modularity': _modularity(status), 'partition': global_part, 'runtime': runtime}


def one_level(graph, status, k, order, rand):
    """Compute one level of communities
    """
    improved_in_last_iteration = True
    iterations = 0
    best_neq_max_dnc_counter = 0
    moves_list = []
    moved_node_counter = dict()

    if order is None:
        nodes_order = list(graph.node.keys())
    else:
        nodes_order = order

    next_level = False
    while improved_in_last_iteration and iterations != k:
        iterations += 1

        if rand:
            random.shuffle(nodes_order)

        improved_in_last_iteration, iteration_info = one_iteration(graph, status, nodes_order, moved_node_counter)
        best_neq_max_dnc_counter += iteration_info['best_neq_max_dnc_counter']
        moves_list.append(iteration_info['moves'])
        if improved_in_last_iteration:
            next_level = True

    # TODO:
    best_neq_max_dnc_fraction = best_neq_max_dnc_counter / (iterations * len(nodes_order))

    return next_level, {'iterations': iterations, 'nodes': graph.number_of_nodes(), 'edges': graph.number_of_edges(),
                        'moves_list': moves_list, 'moved_node_counter': moved_node_counter,
                        'best_neq_max_dnc_fraction': best_neq_max_dnc_fraction}


def one_iteration(graph, status, order, moved_node_counter=False):
    improved = False
    moves = 0
    best_neq_max_dnc_counter = 0
    for node in order:
        improved_locally, local_optimization_info = optimize_locally(node, graph, status)
        best_neq_max_dnc_counter += local_optimization_info['best_neq_max_dnc_counter']
        if improved_locally:
            improved = True
            moves += 1
            if moved_node_counter:
                if node not in moved_node_counter:
                    moved_node_counter[node] = 0
                moved_node_counter[node] += 1

    return improved, {'moves': moves, 'best_neq_max_dnc_counter': best_neq_max_dnc_counter}


def optimize_locally(node, graph, status):
    old_com = status.node2com[node]
    degc_totw = status.gdegrees.get(node, 0.) / (status.total_weight * 2.)
    neigh_communities = _neighcom(node, graph, status)
    _remove(node, old_com, neigh_communities.get(old_com, 0.), status)
    best_com = old_com
    if old_com in neigh_communities:
        best_increase = neigh_communities[old_com] - status.degrees.get(old_com, 0.) * degc_totw
        best_dnc = neigh_communities[old_com]
        max_dnc = best_dnc
    else:
        best_increase = 0
        best_dnc = 0
        max_dnc = best_dnc
    coms = [[com, dnc] for com, dnc in neigh_communities.items()]
    random.shuffle(coms)
    improved_locally = False

    for a in coms:
        com, dnc = a[0], a[1]
        max_dnc = max(max_dnc, dnc)
        incr = dnc - status.degrees.get(com, 0.) * degc_totw

        # TODO: remove
        # print('2m * d(v, C): {}, d(v) * d(C): {}'.format(2. * status.total_weight * dnc,
        #                                              status.gdegrees.get(node, 0.) * status.degrees.get(com, 0.)))

        if incr > best_increase:
            best_increase = incr
            best_com = com
            best_dnc = dnc
            improved_locally = True

    # TODO: remove
    best_neq_max_dnc_counter = 0
    if best_dnc != max_dnc:
        best_neq_max_dnc_counter = 1
        # print('best_dnc: {}, max_dnc: {}'.format(best_dnc, max_dnc))

    _insert(node, best_com, neigh_communities.get(best_com, 0.), status)
    return improved_locally, {'best_neq_max_dnc_counter': best_neq_max_dnc_counter}


def merge(partition, graph, weight="weight"):
    """Produce the graph where nodes are the communities

    there is a link of weight w between communities if the sum of the weights
    of the links between their elements is w

    Parameters
    ----------
    partition : dict
       a dictionary where keys are graph nodes and  values the part the node
       belongs to
    graph : networkx.Graph
        the initial graph
    weight : str, optional
        the key in graph to use as weight. Default to 'weight'


    Returns
    -------
    g : networkx.Graph
       a networkx graph where nodes are the parts

    Examples
    --------
        n = 5
        g = nx.complete_graph(2*n)
        part = dict([])
        for node in g.nodes() :
            part[node] = node % 2
        ind = induced_graph(part, g)
        goal = nx.Graph()
        goal.add_weighted_edges_from([(0,1,n*n),(0,0,n*(n-1)/2), (1, 1, n*(n-1)/2)])  # NOQA
        nx.is_isomorphic(int, goal)
    True
    """
    ret = nx.Graph()
    ret.add_nodes_from(partition.values())

    for node1, node2, datas in graph.edges(data=True):
        edge_weight = datas.get(weight, 1)
        com1 = partition[node1]
        com2 = partition[node2]
        w_prec = ret.get_edge_data(com1, com2, {weight: 0}).get(weight, 1)
        ret.add_edge(com1, com2, **{weight: w_prec + edge_weight})

    return ret


def _renumber(dictionary):
    """Renumber the values of the dictionary from 0 to n
    """
    count = 0
    ret = dictionary.copy()
    new_values = dict([])

    for key in dictionary.keys():
        value = dictionary[key]
        new_value = new_values.get(value, -1)
        if new_value == -1:
            new_values[value] = count
            new_value = count
            count += 1
        ret[key] = new_value

    return ret


def _neighcom(node, graph, status, weight_key='weight'):
    """
    Compute the communities in the neighborhood of node in the graph given
    with the decomposition node2com
    """
    weights = {}
    for neighbor, datas in graph[node].items():
        if neighbor != node:
            edge_weight = datas.get(weight_key, 1)
            neighborcom = status.node2com[neighbor]
            weights[neighborcom] = weights.get(neighborcom, 0.) + edge_weight
    return weights


def _remove(node, com, weight, status):
    """ Remove node from community com and modify status"""
    status.degrees[com] = (status.degrees.get(com, 0.)
                           - status.gdegrees.get(node, 0.))
    status.internals[com] = float(status.internals.get(com, 0.) -
                                  weight - status.loops.get(node, 0.))
    status.node2com[node] = -1


def _insert(node, com, weight, status):
    """ Insert node into community and modify status"""
    status.node2com[node] = com
    status.degrees[com] = (status.degrees.get(com, 0.) +
                           status.gdegrees.get(node, 0.))
    status.internals[com] = float(status.internals.get(com, 0.) +
                                  weight + status.loops.get(node, 0.))


def _modularity(status):
    """
    Fast compute the modularity of the partition of the graph using
    status precomputed
    """
    links = float(status.total_weight)
    result = 0.
    for community in set(status.node2com.values()):
        in_degree = status.internals.get(community, 0.)
        degree = status.degrees.get(community, 0.)
        if links > 0:
            result += in_degree / links - ((degree / (2. * links)) ** 2)
    return result


class Status(object):
    """
    To handle several data in one struct.

    Could be replaced by named tuple, but don't want to depend on python 2.6
    """
    node2com = {}
    total_weight = 0
    internals = {}
    degrees = {}
    gdegrees = {}

    def __init__(self):
        self.node2com = dict([])
        self.total_weight = 0
        self.degrees = dict([])
        self.gdegrees = dict([])
        self.internals = dict([])
        self.loops = dict([])

    @classmethod
    def from_graph(cls, graph):
        status = cls()
        status.init(graph)
        return status

    def __str__(self):
        return ("node2com : " + str(self.node2com) + " degrees : "
                + str(self.degrees) + " internals : " + str(self.internals)
                + " total_weight : " + str(self.total_weight))

    def copy(self):
        """Perform a deep copy of status"""
        new_status = Status()
        new_status.node2com = self.node2com.copy()
        new_status.internals = self.internals.copy()
        new_status.degrees = self.degrees.copy()
        new_status.gdegrees = self.gdegrees.copy()
        new_status.total_weight = self.total_weight
        return new_status

    def init(self, graph, weight='weight', part=None):
        """Initialize the status of a graph with every node in one community"""
        count = 0
        self.node2com = dict([])
        self.total_weight = 0
        self.degrees = dict([])
        self.gdegrees = dict([])
        self.internals = dict([])
        self.total_weight = graph.size(weight=weight)
        if part is None:
            for node in graph.nodes():
                self.node2com[node] = count
                deg = float(graph.degree(node, weight=weight))
                if deg < 0:
                    error = "Bad node degree ({})".format(deg)
                    raise ValueError(error)
                self.degrees[count] = deg
                self.gdegrees[node] = deg
                edge_data = graph.get_edge_data(node, node, default={weight: 0})
                self.loops[node] = float(edge_data.get(weight, 1))
                self.internals[count] = self.loops[node]
                count += 1
        else:
            for node in graph.nodes():
                com = part[node]
                self.node2com[node] = com
                deg = float(graph.degree(node, weight=weight))
                self.degrees[com] = self.degrees.get(com, 0) + deg
                self.gdegrees[node] = deg
                inc = 0.
                for neighbor, datas in graph[node].items():
                    edge_weight = datas.get(weight, 1)
                    if edge_weight <= 0:
                        error = "Bad graph type ({})".format(type(graph))
                        raise ValueError(error)
                    if part[neighbor] == com:
                        if neighbor == node:
                            inc += float(edge_weight)
                        else:
                            inc += float(edge_weight) / 2.
                self.internals[com] = self.internals.get(com, 0) + inc
