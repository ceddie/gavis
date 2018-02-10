def generate(options):
    graph_js = '''var nodes, edges, graph, options;
    
    function start() {
    
        var container = document.getElementById('graph');
        nodes = new vis.DataSet()
        edges = new vis.DataSet()
        
        var data = {
            nodes: nodes,
            edges: edges
        };
    
        options = ''' + options + '''
        
        graph = new vis.Network(container, data, options);
        
        new QWebChannel(qt.webChannelTransport, function (channel) {
            channel.objects.main_window_proxy.loaded_visjs();
            
            graph.on("select", function (params) {
                channel.objects.main_window_proxy.select_callback(params);
            });

            graph.on("dragEnd", function (params) {
                channel.objects.main_window_proxy.dragend_callback(params);
            });
        });
    }'''

    return graph_js
