class Vertex:

    def __init__(self, graph, vertex_id, background_color, border_color, pos=None, label=None):
        self.graph = graph
        self.vertex_id = vertex_id
        self.background_color = background_color
        self.border_color = border_color
        self.pos = pos
        self.label = label

    def set_background_color(self, color, sync=True):
        self.background_color = color
        if sync:
            self.graph.sync()

    def set_border_color(self, color, sync=True):
        self.border_color = color
        if sync:
            self.graph.sync()

    def set_label(self, label, sync=True):
        self.label = label
        if sync:
            self.graph.sync()

    def to_dict(self):
        result = {'id': self.vertex_id, 'color': {}}
        if self.background_color:
            result['color']['background'] = self.background_color
        if self.border_color:
            result['color']['border'] = self.border_color
        if self.pos:
            result['x'] = str(self.pos[0])
            result['y'] = str(self.pos[1])
        if self.label:
            result['label'] = self.label
        return result

    def __str__(self):
        return str(self.to_dict())
