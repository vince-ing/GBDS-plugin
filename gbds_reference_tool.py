import os
import csv
import glob
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QMessageBox, QHeaderView
)
from qgis.PyQt.QtCore import Qt, QRect, QPoint
from qgis.PyQt.QtGui import QColor, QPainter, QPen
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.core import (
    QgsSettings, QgsRectangle, QgsFeatureRequest,
    QgsCoordinateTransform, QgsProject, QgsMapLayerType,
    QgsWkbTypes, QgsGeometry
)


# ---------------------------------------------------------------------------
# ReferenceInfoDialog  (self-contained copy so this file has no circular deps)
# ---------------------------------------------------------------------------

class ReferenceInfoDialog(QDialog):
    """Dialog displaying reference details for a set of reference IDs."""

    def __init__(self, reference_ids, root_path, title="GBDS References", parent=None):
        super().__init__(parent)
        self.reference_ids = [str(r).strip() for r in reference_ids]
        self.root_path = root_path
        self.reference_data = []

        self.setWindowTitle(title)
        self.resize(750, 450)

        layout = QVBoxLayout(self)

        # ---- Top table ----
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Id", "Category1", "Category2", "Reference"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        # ---- Bottom panel ----
        self.details_group = QGroupBox("Selected Reference")
        details_layout = QVBoxLayout(self.details_group)

        form = QFormLayout()
        self.txt_author = QLineEdit(); self.txt_author.setReadOnly(True)
        self.txt_title  = QLineEdit(); self.txt_title.setReadOnly(True)
        self.txt_source = QLineEdit(); self.txt_source.setReadOnly(True)
        self.txt_link   = QLineEdit(); self.txt_link.setReadOnly(True)

        form.addRow("Author", self.txt_author)
        form.addRow("Title",  self.txt_title)
        form.addRow("Source", self.txt_source)
        form.addRow("Link",   self.txt_link)
        details_layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.btn_folder = QPushButton("Open Folder")
        self.btn_pdf    = QPushButton("Open PDF")
        self.btn_map    = QPushButton("Add to Map")
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_folder)
        btn_layout.addWidget(self.btn_pdf)
        btn_layout.addWidget(self.btn_map)
        btn_layout.addStretch()
        details_layout.addLayout(btn_layout)
        layout.addWidget(self.details_group)

        # ---- Connections ----
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        self.btn_folder.clicked.connect(self.open_folder)
        self.btn_pdf.clicked.connect(self.open_pdf)
        self.btn_map.clicked.connect(self.add_to_map)

        self.load_csv_data()

    # ------------------------------------------------------------------
    def load_csv_data(self):
        csv_path = os.path.join(self.root_path, "References", "References.csv")
        if not os.path.exists(csv_path):
            QMessageBox.warning(self, "Missing File",
                                f"Could not find references database at:\n{csv_path}")
            return

        try:
            with open(csv_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ref_id = str(row.get("Ref_Id", "")).strip()
                    if ref_id in self.reference_ids:
                        self.reference_data.append(row)

            # Preserve the order that reference_ids were supplied
            id_order = {rid: i for i, rid in enumerate(self.reference_ids)}
            self.reference_data.sort(key=lambda r: id_order.get(str(r.get("Ref_Id", "")).strip(), 999))

            self.table.setRowCount(len(self.reference_data))
            for i, row_data in enumerate(self.reference_data):
                author = row_data.get("Author", "")
                year   = row_data.get("Pub_Year", "")
                title  = row_data.get("Title", "")
                source = row_data.get("Source", "")

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

    # ------------------------------------------------------------------
    def on_selection_changed(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        row  = selected[0].row()
        data = self.reference_data[row]
        self.txt_author.setText(data.get("Author", ""))
        self.txt_title.setText(data.get("Title", ""))
        self.txt_source.setText(data.get("Source", ""))
        self.txt_link.setText(data.get("Access_Link", ""))

    # ------------------------------------------------------------------
    def _get_library_folder(self):
        selected = self.table.selectedItems()
        if not selected:
            return None
        ref_id     = selected[0].text()
        padded_id  = ref_id.zfill(4)
        base_lib   = os.path.join(self.root_path, "References", "Library")
        matches    = (glob.glob(os.path.join(base_lib, f"{padded_id}_*")) or
                      glob.glob(os.path.join(base_lib, f"{ref_id}_*")))
        return matches[0] if matches else None

    def open_folder(self):
        folder = self._get_library_folder()
        if folder and os.path.exists(folder):
            try:
                os.startfile(folder)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open folder:\n{e}")
        else:
            QMessageBox.information(self, "Not Found",
                                    "No folder found for this reference in the Library.")

    def open_pdf(self):
        folder = self._get_library_folder()
        if not folder or not os.path.exists(folder):
            QMessageBox.information(self, "Not Found",
                                    "No library folder found for this reference.")
            return
        pdfs = glob.glob(os.path.join(folder, "*.pdf"))
        if pdfs:
            folder_name = os.path.basename(folder)
            target = next((p for p in pdfs if folder_name in p), pdfs[0])
            try:
                os.startfile(target)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not open PDF:\n{e}")
        else:
            QMessageBox.information(self, "Not Found",
                                    "No PDF files found inside this reference folder.")

    def add_to_map(self):
        folder = self._get_library_folder()
        if not folder or not os.path.exists(folder):
            QMessageBox.information(self, "Not Found",
                                    "No library folder found for this reference.")
            return
        map_files = (glob.glob(os.path.join(folder, "*.qlr")) +
                     glob.glob(os.path.join(folder, "*.shp")))
        if map_files:
            from qgis.core import QgsLayerDefinition, QgsVectorLayer
            for f in map_files:
                if f.endswith('.qlr'):
                    QgsLayerDefinition.loadLayerDefinition(
                        f, QgsProject.instance(),
                        QgsProject.instance().layerTreeRoot())
                elif f.endswith('.shp'):
                    layer = QgsVectorLayer(f, os.path.basename(f), "ogr")
                    if layer.isValid():
                        QgsProject.instance().addMapLayer(layer)
            QMessageBox.information(self, "Success",
                                    f"Added {len(map_files)} spatial file(s) to the map.")
        else:
            QMessageBox.information(self, "Not Found",
                                    "No spatial files (.qlr, .shp) found in this reference folder.")


# ---------------------------------------------------------------------------
# GbdsReferenceTool  –  rubber-band bounding box → collect refs → show dialog
# ---------------------------------------------------------------------------

class GbdsReferenceTool(QgsMapTool):
    """
    Draw a bounding box on the map canvas.  Every visible vector feature
    inside the box whose attributes include a 'References' column (or any
    alias that contains 'ref') will have its reference IDs collected and
    shown in the ReferenceInfoDialog – exactly mirroring the ArcGIS GBDS
    Reference tool behaviour.
    """

    # Fields we accept as carrying reference IDs (lower-case comparison)
    _REF_FIELD_NAMES = {
        'references', 'reference', 'ref_ids', 'refs',
        'ref', 'reference_ids', 'gbds_refs', 'gbds_ref'
    }

    def __init__(self, canvas, iface):
        super().__init__(canvas)
        self.canvas  = canvas
        self.iface   = iface
        self.setCursor(Qt.CrossCursor)

        # Rubber-band rectangle drawn while the user drags
        self._rubber_band = QgsRubberBand(canvas, QgsWkbTypes.PolygonGeometry)
        self._rubber_band.setColor(QColor(0, 120, 215, 80))       # translucent blue fill
        self._rubber_band.setStrokeColor(QColor(0, 120, 215, 200)) # solid blue border
        self._rubber_band.setWidth(1)

        self._start_point = None   # QgsPointXY where drag began
        self._dragging    = False
        self._active_dialogs = []

    # ------------------------------------------------------------------
    # QgsMapTool overrides
    # ------------------------------------------------------------------

    def canvasPressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return
        self._start_point = self.toMapCoordinates(event.pos())
        self._dragging    = True
        self._rubber_band.reset(QgsWkbTypes.PolygonGeometry)

    def canvasMoveEvent(self, event):
        if not self._dragging or self._start_point is None:
            return
        current = self.toMapCoordinates(event.pos())
        self._update_rubber_band(self._start_point, current)

    def canvasReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or not self._dragging:
            return

        end_point     = self.toMapCoordinates(event.pos())
        self._dragging = False
        self._rubber_band.reset(QgsWkbTypes.PolygonGeometry)

        if self._start_point is None:
            return

        # Build the search rectangle (handles any drag direction)
        search_rect = QgsRectangle(self._start_point, end_point)
        search_rect.normalize()

        # A single click with no real drag → treat as a small tolerance box
        if search_rect.isEmpty() or search_rect.area() < 1e-12:
            tol = self.canvas.mapUnitsPerPixel() * 8
            search_rect = QgsRectangle(
                self._start_point.x() - tol, self._start_point.y() - tol,
                self._start_point.x() + tol, self._start_point.y() + tol,
            )

        self._collect_and_show(search_rect)

    def deactivate(self):
        self._rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        self._dragging    = False
        self._start_point = None
        super().deactivate()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_rubber_band(self, p1, p2):
        """Redraws the drag rectangle from corner p1 to corner p2."""
        rect = QgsRectangle(p1, p2)
        rect.normalize()
        geom = QgsGeometry.fromRect(rect)
        self._rubber_band.setToGeometry(geom, None)

    def _collect_and_show(self, search_rect):
        """Iterate visible layers, collect all reference IDs, open dialog."""
        root_path = QgsSettings().value("gbds/root_path", "")
        if not root_path or not os.path.exists(root_path):
            self.iface.messageBar().pushWarning(
                "Setup Required",
                "Please click '⚙️ GBDS Connection' first to set your database location."
            )
            return

        map_crs      = self.canvas.mapSettings().destinationCrs()
        ref_ids_seen = set()   # de-duplicate across all layers/features
        ref_ids_ordered = []   # preserve first-encounter order

        for layer in self.canvas.layers():
            if layer.type() != QgsMapLayerType.VectorLayer:
                continue

            # Transform the search rect into the layer's own CRS if needed
            layer_rect = search_rect
            if layer.crs() != map_crs:
                try:
                    xform      = QgsCoordinateTransform(
                        map_crs, layer.crs(), QgsProject.instance())
                    layer_rect = xform.transformBoundingBox(search_rect)
                except Exception:
                    pass

            # Find the reference field index for this layer (if any)
            ref_field_idx = self._find_ref_field_index(layer)
            if ref_field_idx is None:
                continue  # layer carries no reference data – skip

            request = QgsFeatureRequest().setFilterRect(layer_rect)
            for feat in layer.getFeatures(request):
                if not feat.hasGeometry():
                    continue
                if not feat.geometry().intersects(layer_rect):
                    continue

                raw = feat.attribute(ref_field_idx)
                if raw in (None, "", "NULL"):
                    continue

                # References column can be a comma-separated list of IDs
                for part in str(raw).split(','):
                    rid = part.strip()
                    if rid and rid not in ref_ids_seen:
                        ref_ids_seen.add(rid)
                        ref_ids_ordered.append(rid)

        if not ref_ids_ordered:
            self.iface.messageBar().pushInfo(
                "GBDS Reference",
                "No references found in the selected area."
            )
            return

        # Clean up any already-closed dialogs
        self._active_dialogs = [d for d in self._active_dialogs if d.isVisible()]

        dialog = ReferenceInfoDialog(
            ref_ids_ordered,
            root_path,
            title=f"GBDS Well References  ({len(ref_ids_ordered)} found)",
            parent=self.iface.mainWindow()
        )
        self._active_dialogs.append(dialog)
        dialog.show()

    def _find_ref_field_index(self, layer):
        """
        Return the field index of the first field whose name or alias looks
        like a 'references' column, or None if the layer has no such field.

        Priority order:
          1. Exact match against _REF_FIELD_NAMES
          2. Field name/alias that *contains* 'ref'
        """
        fields = layer.fields()

        # Pass 1 – exact match
        for idx, field in enumerate(fields):
            name  = field.name().lower()
            alias = (field.alias() or "").lower()
            if name in self._REF_FIELD_NAMES or alias in self._REF_FIELD_NAMES:
                return idx

        # Pass 2 – substring match (catches 'gbds_references', 'ref_list', etc.)
        for idx, field in enumerate(fields):
            name  = field.name().lower()
            alias = (field.alias() or "").lower()
            if 'ref' in name or 'ref' in alias:
                # Exclude common false-positives like 'refresh', 'preferred'
                false_positives = {'preferred', 'refresh', 'deferral', 'reference_crs'}
                if name not in false_positives and alias not in false_positives:
                    return idx

        return None