import os
from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QTreeView, 
    QFileSystemModel, QToolBar, QPushButton, QFileDialog
)
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsSettings, QgsProject, QgsLayerDefinition

class GBDSCatalogDock(QDockWidget):
    def __init__(self, iface, parent=None):
        super().__init__("GBDS Data", parent)
        self.iface = iface
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # Main container for the sidebar
        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar at the top of the sidebar for the Setup button
        self.toolbar = QToolBar()
        self.setup_btn = QPushButton("⚙️ GBDS Connection")
        self.setup_btn.setToolTip("Point this to your main GBDS folder")
        self.setup_btn.clicked.connect(self.run_setup)
        self.toolbar.addWidget(self.setup_btn)
        self.layout.addWidget(self.toolbar)

        # File System Model (The engine for the expandable tree)
        self.file_model = QFileSystemModel()
        self.file_model.setNameFilters(["*.qlr"]) # Only show converted QGIS layers
        self.file_model.setNameFilterDisables(False) # Completely hide other files
        
        # Tree View (The visual UI for the file model)
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_model)
        
        # Hide standard file columns (Size, Type, Date) to make it look like a clean Catalog pane
        for i in range(1, 4):
            self.tree_view.hideColumn(i)
            
        self.layout.addWidget(self.tree_view)
        self.setWidget(self.container)

        # Connect double-click to load the layer
        self.tree_view.doubleClicked.connect(self.on_file_double_clicked)
        
        # Initialize the view path if they have set it before
        self.update_tree_root()

    def run_setup(self):
        """Mimics the ArcGIS 'Setup' workflow."""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select your main GBDS folder"
        )
        if folder_path:
            # Save permanently in QGIS settings
            QgsSettings().setValue("gbds/root_path", folder_path)
            self.update_tree_root()
            self.iface.messageBar().pushSuccess("GBDS Setup", f"Connected to: {folder_path}")

    def update_tree_root(self):
        """Points the sidebar specifically to the Map_Layers folder."""
        root_path = QgsSettings().value("gbds/root_path", "")
        if root_path and os.path.exists(root_path):
            map_layers_dir = os.path.join(root_path, "Map_Layers")
            if os.path.exists(map_layers_dir):
                # Lock the tree view to the Map_Layers folder
                self.file_model.setRootPath(map_layers_dir)
                self.tree_view.setRootIndex(self.file_model.index(map_layers_dir))
            else:
                self.file_model.setRootPath(root_path)
                self.tree_view.setRootIndex(self.file_model.index(root_path))
        else:
            # Empty fallback if not set up yet
            self.file_model.setRootPath("")

    def on_file_double_clicked(self, index):
        """Loads the .qlr file into the map with all symbology intact."""
        file_path = self.file_model.filePath(index)
        if os.path.isfile(file_path) and file_path.lower().endswith(".qlr"):
            try:
                QgsLayerDefinition.loadLayerDefinition(
                    file_path, 
                    QgsProject.instance(), 
                    QgsProject.instance().layerTreeRoot()
                )
                self.iface.messageBar().pushSuccess("GBDS", f"Loaded map layer successfully.")
            except Exception as e:
                self.iface.messageBar().pushCritical("GBDS", f"Failed to load layer: {str(e)}")