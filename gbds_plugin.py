from qgis.PyQt.QtWidgets import QAction, QToolButton
from qgis.PyQt.QtCore import Qt
from .gbds_dock import GBDSCatalogDock
from .gbds_ribbon import GBDSRibbon

# Import all map tools
from .gbds_well_tool import GbdsWellIdentifyTool
from .gbds_cross_section_tool import GbdsCrossSectionTool
from .gbds_zircon_tool import GbdsZirconTool
from .gbds_las_tool import GbdsLasTool
from .gbds_reference_tool import GbdsReferenceTool          # ← NEW


class GBDSToolsPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.dock_widget = None
        self.ribbon_widget = None

        self.action_toggle_ribbon = None
        self.master_toolbar_btn = None

        # Tools
        self.query_tool     = None
        self.cross_tool     = None
        self.zircon_tool    = None
        self.las_tool       = None
        self.reference_tool = None                           # ← NEW

    def initGui(self):
        # 1. Initialize UI Elements
        self.dock_widget = GBDSCatalogDock(self.iface, self.iface.mainWindow())
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)
        self.dock_widget.setVisible(False)

        self.ribbon_widget = GBDSRibbon(self.iface, self)
        self.iface.addDockWidget(Qt.TopDockWidgetArea, self.ribbon_widget)
        self.ribbon_widget.setVisible(False)

        # 2. Initialize Map Tools
        self.query_tool     = GbdsWellIdentifyTool(self.iface.mapCanvas(), self.iface)
        self.cross_tool     = GbdsCrossSectionTool(self.iface.mapCanvas(), self.iface)
        self.zircon_tool    = GbdsZirconTool(self.iface.mapCanvas(), self.iface)
        self.las_tool       = GbdsLasTool(self.iface.mapCanvas(), self.iface)
        self.reference_tool = GbdsReferenceTool(self.iface.mapCanvas(), self.iface)  # ← NEW

        # 3. Create Master Toggle for the Native QGIS Toolbar
        self.action_toggle_ribbon = QAction("GBDS", self.iface.mainWindow())
        self.action_toggle_ribbon.setCheckable(True)
        self.action_toggle_ribbon.setChecked(False)
        self.action_toggle_ribbon.setToolTip("Toggle GBDS Ribbon")
        self.action_toggle_ribbon.triggered.connect(self.ribbon_widget.setVisible)

        btn_master = QToolButton()
        btn_master.setDefaultAction(self.action_toggle_ribbon)
        btn_master.setToolButtonStyle(Qt.ToolButtonTextOnly)
        btn_master.setStyleSheet("""
            QToolButton {
                font-family: 'Segoe UI Semibold', 'Arial', sans-serif;
                font-size: 9pt;
                font-weight: 600;
                letter-spacing: 0.5px;
                padding: 0px 2px;
                color: #1a1a1a;
            }
        """)

        toolbar = self.iface.pluginToolBar()
        self.master_toolbar_btn = toolbar.addWidget(btn_master)

        # 4. Wire up the Ribbon buttons to the Map Tools
        self.ribbon_widget.btn_well.clicked.connect(self.activate_query_tool)
        self.ribbon_widget.btn_las.clicked.connect(self.activate_las_tool)
        self.ribbon_widget.btn_cross.clicked.connect(self.activate_cross_tool)
        self.ribbon_widget.btn_zircon.clicked.connect(self.activate_zircon_tool)
        self.ribbon_widget.btn_reference.clicked.connect(self.activate_reference_tool)  # ← NEW

        # 5. Sync UI states
        self.ribbon_widget.visibilityChanged.connect(self.action_toggle_ribbon.setChecked)
        self.dock_widget.visibilityChanged.connect(self.ribbon_widget.btn_map_layers.setChecked)

        # Connect global signal
        self.iface.mapCanvas().mapToolSet.connect(self.on_map_tool_changed)

    def unload(self):
        try:
            self.iface.mapCanvas().mapToolSet.disconnect(self.on_map_tool_changed)
        except TypeError:
            pass

        if self.master_toolbar_btn:
            self.iface.pluginToolBar().removeAction(self.master_toolbar_btn)

        if self.dock_widget:
            self.iface.removeDockWidget(self.dock_widget)
            self.dock_widget.deleteLater()

        if self.ribbon_widget:
            self.iface.removeDockWidget(self.ribbon_widget)
            self.ribbon_widget.deleteLater()

    # --- Tool Activation Logic ---
    def activate_query_tool(self, checked):
        if checked: self.iface.mapCanvas().setMapTool(self.query_tool)
        else:       self.iface.mapCanvas().unsetMapTool(self.query_tool)

    def activate_las_tool(self, checked):
        if checked: self.iface.mapCanvas().setMapTool(self.las_tool)
        else:       self.iface.mapCanvas().unsetMapTool(self.las_tool)

    def activate_cross_tool(self, checked):
        if checked: self.iface.mapCanvas().setMapTool(self.cross_tool)
        else:       self.iface.mapCanvas().unsetMapTool(self.cross_tool)

    def activate_zircon_tool(self, checked):
        if checked: self.iface.mapCanvas().setMapTool(self.zircon_tool)
        else:       self.iface.mapCanvas().unsetMapTool(self.zircon_tool)

    def activate_reference_tool(self, checked):                # ← NEW
        if checked: self.iface.mapCanvas().setMapTool(self.reference_tool)
        else:       self.iface.mapCanvas().unsetMapTool(self.reference_tool)

    def on_map_tool_changed(self, tool):
        """Uncheck buttons if user switches to a different tool (pan/zoom/etc.)."""
        if not self.ribbon_widget:
            return
        try:
            if tool != self.query_tool:     self.ribbon_widget.btn_well.setChecked(False)
            if tool != self.las_tool:       self.ribbon_widget.btn_las.setChecked(False)
            if tool != self.cross_tool:     self.ribbon_widget.btn_cross.setChecked(False)
            if tool != self.zircon_tool:    self.ribbon_widget.btn_zircon.setChecked(False)
            if tool != self.reference_tool: self.ribbon_widget.btn_reference.setChecked(False)  # ← NEW
        except RuntimeError:
            pass