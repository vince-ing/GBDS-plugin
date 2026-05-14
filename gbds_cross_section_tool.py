import os
import glob
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QListWidget, QMessageBox, QAbstractItemView
)
from qgis.PyQt.QtCore import Qt
from qgis.gui import QgsMapTool
from qgis.core import (
    QgsSettings, QgsRectangle, QgsFeatureRequest, 
    QgsCoordinateTransform, QgsProject, QgsMapLayerType
)

class TransectSelectionDialog(QDialog):
    """Dialog shown when a map click intersects multiple transect lines."""
    def __init__(self, transects, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Multiple Transects Found")
        self.resize(300, 200)
        self.selected_transect = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Please select a transect to view:"))

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        
        self.transect_data = transects
        for t in transects:
            display_text = t.get("name") if t.get("name") else f"Transect ID: {t.get('id')}"
            self.list_widget.addItem(display_text)

        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.cancel_btn = QPushButton("Cancel")
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.ok_btn.clicked.connect(self.accept_selection)
        self.cancel_btn.clicked.connect(self.reject)
        self.list_widget.itemDoubleClicked.connect(self.accept_selection)

    def accept_selection(self):
        selected_items = self.list_widget.selectedItems()
        if selected_items:
            row = self.list_widget.row(selected_items[0])
            self.selected_transect = self.transect_data[row]
            self.accept()
        else:
            QMessageBox.warning(self, "Selection", "Please select a transect.")

class GbdsCrossSectionTool(QgsMapTool):
    """Custom Map Tool to click transects and open PDF cross sections."""
    def __init__(self, canvas, iface):
        super().__init__(canvas)
        self.canvas = canvas
        self.iface = iface
        self.setCursor(Qt.CrossCursor)

    def canvasReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        map_pt = self.toMapCoordinates(event.pos())
        
        # Buffer for line clicking (lines are thin, so give a 10-pixel tolerance)
        tolerance = self.canvas.mapUnitsPerPixel() * 10
        search_rect = QgsRectangle(
            map_pt.x() - tolerance, map_pt.y() - tolerance,
            map_pt.x() + tolerance, map_pt.y() + tolerance
        )

        transects_found = []
        seen_ids = set()
        map_crs = self.canvas.mapSettings().destinationCrs()

        for layer in self.canvas.layers():
            if layer.type() != QgsMapLayerType.VectorLayer or not layer.isVisible():
                continue
            
            # Target layers with "transect" or "section" in the name
            lname = layer.name().lower()
            if "transect" not in lname and "section" not in lname:
                continue

            # Handle CRS Transformation
            layer_rect = search_rect
            if layer.crs() != map_crs:
                try:
                    xform = QgsCoordinateTransform(map_crs, layer.crs(), QgsProject.instance())
                    layer_rect = xform.transformBoundingBox(search_rect)
                except Exception:
                    pass

            request = QgsFeatureRequest().setFilterRect(layer_rect)
            
            for feat in layer.getFeatures(request):
                if feat.hasGeometry() and feat.geometry().intersects(layer_rect):
                    
                    t_id = ""
                    t_name = ""
                    
                    # Fuzzy Field matching for Transects
                    for idx, field in enumerate(layer.fields()):
                        fname = field.name().lower()
                        falias = field.alias().lower() if field.alias() else ""
                        val = feat.attribute(idx)
                        
                        if val in (None, "", "NULL"): continue
                        
                        # Match ID
                        if not t_id and (fname in ['id', 'transect_i', 'objectid'] or 'id' in fname):
                            t_id = str(val)
                            
                        # Match Name
                        if not t_name and (fname in ['name', 'transect_n', 'file_name'] or 'name' in fname):
                            t_name = str(val)

                    if t_id and t_id not in seen_ids:
                        seen_ids.add(t_id)
                        transects_found.append({"id": t_id, "name": t_name})

        if not transects_found:
            return 

        root_path = QgsSettings().value("gbds/root_path", "")
        if not root_path or not os.path.exists(root_path):
            self.iface.messageBar().pushWarning("Setup Required", "Please click '⚙️ GBDS Connection' first.")
            return

        if len(transects_found) == 1:
            self._open_pdf(transects_found[0], root_path)
        else:
            dialog = TransectSelectionDialog(transects_found, self.iface.mainWindow())
            if dialog.exec_() == QDialog.Accepted:
                self._open_pdf(dialog.selected_transect, root_path)

    def _open_pdf(self, transect_data, root_path):
        t_id = transect_data.get("id")
        t_name = transect_data.get("name")
        
        base_dir = os.path.join(root_path, "Documentation", "Cross_Sections")
        sub_dirs = ["Seismic", "Well", ""] # Check Seismic, Well, or the root Cross_Sections folder
        
        found_pdf = None
        
        # Priority 1: Search by ID (e.g., *1001*.pdf)
        if t_id:
            for sub in sub_dirs:
                search_path = os.path.join(base_dir, sub, f"*{t_id}*.pdf")
                matches = glob.glob(search_path)
                if matches:
                    found_pdf = matches[0]
                    break
                    
        # Priority 2: Search by Name if ID failed
        if not found_pdf and t_name:
            for sub in sub_dirs:
                search_path = os.path.join(base_dir, sub, f"*{t_name}*.pdf")
                matches = glob.glob(search_path)
                if matches:
                    found_pdf = matches[0]
                    break

        if found_pdf and os.path.exists(found_pdf):
            try:
                os.startfile(found_pdf)
            except Exception as e:
                QMessageBox.critical(self.iface.mainWindow(), "Error", f"Could not open PDF:\n{e}")
        else:
            QMessageBox.information(
                self.iface.mainWindow(), 
                "Not Found", 
                f"Could not find a PDF for transect ID '{t_id}' or Name '{t_name}' in:\n{base_dir}"
            )