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
from qgis.core import QgsSettings, QgsRectangle, QgsFeatureRequest

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
        
        # Try to load the JSON cache
        self.load_json_data()
        
        self.setWindowTitle(f"GBDS Well {self.gbds_id} - {self.well_data.get('API', '')} - {self.well_data.get('Lease', '')}")
        
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        self.setup_header_tab()
        self.setup_units_tab()

    def load_json_data(self):
        # Uses the relative structure from the Base DB Folder
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
    """Custom Map Tool using pure spatial intersection to avoid QGIS highlight bugs."""
    def __init__(self, canvas, iface):
        super().__init__(canvas)
        self.canvas = canvas
        self.iface = iface
        self.setCursor(Qt.CrossCursor)
        self.active_dialogs = [] # <-- FIX: Prevents Python from instantly deleting the dialog window

    def canvasReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        click_point = self.toMapCoordinates(event.pos())
        
        # Create a 5-pixel search box around the click
        tolerance = self.canvas.mapUnitsPerPixel() * 5
        search_rect = QgsRectangle(
            click_point.x() - tolerance, click_point.y() - tolerance,
            click_point.x() + tolerance, click_point.y() + tolerance
        )

        wells_found = []
        seen_ids = set()

        # Iterate through all currently checked/visible layers in the map
        for layer in self.canvas.layers():
            if layer.type() == layer.VectorLayer and "Well" in layer.name():
                
                request = QgsFeatureRequest().setFilterRect(search_rect)
                for feat in layer.getFeatures(request):
                    
                    # Search common attribute names for the ID
                    gbds_id = None
                    id_fields = ["GbdsId", "Gbds_Wel", "GBDS_ID", "Well_ID", "WellData_WellId", "WellData_Id"]
                    for f_name in id_fields:
                        idx = feat.fieldNameIndex(f_name)
                        if idx != -1:
                            val = feat.attribute(idx)
                            if val:
                                gbds_id = val
                                break
                                
                    if gbds_id and str(gbds_id) not in seen_ids:
                        seen_ids.add(str(gbds_id))
                        
                        # Grab extra info for disambiguation list
                        api_idx = feat.fieldNameIndex("API")
                        api = feat.attribute(api_idx) if api_idx != -1 else ""
                        lease_idx = feat.fieldNameIndex("Lease")
                        lease = feat.attribute(lease_idx) if lease_idx != -1 else ""
                        
                        wells_found.append({
                            "id": str(gbds_id),
                            "api": str(api),
                            "lease": str(lease)
                        })

        if not wells_found:
            return # Ignore clicks on empty map areas

        root_path = QgsSettings().value("gbds/root_path", "")
        if not root_path or not os.path.exists(root_path):
            self.iface.messageBar().pushWarning("Setup Required", "Please click '⚙️ GBDS Connection' in the sidebar first.")
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