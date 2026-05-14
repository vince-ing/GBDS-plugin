from qgis.PyQt.QtWidgets import QAction, QToolButton
from qgis.PyQt.QtCore import Qt
from .gbds_dock import GBDSCatalogDock
from .gbds_well_tool import GbdsWellIdentifyTool

class GBDSToolsPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.dock_widget = None
        self.action_toggle_dock = None
        self.action_query_well = None
        self.button_action_dock = None
        self.button_action_query = None
        self.query_tool = None

    def initGui(self):
        # 1. Create the Sidebar (Dock Widget)
        self.dock_widget = GBDSCatalogDock(self.iface, self.iface.mainWindow())
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)
        self.dock_widget.setVisible(False) 
        
        # 2. Create Map Tool Instance
        self.query_tool = GbdsWellIdentifyTool(self.iface.mapCanvas(), self.iface)
        
        # 3. Create the action for toggling the sidebar
        self.action_toggle_dock = QAction("GBDS", self.iface.mainWindow())
        self.action_toggle_dock.setCheckable(True)
        self.action_toggle_dock.setChecked(False)
        self.action_toggle_dock.setToolTip("Toggle Sidebar")
        self.action_toggle_dock.triggered.connect(self.toggle_dock)
        
        # 4. Create the action for the Query Well tool
        self.action_query_well = QAction("♦ Query Well", self.iface.mainWindow())
        self.action_query_well.setCheckable(True)
        self.action_query_well.setToolTip("Query a GBDS Well")
        self.action_query_well.triggered.connect(self.activate_query_tool)
        
        # 5. Format buttons to show text
        btn_dock = QToolButton()
        btn_dock.setDefaultAction(self.action_toggle_dock)
        btn_dock.setToolButtonStyle(Qt.ToolButtonTextOnly)
        font = btn_dock.font()
        font.setBold(True)
        btn_dock.setFont(font)
        
        btn_query = QToolButton()
        btn_query.setDefaultAction(self.action_query_well)
        btn_query.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        
        # 6. Inject directly into the native Plugins Toolbar
        toolbar = self.iface.pluginToolBar()
        self.button_action_dock = toolbar.addWidget(btn_dock)
        self.button_action_query = toolbar.addWidget(btn_query)
        
        # Sync states
        self.dock_widget.visibilityChanged.connect(self.action_toggle_dock.setChecked)
        self.iface.mapCanvas().mapToolSet.connect(self.deactivate_query_tool)

    def unload(self):
        if self.action_toggle_dock:
            self.iface.removePluginMenu("&GBDS Tools", self.action_toggle_dock)
            self.iface.removePluginMenu("&GBDS Tools", self.action_query_well)
            
        toolbar = self.iface.pluginToolBar()
        if self.button_action_dock:
            toolbar.removeAction(self.button_action_dock)
        if self.button_action_query:
            toolbar.removeAction(self.button_action_query)
            
        if self.dock_widget:
            self.iface.removeDockWidget(self.dock_widget)
            self.dock_widget.deleteLater()

    def toggle_dock(self, checked):
        self.dock_widget.setVisible(checked)

    def activate_query_tool(self, checked):
        if checked:
            self.iface.mapCanvas().setMapTool(self.query_tool)
        else:
            self.iface.mapCanvas().unsetMapTool(self.query_tool)

    def deactivate_query_tool(self, tool):
        # Automatically uncheck the button if the user switches to the standard pan/zoom tools
        if tool != self.query_tool:
            self.action_query_well.setChecked(False)