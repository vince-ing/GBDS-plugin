import os
import json
import glob
import csv
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
    QgsCoordinateTransform, QgsProject, QgsMapLayerType
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
        
        # Updated columns to match your screenshot exactly
        headers = [
            "Unit", "Name", "Penetration", "Geologic Setting", "Top (ft)", 
            "Thickness (ft)", "Gross Sandstone (ft)", "Gross Carbonate (ft)", 
            "Carbonate Material", "Depofacies", "References"
        ]
        
        self.units_table = QTableWidget(len(units), len(headers))
        self.units_table.setHorizontalHeaderLabels(headers)
        
        # Resize behavior: stretch names/descriptions, wrap to contents for others
        self.units_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.units_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch) # Name
        self.units_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch) # Penetration
        
        self.units_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.units_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.units_table.setSelectionMode(QAbstractItemView.SingleSelection)
        
        for r, u in enumerate(units):
            # Parse Depofacies list of dicts into a comma-separated string
            depo_list = u.get("Depofacies", [])
            depo_str = ", ".join([d.get("Label", "") for d in depo_list]) if depo_list else ""
            
            # Parse References list into a comma-separated string
            ref_list = u.get("References", [])
            ref_str = ", ".join([str(ref) for ref in ref_list]) if ref_list else ""

            self.units_table.setItem(r, 0, QTableWidgetItem(str(u.get("Label", ""))))
            self.units_table.setItem(r, 1, QTableWidgetItem(str(u.get("Name", ""))))
            self.units_table.setItem(r, 2, QTableWidgetItem(str(u.get("Penetration", ""))))
            self.units_table.setItem(r, 3, QTableWidgetItem(str(u.get("GeoSetting", "-"))))
            self.units_table.setItem(r, 4, QTableWidgetItem(str(u.get("Top", ""))))
            self.units_table.setItem(r, 5, QTableWidgetItem(str(u.get("Thickness", ""))))
            self.units_table.setItem(r, 6, QTableWidgetItem(str(u.get("GrossSand", ""))))
            self.units_table.setItem(r, 7, QTableWidgetItem(str(u.get("GrossLime", ""))))
            self.units_table.setItem(r, 8, QTableWidgetItem(str(u.get("Carbonate", "-"))))
            self.units_table.setItem(r, 9, QTableWidgetItem(depo_str))
            
            # Make the reference item stand out (e.g., blue text to imply it's clickable)
            ref_item = QTableWidgetItem(ref_str)
            from qgis.PyQt.QtGui import QColor
            ref_item.setForeground(QColor("blue"))
            self.units_table.setItem(r, 10, ref_item)
            
        layout.addWidget(self.units_table)
        self.tabs.addTab(tab, "Units")
        
        # Connect double clicking the table to open the reference dialog
        self.units_table.itemDoubleClicked.connect(self.on_unit_double_clicked)
        
    def on_unit_double_clicked(self, item):
        # If they double clicked the 'References' column (index 10)
        if item.column() == 10 and item.text():
            reference_ids = [r.strip() for r in item.text().split(',')]
            
            # Clean up old dialogs to prevent memory leaks
            if not hasattr(self, 'active_ref_dialogs'):
                self.active_ref_dialogs = []
            self.active_ref_dialogs = [d for d in self.active_ref_dialogs if d.isVisible()]
            
            well_title = f"Well {self.well_data.get('API', self.gbds_id)}"
            dialog = ReferenceInfoDialog(reference_ids, self.root_path, well_title, self)
            self.active_ref_dialogs.append(dialog)
            dialog.show()

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


