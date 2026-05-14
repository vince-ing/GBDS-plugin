import os
from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QTreeView,
    QFileSystemModel, QToolBar, QPushButton, QFileDialog
)
from qgis.PyQt.QtCore import Qt, QMimeData, QUrl
from qgis.PyQt.QtGui import QDrag
from qgis.core import QgsSettings, QgsProject, QgsLayerDefinition

# --- Subclass QTreeView to override drag behavior ---
class DraggableTreeView(QTreeView):
    def __init__(self, file_model, load_callback, parent=None):
        super().__init__(parent)
        self.file_model = file_model
        self.load_callback = load_callback  # Function to call when a .qlr is dropped
        self.setDragEnabled(True)
        self.setDragDropMode(QTreeView.DragOnly)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return super().mouseMoveEvent(event)

        index = self.indexAt(event.pos())
        if not index.isValid():
            return super().mouseMoveEvent(event)

        file_path = self.file_model.filePath(index)
        if not (os.path.isfile(file_path) and file_path.lower().endswith(".qlr")):
            return super().mouseMoveEvent(event)

        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(file_path)])
        mime.setText(file_path)

        drag = QDrag(self)
        drag.setMimeData(mime)

        drag.exec_(Qt.CopyAction)  # ← just execute the drag, don't check the result


class GBDSCatalogDock(QDockWidget):
    def __init__(self, iface, parent=None):
        super().__init__("GBDS Data", parent)
        self.iface = iface
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.toolbar = QToolBar()
        self.setup_btn = QPushButton("⚙️ GBDS Connection")
        self.setup_btn.setToolTip("Point this to your GBDS Current Database folder")
        self.setup_btn.clicked.connect(self.run_setup)
        self.toolbar.addWidget(self.setup_btn)
        self.layout.addWidget(self.toolbar)

        self.file_model = QFileSystemModel()
        self.file_model.setNameFilters(["*.qlr"])
        self.file_model.setNameFilterDisables(False)

        # Use the draggable subclass instead of plain QTreeView
        self.tree_view = DraggableTreeView(self.file_model, self.load_qlr_file)
        self.tree_view.setModel(self.file_model)

        for i in range(1, 4):
            self.tree_view.hideColumn(i)

        self.layout.addWidget(self.tree_view)
        self.setWidget(self.container)

        # Keep double-click as well so both methods work
        self.tree_view.doubleClicked.connect(self.on_file_double_clicked)

        self.update_tree_root()

    def load_qlr_file(self, file_path):
        """Shared loader used by both double-click and drag."""
        try:
            QgsLayerDefinition.loadLayerDefinition(
                file_path,
                QgsProject.instance(),
                QgsProject.instance().layerTreeRoot()
            )
            self.iface.messageBar().pushSuccess("GBDS", "Loaded map layer successfully.")
        except Exception as e:
            self.iface.messageBar().pushCritical("GBDS", f"Failed to load layer: {str(e)}")

    def run_setup(self):
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select your main GBDS folder"
        )
        if folder_path:
            QgsSettings().setValue("gbds/root_path", folder_path)
            self.update_tree_root()
            self.iface.messageBar().pushSuccess("GBDS Setup", f"Connected to: {folder_path}")

    def update_tree_root(self):
        root_path = QgsSettings().value("gbds/root_path", "")
        if root_path and os.path.exists(root_path):
            map_layers_dir = os.path.join(root_path, "Map_Layers")
            target = map_layers_dir if os.path.exists(map_layers_dir) else root_path
            self.file_model.setRootPath(target)
            self.tree_view.setRootIndex(self.file_model.index(target))
        else:
            self.file_model.setRootPath("")

    def on_file_double_clicked(self, index):
        file_path = self.file_model.filePath(index)
        if os.path.isfile(file_path) and file_path.lower().endswith(".qlr"):
            self.load_qlr_file(file_path)