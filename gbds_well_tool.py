import os
import json
import glob
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, 
    QLabel, QLineEdit, QTextEdit, QPushButton, QComboBox, 
    QTabWidget, QWidget, QTableWidget, QTableWidgetItem, 
    QAbstractItemView, QMessageBox, QHeaderView
)
from qgis.PyQt.QtCore import Qt
from qgis.gui import QgsMapTool
from qgis.core import (
    QgsSettings, QgsRectangle, QgsFeatureRequest, 
    QgsCoordinateTransform, QgsProject
)

class WellSelectionDialog(QDialog):
    """Dialog shown when a map click intersects multiple wells."""
    def __init__(self, wells, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Multiple Features Found")
        self.resize(500, 200)
        self.selected_gbds_id = None

        layout = QVBoxLayout(self)
        
        lbl = QLabel("Multiple wells were found at this location.\nPlease choose one of the wells below.")
        layout.addWidget(lbl)

        self.table = QTableWidget(len(wells), 3)
        self.table.setHorizontalHeaderLabels(["GBDS_ID", "API", "Lease"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        for row, well in enumerate(wells):
            self.table.setItem(row, 0, QTableWidgetItem(well.get("id", "")))
            self.table.setItem(row, 1, QTableWidgetItem(well.get("api", "")))
            self.table.setItem(row, 2, QTableWidgetItem(well.get("lease", "")))

        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.cancel_btn = QPushButton("Cancel")
        btn_layout.addStretch()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.ok_btn.clicked.connect(self.accept_selection)
        self.cancel_btn.clicked.connect(self.reject)
        self.table.itemDoubleClicked.connect(self.accept_selection)

    def accept_selection(self):
        selected_items = self.table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            self.selected_gbds_id = self.table.item(row, 0).text()
            self.accept()
        else:
            QMessageBox.warning(self, "Selection", "Please select a well.")


class WellInfoDialog(QDialog):
    """Main dialog displaying well JSON data."""
    def __init__(self, gbds_id, root_path, parent=None):
        super().__init__(parent)
        self.gbds_id = str(gbds_id)
        self.root_path = root_path
        self.well_data = {}
        
        self.resize(700, 500)
        
        # Load the JSON cache
        self.load_json_data()
        
        # Build Title dynamically
        api = self.well_data.get('API', '')
        lease = self.well_data.get('Lease', '')
        title_parts = [f"GBDS Well {self.gbds_id}"]
        if api: title_parts.append(api)
        if lease: title_parts.append(lease)
        self.setWindowTitle(" - ".join(title_parts))
        
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        self.setup_header_tab()
        self.setup_units_tab()

    def load_json_data(self):
        # Maps precisely to G:\...\Current_Database\GBDSTools\Resources\WellQueryCache\1001.json
        json_path = os.path.join(self.root_path, "GBDSTools", "Resources", "WellQueryCache", f"{self.gbds_id}.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.well_data = json.load(f)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to parse well JSON:\n{e}")
        else:
            QMessageBox.warning(self, "Not Found", f"Cache file for well {self.gbds_id} not found at:\n{json_path}")

    def create_readonly_line_edit(self, text):
        le = QLineEdit(str(text))
        le.setReadOnly(True)
        return le

    def setup_header_tab(self):
        tab = QWidget()
        main_hlayout = QHBoxLayout(tab)
        
        # Left Column
        left_vlayout = QVBoxLayout()
        id_group = QGroupBox("Identity")
        id_form = QFormLayout(id_group)
        id_form.addRow("GBDS", self.create_readonly_line_edit(self.well_data.get("GbdsId", self.gbds_id)))
        id_form.addRow("API", self.create_readonly_line_edit(self.well_data.get("API", "")))
        id_form.addRow("OCS", self.create_readonly_line_edit(self.well_data.get("OcsNumber", "")))
        id_form.addRow("Name", self.create_readonly_line_edit(self.well_data.get("CommonName", "")))
        id_form.addRow("Lease", self.create_readonly_line_edit(self.well_data.get("Lease", "")))
        id_form.addRow("Operator", self.create_readonly_line_edit(self.well_data.get("Operator", "")))
        left_vlayout.addWidget(id_group)
        
        file_group = QGroupBox("Related Files")
        file_layout = QHBoxLayout(file_group)
        self.file_combo = QComboBox()
        self.file_combo.addItems(["datasheet", "log", "las", "paleo"])
        self.open_file_btn = QPushButton("Open File")
        self.open_file_btn.clicked.connect(self.open_related_file)
        file_layout.addWidget(self.file_combo)
        file_layout.addWidget(self.open_file_btn)
        file_layout.addStretch()
        left_vlayout.addWidget(file_group)
        
        comment_group = QGroupBox("Comments")
        comment_layout = QVBoxLayout(comment_group)
        comment_box = QTextEdit()
        comment_box.setReadOnly(True)
        comment_box.setText(self.well_data.get("Comments", ""))
        comment_layout.addWidget(comment_box)
        left_vlayout.addWidget(comment_group)
        
        main_hlayout.addLayout(left_vlayout, stretch=2)
        
        # Right Column
        right_vlayout = QVBoxLayout()
        loc_group = QGroupBox("Latitude, Longitude")
        loc_layout = QVBoxLayout(loc_group)
        lat = self.well_data.get("Latitude", "")
        lon = self.well_data.get("Longitude", "")
        loc_layout.addWidget(self.create_readonly_line_edit(f"{lat}, {lon}"))
        right_vlayout.addWidget(loc_group)
        
        depth_group = QGroupBox("Depth")
        depth_form = QFormLayout(depth_group)
        depth_form.addRow("TVD (ft)", self.create_readonly_line_edit(self.well_data.get("TotalVerticalDepth", "")))
        depth_form.addRow("TVD Date", self.create_readonly_line_edit(self.well_data.get("TvdDate", "")))
        depth_form.addRow("Water Depth (ft)", self.create_readonly_line_edit(self.well_data.get("WaterDepthFt", "")))
        depth_form.addRow("KB (ft)", self.create_readonly_line_edit(self.well_data.get("KellyBushingFt", "")))
        right_vlayout.addWidget(depth_group)
        
        right_vlayout.addStretch()
        main_hlayout.addLayout(right_vlayout, stretch=1)
        self.tabs.addTab(tab, "Well Header")

    def setup_units_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        units = self.well_data.get("Units", [])
        table = QTableWidget(len(units), 5)
        table.setHorizontalHeaderLabels(["Top", "Thickness", "Unit", "Name", "Penetration"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        for r, u in enumerate(units):
            table.setItem(r, 0, QTableWidgetItem(str(u.get("Top", ""))))
            table.setItem(r, 1, QTableWidgetItem(str(u.get("Thickness", ""))))
            table.setItem(r, 2, QTableWidgetItem(str(u.get("Label", ""))))
            table.setItem(r, 3, QTableWidgetItem(str(u.get("Name", ""))))
            table.setItem(r, 4, QTableWidgetItem(str(u.get("Penetration", ""))))
            
        layout.addWidget(table)
        self.tabs.addTab(tab, "Units")

    def open_related_file(self):
        file_type = self.file_combo.currentText()
        folder_map = {
            "datasheet": "Datasheet",
            "log": "Log",
            "las": "LAS",
            "paleo": "Paleo"
        }
        
        folder = folder_map.get(file_type)
        if not folder: return
        
        # Structure maps to: Current_Database/Documentation/WellInfo/<Folder>
        search_dir = os.path.join(self.root_path, "Documentation", "WellInfo", folder)
        search_pattern = os.path.join(search_dir, f"*{self.gbds_id}*")
        matches = glob.glob(search_pattern)
        
        if matches:
            file_to_open = matches[0]
            try:
                os.startfile(file_to_open)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open file:\n{e}")
        else:
            QMessageBox.information(self, "Not Found", f"No {file_type} file found for well {self.gbds_id} in:\n{search_dir}")


class GbdsWellIdentifyTool(QgsMapTool):
    """Custom Map Tool using spatial intersection and dynamic CRS projection."""
    def __init__(self, canvas, iface):
        super().__init__(canvas)
        self.canvas = canvas
        self.iface = iface
        self.setCursor(Qt.CrossCursor)
        self.active_dialogs = [] 

    def canvasReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        map_pt = self.toMapCoordinates(event.pos())
        
        # Create a 5-pixel search box around the click
        tolerance = self.canvas.mapUnitsPerPixel() * 5
        search_rect = QgsRectangle(
            map_pt.x() - tolerance, map_pt.y() - tolerance,
            map_pt.x() + tolerance, map_pt.y() + tolerance
        )

        wells_found = []
        seen_ids = set()
        
        # Get the map canvas coordinate projection
        map_crs = self.canvas.mapSettings().destinationCrs()

        # Iterate through all currently checked/visible layers in the map
        for layer in self.canvas.layers():
            if layer.type() != layer.VectorLayer or not layer.isVisible():
                continue
            
            # Target any layer with "well" in the name, bypassing QGIS "Active Layer" rules
            if "well" not in layer.name().lower():
                continue

            # 1. Handle Coordinate Transformation dynamically
            layer_rect = search_rect
            if layer.crs() != map_crs:
                try:
                    xform = QgsCoordinateTransform(map_crs, layer.crs(), QgsProject.instance())
                    layer_rect = xform.transformBoundingBox(search_rect)
                except Exception:
                    pass

            request = QgsFeatureRequest().setFilterRect(layer_rect)
            
            for feat in layer.getFeatures(request):
                # Ensure accurate intersection within the box
                if feat.hasGeometry() and feat.geometry().intersects(layer_rect):
                    
                    gbds_id = None
                    api = ""
                    lease = ""
                    
                    # 2. Fuzzy Field matching (Checks both internal names and User Aliases)
                    for idx, field in enumerate(layer.fields()):
                        fname = field.name().lower()
                        falias = field.alias().lower() if field.alias() else ""
                        val = feat.attribute(idx)
                        
                        if val in (None, "", "NULL"): 
                            continue
                        
                        # Match ID
                        if not gbds_id and (fname in ['gbds_wel', 'gbds_id', 'gbdsid', 'gbdswellid'] or 
                                            ('gbds' in fname and 'id' in fname) or 
                                            ('gbds' in falias and 'id' in falias)):
                            gbds_id = str(val)
                        
                        # Match API
                        elif not api and fname == 'api':
                            api = str(val)
                            
                        # Match Lease
                        elif not lease and fname == 'lease':
                            lease = str(val)

                    if gbds_id and gbds_id not in seen_ids:
                        seen_ids.add(gbds_id)
                        wells_found.append({
                            "id": gbds_id,
                            "api": api,
                            "lease": lease
                        })

        if not wells_found:
            # Uncomment if you want to notify the user when they click empty space
            # self.iface.messageBar().pushInfo("GBDS", "No wells found at this click location.")
            return

        root_path = QgsSettings().value("gbds/root_path", "")
        if not root_path or not os.path.exists(root_path):
            self.iface.messageBar().pushWarning("Setup Required", "Please click '⚙️ GBDS Connection' in the sidebar first to set your database location.")
            return

        if len(wells_found) == 1:
            self._show_well_info(wells_found[0]["id"], root_path)
        else:
            selection_dialog = WellSelectionDialog(wells_found, self.iface.mainWindow())
            if selection_dialog.exec_() == QDialog.Accepted:
                self._show_well_info(selection_dialog.selected_gbds_id, root_path)

    def _show_well_info(self, gbds_id, root_path):
        # Clean up any previously closed windows to keep memory usage low
        self.active_dialogs = [d for d in self.active_dialogs if d.isVisible()]
        
        dialog = WellInfoDialog(gbds_id, root_path, self.iface.mainWindow())
        self.active_dialogs.append(dialog)
        dialog.show()