from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtGui import QImage, QPixmap
from csvRead import generate_plot
import pandas as pd
import json
import os

class Ui_MainWindow(object):

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(796, 600)
        
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        
        self.main_layout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.graphicsView = QtWidgets.QGraphicsView(self.centralwidget)
        self.graphicsView.setObjectName("graphicsView")
        
        self.scene = QtWidgets.QGraphicsScene()
        self.graphicsView.setScene(self.scene)
        self.main_layout.addWidget(self.graphicsView, 2)

        self.textDisplay = QtWidgets.QTextEdit(self.centralwidget)
        self.textDisplay.setObjectName("textDisplay")
        self.textDisplay.setReadOnly(True)
        self.main_layout.addWidget(self.textDisplay, 1)

        MainWindow.setCentralWidget(self.centralwidget)
        
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 796, 21))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuEdit = QtWidgets.QMenu(self.menubar)
        self.menuEdit.setObjectName("menuEdit")
        MainWindow.setMenuBar(self.menubar)
        
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        
        self.actionNew = QtWidgets.QAction(MainWindow)
        self.actionNew.setObjectName("actionNew")
        self.actionOpen = QtWidgets.QAction(MainWindow)
        self.actionOpen.setObjectName("actionOpen")
        self.actionSave_As = QtWidgets.QAction(MainWindow)
        self.actionSave_As.setObjectName("actionSave_As")
        self.actionSave = QtWidgets.QAction(MainWindow)
        self.actionSave.setObjectName("actionSave")
        self.actionOpen_Recent = QtWidgets.QAction(MainWindow)
        self.actionOpen_Recent.setObjectName("actionOpen_Recent")
        self.actionUndo = QtWidgets.QAction(MainWindow)
        self.actionUndo.setObjectName("actionUndo")
        self.actionRedo = QtWidgets.QAction(MainWindow)
        self.actionRedo.setObjectName("actionRedo")
        self.actionExport = QtWidgets.QAction(MainWindow)
        self.actionExport.setObjectName("actionExport")

        self.menuFile.addAction(self.actionNew)
        self.menuFile.addAction(self.actionOpen)
        self.menuFile.addAction(self.actionOpen_Recent)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionSave_As)
        self.menuFile.addAction(self.actionSave)
        self.menuFile.addAction(self.actionExport)
        self.menuEdit.addAction(self.actionUndo)
        self.menuEdit.addAction(self.actionRedo)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuEdit.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        self.actionNew.triggered.connect(self.handle_new_action)
        self.actionOpen.triggered.connect(self.handle_open_action)
        self.actionSave.triggered.connect(self.save_file)
        self.actionExport.triggered.connect(self.export_workspace)

        self.current_file_path = None
        self.is_unsaved = False

    def display_matplotlib_graph(self, figure):
        canvas = FigureCanvas(figure)
        scene = QtWidgets.QGraphicsScene()
        scene.addWidget(canvas)
        self.graphicsView.setScene(scene)
        self.graphicsView.setRenderHint(QtGui.QPainter.Antialiasing)
        canvas.draw()
        
    def open_excel_file(self, file_path):
        if file_path.endswith('.csv'):
            try:
                data = pd.read_csv(file_path)
                figure = generate_plot(file_path)
                self.display_matplotlib_graph(figure)
                self.is_unsaved = True
            except Exception as e:
                QMessageBox.warning(None, "Error", f"Could not load CSV file:\n{e}")
        else:
            QMessageBox.information(None, "File Opened", f"Opened: {file_path}")
            
    def open_json_file(self, file_path):
        try:
            with open(file_path, "r") as json_file:
                workspace_data = json.load(json_file)

            image_file = workspace_data.get("graph_image_path")
            if image_file and os.path.exists(image_file):
                pixmap = QPixmap(image_file)
                self.scene.addPixmap(pixmap)
            else:
                QMessageBox.warning(None, "Error", f"Graph image not found: {image_file}")

            self.textDisplay.setPlainText(workspace_data.get("text_content", ""))
            self.is_unsaved = False
            QMessageBox.information(None, "File Opened", f"Workspace opened: {file_path}")

        except Exception as e:
            QMessageBox.warning(None, "Error", f"Could not load workspace:\n{e}")
            
    def save_workspace(self, file_path):
        workspace_data = {
            "current_file_path": self.current_file_path,
            "is_unsaved": self.is_unsaved,
            "scene_items": self.get_scene_items(),
            "text_display": self.textDisplay.toPlainText(),
        }

        try:
            with open(file_path, 'w') as json_file:
                json.dump(workspace_data, json_file, indent=4)
            QMessageBox.information(None, "Save Successful", "Workspace saved successfully.")
        except Exception as e:
            QMessageBox.warning(None, "Save Failed", f"Could not save workspace:\n{e}")

    def get_scene_items(self):
        items_data = []
        for item in self.scene.items():
            if isinstance(item, QtWidgets.QGraphicsItem):
                items_data.append({
                    "type": type(item).__name__,
                    "position": {"x": item.pos().x(), "y": item.pos().y()},
                })
        return items_data

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "TeeSense Current Pulse Display"))
        self.menuFile.setTitle(_translate("MainWindow", "&File"))
        self.menuEdit.setTitle(_translate("MainWindow", "&Edit"))
        self.actionNew.setText(_translate("MainWindow", "New"))
        self.actionNew.setShortcut(_translate("MainWindow", "Ctrl+N"))
        self.actionOpen.setText(_translate("MainWindow", "Open"))
        self.actionOpen.setShortcut(_translate("MainWindow", "Ctrl+O"))
        self.actionSave_As.setText(_translate("MainWindow", "Save As"))
        self.actionSave_As.setShortcut(_translate("MainWindow", "Ctrl+Shift+S"))
        self.actionSave.setText(_translate("MainWindow", "Save"))
        self.actionSave.setShortcut(_translate("MainWindow", "Ctrl+S"))
        self.actionOpen_Recent.setText(_translate("MainWindow", "Open Recent"))
        self.actionUndo.setText(_translate("MainWindow", "Undo"))
        self.actionUndo.setShortcut(_translate("MainWindow", "Ctrl+Z"))
        self.actionRedo.setText(_translate("MainWindow", "Redo"))
        self.actionRedo.setShortcut(_translate("MainWindow", "Ctrl+Y"))
        self.actionExport.setText(_translate("MainWindow", "Export"))

    def prompt_save_changes(self):
        if self.is_unsaved:
            response = QMessageBox.question(
                None, 
                "Unsaved Changes",
                "You have unsaved changes. Do you want to save them?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )
            if response == QMessageBox.Save:
                file_path, _ = QFileDialog.getSaveFileName(None, "Save As", "", "JSON Files (*.json);;All Files (*)")
                if file_path:
                    if not file_path.endswith('.json'):
                        file_path += '.json'
                    self.current_file_path = file_path
                    self.save_workspace(file_path)
                    return True
            elif response == QMessageBox.Discard:
                self.scene.clear()
                self.current_file_path = None
                self.is_unsaved = False
                return True
            else:
                return False
        return True

    def handle_new_action(self):
        if self.prompt_save_changes():
            self.new_file()

    def handle_open_action(self):
        if self.prompt_save_changes():
            self.open_file()

    def new_file(self):
        self.scene.clear()
        self.current_file_path = None
        self.is_unsaved = False
        self.display_matplotlib_graph(Figure())
        QMessageBox.information(None, "New File", "Created a new file.")

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Open File",
            "",
            "Supported Files (*.json *.csv *.xlsx);;All Files (*)"
        )
        if file_path:
            self.current_file_path = file_path
            self.scene.clear()

            if file_path.endswith('.json'):
                self.open_json_file(file_path)
            elif file_path.endswith('.csv') or file_path.endswith('.xlsx'):
                self.open_excel_file(file_path)
            else:
                QMessageBox.warning(None, "Error", "Unsupported file type.")

    def save_file(self):
        if self.current_file_path:
            pixmap = QtGui.QPixmap(self.graphicsView.viewport().size())
            painter = QtGui.QPainter(pixmap)
            self.scene.render(painter)
            painter.end()
            pixmap.save(self.current_file_path)
            self.is_unsaved = False
            QMessageBox.information(None, "Save File", "File saved successfully.")
        else:
            self.save_as_file()

    def save_as_file(self):
        file_path, _ = QFileDialog.getSaveFileName(None, "Save Workspace As", "", "JSON Files (*.json);;All Files (*)")
        if file_path:
            if not file_path.endswith('.json'):
                file_path += '.json'
            self.current_file_path = file_path
            self.save_workspace(file_path)

    def export_workspace(self):
        file_path, _ = QFileDialog.getSaveFileName(None, "Export", "", "PNG Files (*.png);;All Files (*)")
        if file_path:
            # Create a QPixmap with the size of the QGraphicsView
            pixmap = QPixmap(self.graphicsView.viewport().size())
            
            # Use a QPainter to render the scene onto the pixmap
            painter = QtGui.QPainter(pixmap)
            self.graphicsView.render(painter)
            painter.end()
            
            # Save the pixmap to the selected file
            pixmap.save(file_path)
            QMessageBox.information(None, "Export Successful", "Workspace exported as PNG.")


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
