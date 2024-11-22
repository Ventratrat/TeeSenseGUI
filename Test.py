from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtGui import QImage, QPixmap
from csvRead import generate_plot


class Ui_MainWindow(object):

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(796, 600)
        
        # Central widget
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        
        # Main layout (horizontal layout for graphics view and text display)
        self.main_layout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        
        # Graphics view
        self.graphicsView = QtWidgets.QGraphicsView(self.centralwidget)
        self.graphicsView.setObjectName("graphicsView")
        
        # Initialize a QGraphicsScene
        self.scene = QtWidgets.QGraphicsScene()
        self.graphicsView.setScene(self.scene)
        self.main_layout.addWidget(self.graphicsView, 2)  # Give this widget more space

        # Text display (using QTextEdit for flexibility)
        self.textDisplay = QtWidgets.QTextEdit(self.centralwidget)
        self.textDisplay.setObjectName("textDisplay")
        self.textDisplay.setReadOnly(True)  # Make it read-only for display purposes
        self.main_layout.addWidget(self.textDisplay, 1)  # Give this widget less space

        MainWindow.setCentralWidget(self.centralwidget)
        
        # Menu bar, status bar, and other setups remain the same
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
        
        # Menu actions
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
        
        self.menuFile.addAction(self.actionNew)
        self.menuFile.addAction(self.actionOpen)
        self.menuFile.addAction(self.actionOpen_Recent)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionSave_As)
        self.menuFile.addAction(self.actionSave)
        self.menuEdit.addAction(self.actionUndo)
        self.menuEdit.addAction(self.actionRedo)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuEdit.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        # Connect actions to methods
        self.actionNew.triggered.connect(self.handle_new_action)
        self.actionOpen.triggered.connect(self.handle_open_action)
        self.actionSave.triggered.connect(self.save_file)

        # Placeholder to store current file path
        self.current_file_path = None
        self.is_unsaved = False  # Track unsaved changes

    def display_matplotlib_graph(self, figure):
        # Create a canvas for the figure
        canvas = FigureCanvas(figure)
    
        # Create a graphics scene to display the canvas
        scene = QtWidgets.QGraphicsScene()  # Parent should be None or MainWindow, not Ui_MainWindow.
    
        # Add the canvas as an item to the scene
        scene.addWidget(canvas)
    
        # Set the scene for the graphics view to display the canvas
        self.graphicsView.setScene(scene)
    
        # Resize the graphics view to fit the figure
        self.graphicsView.setRenderHint(QtGui.QPainter.Antialiasing)
        canvas.draw()



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
                file_path, _ = QFileDialog.getSaveFileName(None, "Save File As", "", "Images (*.png *.jpg *.bmp);;All Files (*)")
                if file_path:
                    self.current_file_path = file_path
                    self.save_file()
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
        # Clears the graphics view for a new file
        self.scene.clear()
        self.current_file_path = None
        self.is_unsaved = False
        self.display_matplotlib_graph(Figure())
        QMessageBox.information(None, "New File", "Created a new file.")

    def open_file(self):
    # Opens a file dialog to load a CSV or any file
        file_path, _ = QFileDialog.getOpenFileName(
        None,
        "Open File",
        "",
        "CSV Files (*.csv);;All Files (*)"
    )
        if file_path:
            self.current_file_path = file_path
            self.scene.clear()

        # Check if the file is a CSV file
        if file_path.endswith('.csv'):
            try:
                # Read the CSV content (optional for graph generation)
                import pandas as pd
                data = pd.read_csv(file_path)
                
                # Call a function to generate the matplotlib figure
                figure = generate_plot(file_path)
                
                # Render the graph on the scene
                self.display_matplotlib_graph(figure)
                self.is_unsaved = True
            except Exception as e:
                QMessageBox.warning(None, "Error", f"Could not load CSV file:\n{e}")
        else:
            QMessageBox.information(None, "File Opened", f"Opened: {file_path}")


    def save_file(self):
        # Saves the current content to a file
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
        # Saves the content to a new file
        file_path, _ = QFileDialog.getSaveFileName(None, "Save File As", "", "Images (*.png *.jpg *.bmp);;All Files (*)")
        if file_path:
            self.current_file_path = file_path
            self.save_file()


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
