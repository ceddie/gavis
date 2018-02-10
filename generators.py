import math
import random
import networkx as nx
from _NetworKit import PowerlawDegreeSequence, ChungLuGenerator, HyperbolicGenerator
from networkit import nxadapter


def erdos_renyi_graph(n, k, giant=True):
    graph = nx.fast_gnp_random_graph(n, k / (n - 1))
    if giant:
        graph = max(nx.connected_component_subgraphs(graph), key=len)

    for i in graph.nodes():
        graph.node[i]['pos'] = (random.random(), random.random())
    multiply_pos(graph, 5000)
    return graph


def hyperbolic_graph(n, k, giant=True):
    nk_graph = HyperbolicGenerator(n, k=k, gamma=2.5, T=0).generate()
    graph = nxadapter.nk2nx(nk_graph)
    if giant:
        graph = max(nx.connected_component_subgraphs(graph), key=len)
    for i in graph.nodes():
        graph.node[i]['pos'] = (random.random(), random.random())
    multiply_pos(graph, 5000)
    return graph


def chung_lu_graph(n, giant=True):
    powerlaw_gen = PowerlawDegreeSequence(3, 50, -2.5)
    powerlaw_gen.run()
    nk_graph = ChungLuGenerator(powerlaw_gen.getDegreeSequence(n)).generate()
    graph = nxadapter.nk2nx(nk_graph)
    if giant:
        graph = max(nx.connected_component_subgraphs(graph), key=len)
    for i in graph.nodes():
        graph.node[i]['pos'] = (random.random(), random.random())
    multiply_pos(graph, 5000)
    return graph


def geometric_graph(n, k, giant=True):
    r = math.sqrt(k / (n * math.pi))
    graph = nx.random_geometric_graph(n, r)
    if giant:
        graph = max(nx.connected_component_subgraphs(graph), key=len)
    multiply_pos(graph, 5000)
    return graph


def multiply_pos(graph, factor):
    for _, node in graph.nodes.items():
        node['pos'] = [factor * node['pos'][0], factor * node['pos'][1]]
