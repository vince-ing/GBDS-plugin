import os
import csv
import glob
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QMessageBox, QHeaderView
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.core import (
    QgsSettings, QgsRectangle, QgsFeatureRequest,
    QgsCoordinateTransform, QgsProject, QgsMapLayerType,
    QgsWkbTypes, QgsGeometry
)


# ---------------------------------------------------------------------------
# ReferenceInfoDialog
# ---------------------------------------------------------------------------

class ReferenceInfoDialog(QDialog):
    """
    Dialog displaying reference details for a set of reference IDs.

    Parameters
    ----------
    reference_ids : list[str]
        Ordered, de-duplicated list of reference IDs to display.
    root_path : str
        GBDS root folder (used to locate References.csv and the Library).
    source_map : dict[str, str]
        Maps each reference ID -> the layer name it was found in.
        Populates the "Source Layer" column so the user always knows
        which layer each reference came from.
    title : str
        Window title — set dynamically by GbdsReferenceTool so it
        reflects the actual layer name(s) rather than a generic string.
    """

    def __init__(self, reference_ids, root_path, source_map=None,
                 title="GBDS References", parent=None):
        super().__init__(parent)
        self.reference_ids  = [str(r).strip() for r in reference_ids]
        self.root_path      = root_path
        self.source_map     = source_map or {}   # ref_id -> layer name
        self.reference_data = []                 # list of CSV row dicts

        self.setWindowTitle(title)
        self.resize(860, 480)

        layout = QVBoxLayout(self)

        # ---- Top table ----
        # Columns: Id | Source Layer | Category1 | Category2 | Reference
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Id", "Source Layer", "Category1", "Category2", "Reference"]
        )
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)   # Id
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)   # Source Layer
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)   # Category1
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)   # Category2
        hh.setSectionResizeMode(4, QHeaderView.Stretch)            # Reference (fills remaining)
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

            # Preserve the caller-supplied order
            id_order = {rid: i for i, rid in enumerate(self.reference_ids)}
            self.reference_data.sort(
                key=lambda r: id_order.get(str(r.get("Ref_Id", "")).strip(), 999)
            )

            self.table.setRowCount(len(self.reference_data))
            for i, row_data in enumerate(self.reference_data):
                ref_id     = str(row_data.get("Ref_Id", "")).strip()
                author     = row_data.get("Author", "")
                year       = row_data.get("Pub_Year", "")
                title      = row_data.get("Title", "")
                source     = row_data.get("Source", "")
                layer_name = self.source_map.get(ref_id, "")

                year_str = f" ({year})" if year and year.lower() != "n/a" else ""
                ref_text = f"{author}{year_str}. {title}. {source}".strip(" .")

                self.table.setItem(i, 0, QTableWidgetItem(ref_id))
                self.table.setItem(i, 1, QTableWidgetItem(layer_name))
                self.table.setItem(i, 2, QTableWidgetItem(row_data.get("Category_1", "")))
                self.table.setItem(i, 3, QTableWidgetItem(row_data.get("Category_2", "")))
                self.table.setItem(i, 4, QTableWidgetItem(ref_text))

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
    def _get_selected_ref_id(self):
        selected = self.table.selectedItems()
        if not selected:
            return None
        return self.table.item(selected[0].row(), 0).text()

    def _get_library_folder(self):
        ref_id = self._get_selected_ref_id()
        if not ref_id:
            return None
        padded_id = ref_id.zfill(4)
        base_lib  = os.path.join(self.root_path, "References", "Library")
        matches   = (glob.glob(os.path.join(base_lib, f"{padded_id}_*")) or
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
# GbdsReferenceTool
# ---------------------------------------------------------------------------

class GbdsReferenceTool(QgsMapTool):
    """
    Draw a bounding box on the map canvas.  Every visible vector feature
    inside the box whose attributes include a References column will have
    its reference IDs collected and shown in ReferenceInfoDialog.

    Title logic
    -----------
    - One contributing layer  → "<Layer Name> References  (N found)"
      e.g. "Zircon Sample References  (4 found)"
    - Multiple contributing layers → "GBDS References — Layer A, Layer B  (N found)"

    The "Source Layer" column in the table tells the user exactly which
    layer each individual reference row came from.
    """

    _REF_FIELD_NAMES = {
        'references', 'reference', 'ref_ids', 'refs',
        'ref', 'reference_ids', 'gbds_refs', 'gbds_ref'
    }
    _REF_FALSE_POSITIVES = {'preferred', 'refresh', 'deferral', 'reference_crs'}

    def __init__(self, canvas, iface):
        super().__init__(canvas)
        self.canvas  = canvas
        self.iface   = iface
        self.setCursor(Qt.CrossCursor)

        self._rubber_band = QgsRubberBand(canvas, QgsWkbTypes.PolygonGeometry)
        self._rubber_band.setColor(QColor(0, 120, 215, 80))
        self._rubber_band.setStrokeColor(QColor(0, 120, 215, 200))
        self._rubber_band.setWidth(1)

        self._start_point    = None
        self._dragging       = False
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
        self._update_rubber_band(self._start_point,
                                 self.toMapCoordinates(event.pos()))

    def canvasReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or not self._dragging:
            return

        end_point      = self.toMapCoordinates(event.pos())
        self._dragging = False
        self._rubber_band.reset(QgsWkbTypes.PolygonGeometry)

        if self._start_point is None:
            return

        search_rect = QgsRectangle(self._start_point, end_point)
        search_rect.normalize()

        # Single click (no real drag) → small tolerance box
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
        rect = QgsRectangle(p1, p2)
        rect.normalize()
        self._rubber_band.setToGeometry(QgsGeometry.fromRect(rect), None)

    def _collect_and_show(self, search_rect):
        root_path = QgsSettings().value("gbds/root_path", "")
        if not root_path or not os.path.exists(root_path):
            self.iface.messageBar().pushWarning(
                "Setup Required",
                "Please click '⚙️ GBDS Connection' first to set your database location."
            )
            return

        map_crs = self.canvas.mapSettings().destinationCrs()

        # ref_id -> layer name  (first-seen layer wins for de-dup)
        source_map      = {}
        ref_ids_ordered = []   # insertion-order de-duplicated
        # Ordered list of layer names that actually contributed at least one ref
        layer_names_hit = []

        for layer in self.canvas.layers():
            if layer.type() != QgsMapLayerType.VectorLayer:
                continue

            ref_field_idx = self._find_ref_field_index(layer)
            if ref_field_idx is None:
                continue

            # CRS transform if necessary
            layer_rect = search_rect
            if layer.crs() != map_crs:
                try:
                    xform      = QgsCoordinateTransform(
                        map_crs, layer.crs(), QgsProject.instance())
                    layer_rect = xform.transformBoundingBox(search_rect)
                except Exception:
                    pass

            layer_contributed = False
            request = QgsFeatureRequest().setFilterRect(layer_rect)

            for feat in layer.getFeatures(request):
                if not feat.hasGeometry():
                    continue
                if not feat.geometry().intersects(layer_rect):
                    continue

                raw = feat.attribute(ref_field_idx)
                if raw in (None, "", "NULL"):
                    continue

                for part in str(raw).split(','):
                    rid = part.strip()
                    if not rid:
                        continue
                    if rid not in source_map:
                        source_map[rid]   = layer.name()
                        ref_ids_ordered.append(rid)
                        layer_contributed = True
                    # If already seen from another layer, keep first attribution

            if layer_contributed and layer.name() not in layer_names_hit:
                layer_names_hit.append(layer.name())

        if not ref_ids_ordered:
            self.iface.messageBar().pushInfo(
                "GBDS Reference",
                "No references found in the selected area."
            )
            return

        # ------------------------------------------------------------------
        # Build title from the actual contributing layer name(s)
        # ------------------------------------------------------------------
        n = len(ref_ids_ordered)
        if len(layer_names_hit) == 1:
            # Single source: use its exact name
            # e.g. "Zircon Sample References  (4 found)"
            title = f"{layer_names_hit[0]} References  ({n} found)"
        else:
            # Multiple sources: list them
            # e.g. "GBDS References — Zircon Sample, GBDS Well  (7 found)"
            joined = ", ".join(layer_names_hit)
            title  = f"GBDS References — {joined}  ({n} found)"

        self._active_dialogs = [d for d in self._active_dialogs if d.isVisible()]

        dialog = ReferenceInfoDialog(
            ref_ids_ordered,
            root_path,
            source_map=source_map,
            title=title,
            parent=self.iface.mainWindow()
        )
        self._active_dialogs.append(dialog)
        dialog.show()

    def _find_ref_field_index(self, layer):
        """
        Return the index of the first field that looks like a references
        column, or None if the layer has no such field.
        Priority: exact name match first, then substring match.
        """
        fields = layer.fields()

        # Pass 1 – exact match
        for idx, field in enumerate(fields):
            name  = field.name().lower()
            alias = (field.alias() or "").lower()
            if name in self._REF_FIELD_NAMES or alias in self._REF_FIELD_NAMES:
                return idx

        # Pass 2 – substring match
        for idx, field in enumerate(fields):
            name  = field.name().lower()
            alias = (field.alias() or "").lower()
            if 'ref' in name or 'ref' in alias:
                if (name not in self._REF_FALSE_POSITIVES and
                        alias not in self._REF_FALSE_POSITIVES):
                    return idx

        return None