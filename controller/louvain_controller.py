from __future__ import print_function
import random
from controller.colors import colors1
from controller.louvain import optimize_locally, Status, _renumber, merge, _neighcom
from graph.gavisgraph import GavisGraph

colors = colors1


class LouvainController:
    def __init__(self, gavis_graph, proxy):
        self.gavis_graph = gavis_graph
        self.proxy = proxy
        self.nx_graph = self.gavis_graph.nx_graph
        self.original_nx_graph = self.nx_graph.copy()
        self.status = None
        self.partition = None
        self.self_loops = None
        self.after_merge = None

    def recolor(self, node2com, sync=True):
        for vertex_id, vertex in self.gavis_graph.vertices.items():
            com = node2com[vertex_id]
            color = colors[min(com, len(colors) - 1)]
            vertex.set_background_color(color, sync=False)
        if sync:
            self.gavis_graph.sync()

    def relabel(self, sync=True):
        for vertex_id, vertex in self.gavis_graph.vertices.items():
            neigh_communities = _neighcom(vertex_id, self.nx_graph, self.status)
            if self.after_merge:
                vertex_label = str(self.status.degrees[vertex_id])
                for com, dnc in neigh_communities.items():
                    self.gavis_graph.edges[(vertex_id, com)].set_label(str(dnc), sync=False)
            else:
                vertex_label = "   "
            vertex.set_label(vertex_label, sync=False)

        for edge, vis_edge in self.gavis_graph.edges.items():
            if self.after_merge:
                if edge[0] == edge[1]:
                    edge_label = str(2 * self.status.internals[edge[0]])
                    vis_edge.set_label(edge_label, sync=False)
            else:
                edge_label = "   "
                vis_edge.set_label(edge_label, sync=False)

        if sync:
            self.gavis_graph.sync()

    def init(self):
        self.status = Status.from_graph(self.nx_graph)
        self.partition = {i: i for i in self.nx_graph.nodes()}
        self.recolor(self.status.node2com)
        self.self_loops = False

    def iteration(self):
        improved = False
        nodes_order = list(self.nx_graph.node.keys())
        random.shuffle(nodes_order)
        for node in nodes_order:
            improved_locally, local_optimization_info = optimize_locally(node, self.nx_graph, self.status)
            if improved_locally:
                improved = True
        self.recolor(_renumber(self.status.node2com), sync=False)
        self.after_merge = False
        self.relabel()
        print('Improved: {}'.format(str(improved)))

    def update_partition(self):
        for v, com in self.partition.items():
            self.partition[v] = self.status.node2com[self.partition[v]]
        node2com_renumbered = _renumber(self.status.node2com)
        renumber_dict = dict()
        for v, old_com in self.status.node2com.items():
            renumber_dict[old_com] = node2com_renumbered[v]
        for v, com in self.partition.items():
            self.partition[v] = renumber_dict[self.partition[v]]

    def merge(self):
        self.update_partition()
        self.gavis_graph.clear()
        self.nx_graph = merge(_renumber(self.status.node2com), self.nx_graph)
        self.gavis_graph = GavisGraph.from_nx_graph(self.nx_graph, self.proxy)
        self.proxy.reset_nx_graph(self.nx_graph)
        self.proxy.reset_gavis_graph(self.gavis_graph)
        js = 'options.nodes.fixed = false;\n' \
             'graph.setOptions(options);'
        self.proxy.run_java_script(js)
        self.status = Status.from_graph(self.nx_graph)
        self.recolor(self.status.node2com, sync=False)
        self.after_merge = True
        self.self_loops = True
        self.relabel()

    def display_original_graph(self):
        self.gavis_graph.clear()
        self.nx_graph = self.original_nx_graph
        self.gavis_graph = GavisGraph.from_nx_graph(self.nx_graph, self.proxy)
        self.proxy.reset_nx_graph(self.nx_graph)
        self.proxy.reset_gavis_graph(self.gavis_graph)
        js = 'options.nodes.fixed = true;\n' \
             'graph.setOptions(options);'
        self.proxy.run_java_script(js)
        self.recolor(self.partition)

    def set_physics(self, enabled):
        if enabled:
            string = 'true'
        else:
            string = 'false'
        js = 'options.physics.enabled = ' + string + ';\n' \
             'graph.setOptions(options);'
        self.proxy.run_java_script(js)

    def fix_vertices(self, enabled):
        if enabled:
            string = 'true'
        else:
            string = 'false'
        js = 'options.nodes.fixed = ' + string + ';\n' \
             'graph.setOptions(options);'
        self.proxy.run_java_script(js)

    # see http://visjs.org/docs/network/
    @staticmethod
    def get_visjs_options():
        return {
            'physics': {
                'enabled': 'true',
            },
            'nodes': {
                'size': 10,
                'fixed': 'true',
                'color': {'background': '\'#FF0000\'',
                          'border': '\'#000000\''}
            },
            'edges': {
                'width': 2,
                'color': {'color': '\'#A4A4A4\''}
            }
        }

    def get_button_callbacks(self):
        return [('init', self.init),
                ('iteration', self.iteration),
                ('merge', self.merge),
                ('display original graph', self.display_original_graph)]
