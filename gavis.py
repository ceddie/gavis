#!/usr/bin/env python3

import sys
import os
import simplejson
from PyQt5 import QtCore, uic, QtWidgets
from PyQt5.QtCore import QObject
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QComboBox, QTabWidget, QLabel, QPlainTextEdit, QPushButton, QFileDialog, QDialog, \
    QDialogButtonBox, QVBoxLayout
from controller.louvain_controller import LouvainController
from generators import hyperbolic_graph, chung_lu_graph, erdos_renyi_graph, geometric_graph
from graph.gavisgraph import GavisGraph
from vis import graph_js_generator
import networkx as nx
import json

qtCreatorFile = "gavis.ui"

Ui_MainWindow, QtBaseClass = uic.loadUiType(qtCreatorFile)


def dict_to_js_list(data_dict):
    js_list = '['
    for data in data_dict.values():
        js_list += str(data) + ', '
    js_list = js_list + ']'
    return js_list


def dict_to_js(data_dict):
    js = '{'
    for key, value in data_dict.items():
        js += key + ': '
        if type(value) is dict:
            js += dict_to_js(value)
        else:
            js += str(value)
        js += ', '
    js += '}'
    return js


def write_to_file(_l, _name):
    _file = open(_name, 'w')
    simplejson.dump(_l, _file)
    _file.close()


def read_from_file(_name):
    _file = open(_name, 'r')
    result = simplejson.load(_file)
    _file.close()
    return result


k = 6
n = 200


class GeneratorDialog(QDialog):
    def __init__(self, parent=None):
        super(GeneratorDialog, self).__init__(parent)
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setOrientation(QtCore.Qt.Vertical)

        self.button1 = QPushButton(self)
        self.button1.setText("hyperbolic")
        self.button1.clicked.connect(self.hyperbolic)
        self.button2 = QPushButton(self)
        self.button2.setText("Chung-Lu")
        self.button2.clicked.connect(self.chung_lu)
        self.button3 = QPushButton(self)
        self.button3.setText("Erdos-Renyi")
        self.button3.clicked.connect(self.erdos_renyi)
        self.button4 = QPushButton(self)
        self.button4.setText("geometric")
        self.button4.clicked.connect(self.geometric)

        self.buttonBox.addButton(self.button1, QDialogButtonBox.ActionRole)
        self.buttonBox.addButton(self.button2, QDialogButtonBox.ActionRole)
        self.buttonBox.addButton(self.button3, QDialogButtonBox.ActionRole)
        self.buttonBox.addButton(self.button4, QDialogButtonBox.ActionRole)
        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.addWidget(self.buttonBox)

    def hyperbolic(self):
        self.parent().nx_graph = hyperbolic_graph(n, k)
        self.close()

    def chung_lu(self):
        self.parent().nx_graph = chung_lu_graph(n)
        self.close()

    def erdos_renyi(self):
        self.parent().nx_graph = erdos_renyi_graph(n, k)
        self.close()

    def geometric(self):
        self.parent().nx_graph = geometric_graph(n, k)
        self.close()


