from qgis.PyQt.QtWidgets import QAction, QToolButton
from qgis.PyQt.QtCore import Qt
from .gbds_dock import GBDSCatalogDock

class GBDSToolsPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.dock_widget = None
        self.action_toggle_dock = None
        self.button_action = None

    def initGui(self):
        # 1. Create the Sidebar (Dock Widget)
        self.dock_widget = GBDSCatalogDock(self.iface, self.iface.mainWindow())
        
        # 2. Add it to the QGIS interface (docked on the RIGHT side)
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)
        
        # HIDE BY DEFAULT so it doesn't open until clicked
        self.dock_widget.setVisible(False) 
        
        # 3. Create the action for the toolbar
        self.action_toggle_dock = QAction("GBDS", self.iface.mainWindow())
        self.action_toggle_dock.setCheckable(True)
        self.action_toggle_dock.setChecked(False) # Start un-clicked
        self.action_toggle_dock.setToolTip("Toggle Sidebar")
        self.action_toggle_dock.triggered.connect(self.toggle_dock)
        
        # 4. Create the ToolButton with Text
        button = QToolButton()
        button.setDefaultAction(self.action_toggle_dock)
        button.setToolButtonStyle(Qt.ToolButtonTextOnly)
        
        font = button.font()
        font.setBold(True)
        button.setFont(font)
        
        # 5. Inject DIRECTLY into the native Plugins Toolbar (next to ArcToQ)
        self.button_action = self.iface.pluginToolBar().addWidget(button)
        
        # Add the button to the QGIS "Plugins" menu as well
        self.iface.addPluginToMenu("&GBDS Tools", self.action_toggle_dock)
        
        # Keep the button state synced if the user manually closes the sidebar with the 'X'
        self.dock_widget.visibilityChanged.connect(self.action_toggle_dock.setChecked)

    def unload(self):
        # Clean everything up if the user uninstalls or disables the plugin
        if self.action_toggle_dock:
            self.iface.removePluginMenu("&GBDS Tools", self.action_toggle_dock)
            
        if self.button_action:
            self.iface.pluginToolBar().removeAction(self.button_action)
            
        if self.dock_widget:
            self.iface.removeDockWidget(self.dock_widget)
            self.dock_widget.deleteLater()

    def toggle_dock(self, checked):
        self.dock_widget.setVisible(checked)