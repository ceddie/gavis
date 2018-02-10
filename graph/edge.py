class Edge:

    def __init__(self, graph, edge_id, from_vertex_id, to_vertex_id, color, label=None):
        self.graph = graph
        self.edge_id = edge_id
        self.from_vertex_id = from_vertex_id
        self.to_vertex_id = to_vertex_id
        self.color = color
        self.label = label

    def set_color(self, color, sync=True):
        self.color = color
        if sync:
            self.graph.sync()

    def set_label(self, label, sync=True):
        self.label = label
        if sync:
            self.graph.sync()

    def to_dict(self):
        result = {'id': self.edge_id,
                  'from': self.from_vertex_id,
                  'to': self.to_vertex_id,
                  'color': {}}
        if self.color:
            result['color']['color'] = self.color
        if self.label:
            result['label'] = self.label
        return result

    def __str__(self):
        return str(self.to_dict())