class Proxy(QObject):
    def __init__(self, main_window):
        QObject.__init__(self)
        self.main_window = main_window
        self.select_callbacks = []
        self.dragend_callbacks = []

    def add_select_callback(self, callback):
        self.select_callbacks.append(callback)

    def add_dragend_callback(self, callback):
        self.dragend_callbacks.append(callback)

    def update_graph(self, vertices, edges):
        vertices = dict_to_js_list(vertices)
        edges = dict_to_js_list(edges)
        js = 'nodes.update({});\n'.format(vertices)
        js += 'edges.update({});\n'.format(edges)
        self.main_window.run_java_script(js)

    def clear_graph(self):
        js = 'nodes.clear();\n'
        js += 'edges.clear();\n'
        self.main_window.run_java_script(js)

    def reset_nx_graph(self, nx_graph):
        self.main_window.nx_graph = nx_graph

    def reset_gavis_graph(self, gavis_graph):
        self.main_window.gavis_graph = gavis_graph

    def run_java_script(self, js):
        self.main_window.run_java_script(js)

    @QtCore.pyqtSlot()
    def loaded_visjs(self):
        self.main_window.gavis_graph.sync()

    @QtCore.pyqtSlot(QtCore.QJsonValue)
    def select_callback(self, params):
        for callback in self.select_callbacks:
            callback(params.toObject())

    @QtCore.pyqtSlot(QtCore.QJsonValue)
    def dragend_callback(self, params):
        for callback in self.dragend_callbacks:
            callback(params.toObject())

    def get_vertex_positions(self, nodes_id_list):
        js = 'graph.getPositions({});'.format(nodes_id_list)

        def get_vertex_positions_callback(pos_dict):
            print(pos_dict)

        return self.main_window.run_java_script(js, get_vertex_positions_callback)


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)

        self.controllers = dict()
        self.controller = None

        self.tab_widget = self.findChild(QTabWidget, "tabs")
        self.tab_widget.setTabEnabled(1, False)

        self.web_engine_view = self.findChild(QWebEngineView, "webEngineView")
        self.channel = QWebChannel(self.web_engine_view.page())
        self.web_engine_view.page().setWebChannel(self.channel)

        self.proxy = Proxy(self)

        self.channel.registerObject("main_window_proxy", self.proxy)

        self.combo_box = self.findChild(QComboBox, "comboBox")

        self.nx_graph = None
        self.gavis_graph = None

        self.findChild(QPushButton, "load_graph_button").clicked.connect(self.load_graph_button_clicked)
        self.findChild(QPushButton, "empty_graph_button").clicked.connect(self.empty_graph_button_clicked)
        self.findChild(QPushButton, "graph_generator_button").clicked.connect(self.graph_generator_button_clicked)
        self.findChild(QPushButton, "controller_button").clicked.connect(self.controller_button_clicked)
        self.findChild(QPushButton, "save_graph_button").clicked.connect(self.save_graph_button_clicked)

    def add_controller(self, controller_class):
        self.controllers[controller_class.__name__] = controller_class

    def init(self):
        for controller_cls_name in self.controllers:
            self.combo_box.addItem(controller_cls_name)
        self.changed_selected_controller()
        self.combo_box.currentIndexChanged.connect(self.changed_selected_controller)

    def changed_selected_controller(self):
        controller_cls_name = self.combo_box.currentText()
        options_dict = self.controllers[controller_cls_name].get_visjs_options()
        options_string = json.dumps(options_dict, indent=4)
        self.findChild(QPlainTextEdit, "options_text_edit").setPlainText(options_string)

    def controller_button_clicked(self):
        options = str(self.findChild(QPlainTextEdit, "options_text_edit").toPlainText())
        self.init_graph_view(options)
        controller_cls_name = self.combo_box.currentText()
        self.gavis_graph = GavisGraph.from_nx_graph(self.nx_graph, self.proxy)
        self.info_display = self.findChild(QVBoxLayout, "info_display")
        self.controller = self.controllers[controller_cls_name](self.gavis_graph, self.proxy, self.info_display)
        self.set_button_callbacks(self.controller.get_button_callbacks())
        self.tab_widget.setTabEnabled(1, True)
        self.findChild(QLabel, "controller_label").setText(controller_cls_name + ':')

    def init_graph_view(self, options):
        options_dict = eval(options)
        graph_js = graph_js_generator.generate(dict_to_js(options_dict))
        with open('vis/graph.js', 'w') as f:
            f.write(graph_js)
        local_url = QtCore.QUrl.fromLocalFile(os.getcwd() + '/vis/index.html')
        self.web_engine_view.load(local_url)

    def load_graph_button_clicked(self):
        file_names = QFileDialog.getOpenFileName()
        self.nx_graph = nx.node_link_graph(read_from_file(file_names[0]))

    def empty_graph_button_clicked(self):
        self.nx_graph = nx.empty_graph()

    def graph_generator_button_clicked(self):
        GeneratorDialog(self).exec_()

    def save_graph_button_clicked(self):
        file_names = QFileDialog.getSaveFileName()
        write_to_file(nx.node_link_data(self.nx_graph), file_names[0])

    def run_java_script(self, js, callback=lambda *a, **k: None):
        self.web_engine_view.page().runJavaScript(js, callback)

    def set_button_callbacks(self, button_callbacks):
        if len(button_callbacks) > 8:
            raise AssertionError('Not enough buttons!')
        for i in range(len(button_callbacks)):
            self.findChild(QPushButton, "pushButton_{}".format(i + 1)).setText(button_callbacks[i][0])
            self.findChild(QPushButton, "pushButton_{}".format(i + 1)).clicked.connect(button_callbacks[i][1])


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()

    # add controllers here
    main_window.add_controller(LouvainController)

    main_window.init()
    main_window.show()
    sys.exit(app.exec_())
