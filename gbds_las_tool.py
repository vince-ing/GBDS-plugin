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
    QgsCoordinateTransform, QgsProject, QgsMapLayerType,
    QgsLayerDefinition
)

class LasSelectionDialog(QDialog):
    """Dialog shown when a map click intersects multiple LAS wells."""
    def __init__(self, wells, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Multiple Wells Found")
        self.resize(300, 200)
        self.selected_well = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Please select a well to view its LAS file:"))

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        
        self.well_data = wells
        for w in wells:
            display_text = f"Well ID: {w.get('id')} "
            if w.get('api'):
                display_text += f"(API: {w.get('api')})"
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
            self.selected_well = self.well_data[row]
            self.accept()
        else:
            QMessageBox.warning(self, "Selection", "Please select a well.")

class GbdsLasTool(QgsMapTool):
    """Custom Map Tool to click wells and open LAS files in an external viewer."""
    def __init__(self, canvas, iface):
        super().__init__(canvas)
        self.canvas = canvas
        self.iface = iface
        self.setCursor(Qt.CrossCursor)

    def activate(self):
        """Triggered automatically when the user clicks the tool on the toolbar."""
        super().activate()
        
        # Check if an LAS or generic well layer is already in the map
        has_layer = False
        for layer in QgsProject.instance().mapLayers().values():
            lname = layer.name().lower()
            if "las" in lname or "well" in lname:
                has_layer = True
                break
                
        # If no well layer is found, automatically load the LAS Well layer
        if not has_layer:
            root_path = QgsSettings().value("gbds/root_path", "")
            if root_path and os.path.exists(root_path):
                # Try to find LAS Well.qlr or default to GBDS Well.qlr
                qlr_paths = [
                    os.path.join(root_path, "Map_Layers", "Wells_and_Transects", "LAS Well.qlr"),
                    os.path.join(root_path, "Map_Layers", "Wells_and_Transects", "GBDS Well.qlr")
                ]
                
                for qlr_path in qlr_paths:
                    if os.path.exists(qlr_path):
                        try:
                            QgsLayerDefinition.loadLayerDefinition(
                                qlr_path, 
                                QgsProject.instance(), 
                                QgsProject.instance().layerTreeRoot()
                            )
                            self.iface.messageBar().pushInfo("GBDS", f"Automatically loaded Well layer.")
                            break
                        except Exception as e:
                            self.iface.messageBar().pushWarning("GBDS", f"Failed to load layer: {e}")

    def canvasReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        map_pt = self.toMapCoordinates(event.pos())
        tolerance = self.canvas.mapUnitsPerPixel() * 5
        search_rect = QgsRectangle(
            map_pt.x() - tolerance, map_pt.y() - tolerance,
            map_pt.x() + tolerance, map_pt.y() + tolerance
        )

        wells_found = []
        seen_ids = set()
        map_crs = self.canvas.mapSettings().destinationCrs()

        for layer in self.canvas.layers():
            if layer.type() != QgsMapLayerType.VectorLayer:
                continue
            
            # Target well layers
            if "well" not in layer.name().lower() and "las" not in layer.name().lower():
                continue

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
                    
                    gbds_id = ""
                    api = ""
                    
                    for idx, field in enumerate(layer.fields()):
                        fname = field.name().lower()
                        falias = field.alias().lower() if field.alias() else ""
                        val = feat.attribute(idx)
                        
                        if val in (None, "", "NULL"): continue
                        val_str = str(val).strip()
                        
                        # MATCH ID
                        if not gbds_id and (fname in ['gbds_wel', 'gbds_id', 'gbdsid'] or 'gbds' in fname):
                            gbds_id = val_str
                            
                        # MATCH API
                        if not api and fname == 'api':
                            api = val_str

                    if gbds_id and gbds_id not in seen_ids:
                        seen_ids.add(gbds_id)
                        wells_found.append({"id": gbds_id, "api": api})

        if not wells_found:
            return 

        root_path = QgsSettings().value("gbds/root_path", "")
        if not root_path or not os.path.exists(root_path):
            self.iface.messageBar().pushWarning("Setup Required", "Please click '⚙️ GBDS Connection' first.")
            return

        if len(wells_found) == 1:
            self._open_las(wells_found[0], root_path)
        else:
            dialog = LasSelectionDialog(wells_found, self.iface.mainWindow())
            if dialog.exec_() == QDialog.Accepted:
                self._open_las(dialog.selected_well, root_path)

    def _open_las(self, well_data, root_path):
        w_id = well_data.get("id")
        api = well_data.get("api")
        
        base_dir = os.path.join(root_path, "Documentation", "WellInfo", "LAS")
        
        found_las = None
        
        # Per manual: "LAS files begin with a 12-digit API number, followed by an underscore, followed by the GBDS well number."
        # e.g., 00000__05419_1001.las
        if w_id:
            # Search broadly for the GBDS ID inside the filename ending in .las or .LAS
            search_pattern = os.path.join(base_dir, f"*{w_id}*.las")
            matches = glob.glob(search_pattern) + glob.glob(search_pattern.upper())
            
            if matches:
                found_las = matches[0]

        if found_las and os.path.exists(found_las):
            try:
                os.startfile(found_las)
            except Exception as e:
                QMessageBox.critical(self.iface.mainWindow(), "Error", f"Could not launch LAS Viewer:\n{e}")
        else:
            QMessageBox.information(
                self.iface.mainWindow(), 
                "Not Found", 
                f"Could not find an LAS file for Well ID '{w_id}' in:\n{base_dir}"
            )