class ReferenceInfoDialog(QDialog):
    """Dialog displaying details for selected GBDS references."""
    def __init__(self, reference_ids, root_path, well_title="", parent=None):
        super().__init__(parent)
        self.reference_ids = [str(r).strip() for r in reference_ids]
        self.root_path = root_path
        self.reference_data = []
        
        self.setWindowTitle(f"{well_title} References")
        self.resize(750, 450)
        
        layout = QVBoxLayout(self)
        
        # --- Top Table ---
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Id", "Category1", "Category2", "Reference"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)
        
        # --- Bottom Panel (Selected Reference) ---
        self.details_group = QGroupBox("Selected Reference")
        details_layout = QVBoxLayout(self.details_group)
        
        form_layout = QFormLayout()
        self.txt_author = QLineEdit()
        self.txt_title = QLineEdit()
        self.txt_source = QLineEdit()
        self.txt_link = QLineEdit()
        
        for txt in [self.txt_author, self.txt_title, self.txt_source, self.txt_link]:
            txt.setReadOnly(True)
            
        form_layout.addRow("Author", self.txt_author)
        form_layout.addRow("Title", self.txt_title)
        form_layout.addRow("Source", self.txt_source)
        form_layout.addRow("Link", self.txt_link)
        details_layout.addLayout(form_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_folder = QPushButton("Open Folder")
        self.btn_pdf = QPushButton("Open PDF")
        self.btn_map = QPushButton("Add to Map")
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_folder)
        btn_layout.addWidget(self.btn_pdf)
        btn_layout.addWidget(self.btn_map)
        btn_layout.addStretch()
        details_layout.addLayout(btn_layout)
        
        layout.addWidget(self.details_group)
        
        # --- Connections ---
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        self.btn_folder.clicked.connect(self.open_folder)
        self.btn_pdf.clicked.connect(self.open_pdf)
        self.btn_map.clicked.connect(self.add_to_map)
        
        # Load the data
        self.load_csv_data()

    def load_csv_data(self):
        csv_path = os.path.join(self.root_path, "References", "References.csv")
        if not os.path.exists(csv_path):
            QMessageBox.warning(self, "Missing File", f"Could not find references database at:\n{csv_path}")
            return
            
        try:
            with open(csv_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    ref_id = str(row.get("Ref_Id", "")).strip()
                    if ref_id in self.reference_ids:
                        self.reference_data.append(row)
                        
            # Populate table
            self.table.setRowCount(len(self.reference_data))
            for i, row_data in enumerate(self.reference_data):
                author = row_data.get("Author", "")
                year = row_data.get("Pub_Year", "")
                title = row_data.get("Title", "")
                source = row_data.get("Source", "")
                
                # Format: Author (Year). Title. Source.
                year_str = f" ({year})" if year and year.lower() != "n/a" else ""
                ref_text = f"{author}{year_str}. {title}. {source}".strip(" .")
                
                self.table.setItem(i, 0, QTableWidgetItem(row_data.get("Ref_Id", "")))
                self.table.setItem(i, 1, QTableWidgetItem(row_data.get("Category_1", "")))
                self.table.setItem(i, 2, QTableWidgetItem(row_data.get("Category_2", "")))
                self.table.setItem(i, 3, QTableWidgetItem(ref_text))
                
            if self.reference_data:
                self.table.selectRow(0)
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to read References.csv:\n{e}")

    def on_selection_changed(self):
        selected = self.table.selectedItems()
        if not selected:
            return
            
        row = selected[0].row()
        data = self.reference_data[row]
        
        self.txt_author.setText(data.get("Author", ""))
        self.txt_title.setText(data.get("Title", ""))
        self.txt_source.setText(data.get("Source", ""))
        self.txt_link.setText(data.get("Access_Link", ""))

    def _get_target_library_folder(self):
        """Helper to find the specific reference folder."""
        selected = self.table.selectedItems()
        if not selected: return None
        
        ref_id = selected[0].text()
        padded_id = ref_id.zfill(4) # GBDS pads folder names (e.g., '243' -> '0243_Name')
        
        base_lib_path = os.path.join(self.root_path, "References", "Library")
        matches = glob.glob(os.path.join(base_lib_path, f"{padded_id}_*"))
        
        # Fallback without padding just in case
        if not matches:
            matches = glob.glob(os.path.join(base_lib_path, f"{ref_id}_*"))
            
        return matches[0] if matches else None

    def open_folder(self):
        folder = self._get_target_library_folder()
        if folder and os.path.exists(folder):
            try:
                os.startfile(folder)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open folder:\n{e}")
        else:
            QMessageBox.information(self, "Not Found", "No folder found for this reference in the Library.")

    def open_pdf(self):
        folder = self._get_target_library_folder()
        if not folder or not os.path.exists(folder):
            QMessageBox.information(self, "Not Found", "No library folder found for this reference.")
            return
            
        # Look for PDFs in the folder
        pdfs = glob.glob(os.path.join(folder, "*.pdf"))
        if pdfs:
            # Prefer a PDF that matches the folder name
            folder_name = os.path.basename(folder)
            target_pdf = next((p for p in pdfs if folder_name in p), pdfs[0])
            try:
                os.startfile(target_pdf)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open PDF:\n{e}")
        else:
            QMessageBox.information(self, "Not Found", "No PDF files found inside this reference folder.")

    def add_to_map(self):
        folder = self._get_target_library_folder()
        if not folder or not os.path.exists(folder):
            QMessageBox.information(self, "Not Found", "No library folder found for this reference.")
            return
            
        # Look for converted QGIS layers or shapefiles
        map_files = glob.glob(os.path.join(folder, "*.qlr")) + glob.glob(os.path.join(folder, "*.shp"))
        
        if map_files:
            from qgis.core import QgsProject, QgsLayerDefinition, QgsVectorLayer
            for f in map_files:
                if f.endswith('.qlr'):
                    QgsLayerDefinition.loadLayerDefinition(f, QgsProject.instance(), QgsProject.instance().layerTreeRoot())
                elif f.endswith('.shp'):
                    layer = QgsVectorLayer(f, os.path.basename(f), "ogr")
                    if layer.isValid():
                        QgsProject.instance().addMapLayer(layer)
            QMessageBox.information(self, "Success", f"Added {len(map_files)} spatial file(s) to the map.")
        else:
            QMessageBox.information(self, "Not Found", "No spatial files (.qlr, .shp) found in this reference folder.")

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

        # Iterate through all currently rendered layers in the map
        for layer in self.canvas.layers():
            # If it's in canvas.layers(), it is already visible. Just check if it's a Vector.
            if layer.type() != QgsMapLayerType.VectorLayer:
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