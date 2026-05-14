from qgis.PyQt.QtWidgets import QAction, QToolButton
from qgis.PyQt.QtCore import Qt
from .gbds_dock import GBDSCatalogDock
from .gbds_well_tool import GbdsWellIdentifyTool
from .gbds_cross_section_tool import GbdsCrossSectionTool
from .gbds_zircon_tool import GbdsZirconTool
from .gbds_las_tool import GbdsLasTool

class GBDSToolsPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.dock_widget = None
        
        # Actions
        self.action_toggle_dock = None
        self.action_query_well = None
        self.action_cross_section = None
        self.action_zircon = None
        self.action_las = None
        
        # Toolbar Buttons
        self.button_action_dock = None
        self.button_action_query = None
        self.button_action_cross = None
        self.button_action_zircon = None
        self.button_action_las = None
        
        # Tools
        self.query_tool = None
        self.cross_tool = None
        self.zircon_tool = None
        self.las_tool = None

    def initGui(self):
        # 1. Sidebar (Dock Widget)
        self.dock_widget = GBDSCatalogDock(self.iface, self.iface.mainWindow())
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)
        self.dock_widget.setVisible(False) 
        
        # 2. Map Tools
        self.query_tool = GbdsWellIdentifyTool(self.iface.mapCanvas(), self.iface)
        self.cross_tool = GbdsCrossSectionTool(self.iface.mapCanvas(), self.iface)
        self.zircon_tool = GbdsZirconTool(self.iface.mapCanvas(), self.iface)
        self.las_tool = GbdsLasTool(self.iface.mapCanvas(), self.iface)
        
        # 3. Actions
        self.action_toggle_dock = QAction("GBDS", self.iface.mainWindow())
        self.action_toggle_dock.setCheckable(True)
        self.action_toggle_dock.setChecked(False)
        self.action_toggle_dock.triggered.connect(self.toggle_dock)
        
        self.action_query_well = QAction("♦ Query Well", self.iface.mainWindow())
        self.action_query_well.setCheckable(True)
        self.action_query_well.triggered.connect(self.activate_query_tool)
        
        self.action_las = QAction("📉 View LAS", self.iface.mainWindow())
        self.action_las.setCheckable(True)
        self.action_las.triggered.connect(self.activate_las_tool)
        
        self.action_cross_section = QAction("〰️ Cross Section", self.iface.mainWindow())
        self.action_cross_section.setCheckable(True)
        self.action_cross_section.triggered.connect(self.activate_cross_tool)

        self.action_zircon = QAction("✨ Zircon", self.iface.mainWindow())
        self.action_zircon.setCheckable(True)
        self.action_zircon.triggered.connect(self.activate_zircon_tool)
        
        # 4. Format Buttons
        btn_dock = QToolButton()
        btn_dock.setDefaultAction(self.action_toggle_dock)
        btn_dock.setToolButtonStyle(Qt.ToolButtonTextOnly)
        font = btn_dock.font()
        font.setBold(True)
        btn_dock.setFont(font)
        
        btn_query = QToolButton()
        btn_query.setDefaultAction(self.action_query_well)
        btn_query.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        btn_las = QToolButton()
        btn_las.setDefaultAction(self.action_las)
        btn_las.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        
        btn_cross = QToolButton()
        btn_cross.setDefaultAction(self.action_cross_section)
        btn_cross.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        btn_zircon = QToolButton()
        btn_zircon.setDefaultAction(self.action_zircon)
        btn_zircon.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        
        # 5. Inject into Toolbar
        toolbar = self.iface.pluginToolBar()
        self.button_action_dock = toolbar.addWidget(btn_dock)
        self.button_action_query = toolbar.addWidget(btn_query)
        self.button_action_las = toolbar.addWidget(btn_las)
        self.button_action_cross = toolbar.addWidget(btn_cross)
        self.button_action_zircon = toolbar.addWidget(btn_zircon)
        
        # Sync states
        self.dock_widget.visibilityChanged.connect(self.action_toggle_dock.setChecked)
        self.iface.mapCanvas().mapToolSet.connect(self.on_map_tool_changed)

    def unload(self):
        toolbar = self.iface.pluginToolBar()
        if self.button_action_dock: toolbar.removeAction(self.button_action_dock)
        if self.button_action_query: toolbar.removeAction(self.button_action_query)
        if self.button_action_las: toolbar.removeAction(self.button_action_las)
        if self.button_action_cross: toolbar.removeAction(self.button_action_cross)
        if self.button_action_zircon: toolbar.removeAction(self.button_action_zircon)
            
        if self.dock_widget:
            self.iface.removeDockWidget(self.dock_widget)
            self.dock_widget.deleteLater()

    def toggle_dock(self, checked):
        self.dock_widget.setVisible(checked)

    def activate_query_tool(self, checked):
        if checked: self.iface.mapCanvas().setMapTool(self.query_tool)
        else: self.iface.mapCanvas().unsetMapTool(self.query_tool)
        
    def activate_las_tool(self, checked):
        if checked: self.iface.mapCanvas().setMapTool(self.las_tool)
        else: self.iface.mapCanvas().unsetMapTool(self.las_tool)

    def activate_cross_tool(self, checked):
        if checked: self.iface.mapCanvas().setMapTool(self.cross_tool)
        else: self.iface.mapCanvas().unsetMapTool(self.cross_tool)

    def activate_zircon_tool(self, checked):
        if checked: self.iface.mapCanvas().setMapTool(self.zircon_tool)
        else: self.iface.mapCanvas().unsetMapTool(self.zircon_tool)

    def on_map_tool_changed(self, tool):
        if tool != self.query_tool: self.action_query_well.setChecked(False)
        if tool != self.las_tool: self.action_las.setChecked(False)
        if tool != self.cross_tool: self.action_cross_section.setChecked(False)
        if tool != self.zircon_tool: self.action_zircon.setChecked(False)