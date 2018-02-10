from networkx import empty_graph
from graph.edge import Edge
from graph.vertex import Vertex


class GavisGraph:

    def __init__(self, proxy):
        self._nx_graph = empty_graph()
        self.proxy = proxy
        self.edge_map = {}
        self.edge_id = 0

    @classmethod
    def from_nx_graph(cls, nx_graph, proxy):
        graph = cls(proxy)
        for node_id, node in nx_graph.nodes().items():
            if 'pos' in node:
                graph.add_vertex(node_id, pos=node['pos'], sync=False)
            else:
                graph.add_vertex(node_id, sync=False)
        for (a, b) in nx_graph.edges():
            graph.add_edge(a, b, sync=False)
        return graph

    @property
    def nx_graph(self):
        return self._nx_graph

    @property
    def vertices(self):
        result = dict()
        for vertex_id, vertex in self._nx_graph.nodes().items():
            result[vertex_id] = vertex['viz']
        return result

    def neighbors(self, vertex):
        return {vertex_id: self.vertices()[vertex_id] for vertex_id in self._nx_graph.neighbors(vertex.vertex_id)}

    @property
    def edges(self):
        result = dict()
        for edge, viz_edge in self._nx_graph.edges.items():
            (a, b) = edge
            result[(a, b)] = viz_edge['viz']
            result[(b, a)] = viz_edge['viz']
        return result

    def add_vertex(self, vertex_id, background_color=None, border_color=None, pos=None, sync=True):
        new_vertex = Vertex(self, vertex_id, background_color, border_color, pos=pos, label=None)
        self._nx_graph.add_node(vertex_id, pos=pos, viz=new_vertex)
        if sync:
            self.sync()

    def add_edge(self, from_vertex_id, to_vertex_id, color=None, sync=True):
        if (from_vertex_id, to_vertex_id) not in self.edge_map:
            self.edge_map[(from_vertex_id, to_vertex_id)] = self.edge_id
            self.edge_map[(to_vertex_id, from_vertex_id)] = self.edge_id
            self.edge_id += 1

        new_edge = Edge(self, self.edge_map[(from_vertex_id, to_vertex_id)], from_vertex_id, to_vertex_id,
                        color, label=None)
        self._nx_graph.add_edge(from_vertex_id, to_vertex_id, viz=new_edge)
        if sync:
            self.sync()

    def sync(self):
        self.proxy.update_graph(self.vertices, self.edges)

    def clear(self):
        self.proxy.clear_graph()
