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

class ZirconSelectionDialog(QDialog):
    """Dialog shown when a map click intersects multiple zircon samples."""
    def __init__(self, samples, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Multiple Samples Found")
        self.resize(300, 200)
        self.selected_sample = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Please select a zircon sample to view:"))

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        
        self.sample_data = samples
        for s in samples:
            display_text = s.get("name") if s.get("name") else f"Plot: {s.get('plot_file')}"
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
            self.selected_sample = self.sample_data[row]
            self.accept()
        else:
            QMessageBox.warning(self, "Selection", "Please select a sample.")

class GbdsZirconTool(QgsMapTool):
    """Custom Map Tool to click zircon samples and open plot images."""
    def __init__(self, canvas, iface):
        super().__init__(canvas)
        self.canvas = canvas
        self.iface = iface
        self.setCursor(Qt.CrossCursor)

    def activate(self):
        """Triggered automatically when the user clicks the tool on the toolbar."""
        super().activate()
        
        # Check if a zircon layer is already in the map
        has_zircon = False
        for layer in QgsProject.instance().mapLayers().values():
            if "zircon" in layer.name().lower():
                has_zircon = True
                break
                
        # If no zircon layer is found, automatically load it
        if not has_zircon:
            root_path = QgsSettings().value("gbds/root_path", "")
            if root_path and os.path.exists(root_path):
                
                # Check both Map_Layers and Map_Layers_Q
                qlr_path = os.path.join(root_path, "Map_Layers", "Regional_Geology", "Zircon Sample.qlr")
                if not os.path.exists(qlr_path):
                    qlr_path = os.path.join(root_path, "Map_Layers_Q", "Regional_Geology", "Zircon Sample.qlr")
                
                if os.path.exists(qlr_path):
                    try:
                        QgsLayerDefinition.loadLayerDefinition(
                            qlr_path, 
                            QgsProject.instance(), 
                            QgsProject.instance().layerTreeRoot()
                        )
                        self.iface.messageBar().pushInfo("GBDS", "Automatically loaded Zircon Sample layer.")
                    except Exception as e:
                        self.iface.messageBar().pushWarning("GBDS", f"Failed to load zircon layer: {e}")

    def canvasReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        map_pt = self.toMapCoordinates(event.pos())
        
        # Buffer for point clicking (10-pixel tolerance)
        tolerance = self.canvas.mapUnitsPerPixel() * 10
        search_rect = QgsRectangle(
            map_pt.x() - tolerance, map_pt.y() - tolerance,
            map_pt.x() + tolerance, map_pt.y() + tolerance
        )

        samples_found = []
        seen_plots = set()
        map_crs = self.canvas.mapSettings().destinationCrs()

        for layer in self.canvas.layers():
            if layer.type() != QgsMapLayerType.VectorLayer:
                continue
            
            # Target layers with "zircon" in the name
            if "zircon" not in layer.name().lower():
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
                    
                    s_name = ""
                    plot_file = ""
                    
                    # Fuzzy Field matching for Zircons
                    for idx, field in enumerate(layer.fields()):
                        fname = field.name().lower()
                        val = feat.attribute(idx)
                        
                        if val in (None, "", "NULL"): continue
                        val_str = str(val).strip()
                        
                        # MATCH PLOT FILE
                        if not plot_file and fname in ['plot_file', 'plot', 'file', 'image']:
                            plot_file = val_str
                            
                        # MATCH NAME or SAMPLE ID for the dialog display
                        if not s_name and fname in ['sample_id', 'sample', 'name', 'id']:
                            # Exclude typical GIS automatic IDs
                            if fname not in ['fid', 'objectid']:
                                s_name = val_str

                    if plot_file and plot_file not in seen_plots:
                        seen_plots.add(plot_file)
                        samples_found.append({"name": s_name, "plot_file": plot_file})

        if not samples_found:
            return 

        root_path = QgsSettings().value("gbds/root_path", "")
        if not root_path or not os.path.exists(root_path):
            self.iface.messageBar().pushWarning("Setup Required", "Please click '⚙️ GBDS Connection' first.")
            return

        if len(samples_found) == 1:
            self._open_plot(samples_found[0], root_path)
        else:
            dialog = ZirconSelectionDialog(samples_found, self.iface.mainWindow())
            if dialog.exec_() == QDialog.Accepted:
                self._open_plot(dialog.selected_sample, root_path)

    def _open_plot(self, sample_data, root_path):
        plot_file = sample_data.get("plot_file")
        
        # Build the path: Projects/Detrital Zircon Analysis/Plots/<Plot_File>
        base_dir = os.path.join(root_path, "Projects", "Detrital Zircon Analysis", "Plots")
        
        # Try exact match first
        target_path = os.path.join(base_dir, plot_file)
        
        # If exact match fails (e.g. extension missing in attribute), try wildcard
        if not os.path.exists(target_path):
            matches = glob.glob(os.path.join(base_dir, f"{plot_file}*"))
            if matches:
                target_path = matches[0]

        if os.path.exists(target_path):
            try:
                os.startfile(target_path)
            except Exception as e:
                QMessageBox.critical(self.iface.mainWindow(), "Error", f"Could not open Zircon Plot:\n{e}")
        else:
            QMessageBox.information(
                self.iface.mainWindow(), 
                "Not Found", 
                f"Could not find plot image '{plot_file}' in:\n{base_dir}"
            )