import os
from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, 
    QTabWidget, QToolButton, QMessageBox
)
from qgis.PyQt.QtCore import Qt, QUrl, QSize
from qgis.PyQt.QtGui import QIcon, QDesktopServices
from qgis.core import QgsSettings

class GBDSRibbon(QDockWidget):
    """A Top-Docked Widget mimicking the ArcGIS Pro Ribbon."""
    def __init__(self, iface, plugin, parent=None):
        super().__init__("GBDS Tools", parent)
        self.iface = iface
        self.plugin = plugin
        self.setAllowedAreas(Qt.TopDockWidgetArea)
        
        # Keep the title bar clean
        self.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable)

        # Main Container
        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Tabs
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)
        self.setWidget(self.container)

        # Build Tabs
        self._setup_config_tab()
        self._setup_browse_tab()
        self._setup_tools_tab()
        self._setup_help_tab()

    def _get_icon(self, icon_name):
        """Helper to safely load 32x32 icons from the images folder."""
        icon_path = os.path.join(os.path.dirname(__file__), 'images', icon_name)
        return QIcon(icon_path)

    def _create_tool_button(self, text, icon_name, tooltip="", checkable=False):
        """Helper to create standard ribbon buttons."""
        btn = QToolButton()
        btn.setText(text)
        btn.setIcon(self._get_icon(icon_name))
        btn.setIconSize(QSize(32, 32))
        btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        btn.setToolTip(tooltip)
        btn.setCheckable(checkable)
        
        # Ensure minimum width so text isn't cut off
        btn.setMinimumWidth(75) 
        return btn

    def _add_tab(self, name):
        """Helper to create and add a tab."""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setAlignment(Qt.AlignLeft)
        self.tabs.addTab(tab, name)
        return layout

    def _open_gbds_path(self, *subdirs):
        """Helper to safely open local GBDS folders/files."""
        root_path = QgsSettings().value("gbds/root_path", "")
        if not root_path or not os.path.exists(root_path):
            self.iface.messageBar().pushWarning("Setup Required", "Please click 'Setup' in the Config tab first.")
            return

        target_path = os.path.join(root_path, *subdirs)
        if os.path.exists(target_path):
            try:
                os.startfile(target_path)
            except Exception as e:
                self.iface.messageBar().pushCritical("Error", f"Could not open path:\n{e}")
        else:
            self.iface.messageBar().pushWarning("Not Found", f"Could not find:\n{target_path}")

    # --- TAB SETUPS ---

    def _setup_config_tab(self):
        layout = self._add_tab("Config")
        
        self.btn_setup = self._create_tool_button("Setup", "AddIn32.png", "Configure GBDS Root Folder")
        self.btn_setup.clicked.connect(lambda: self.plugin.dock_widget.run_setup())
        layout.addWidget(self.btn_setup)
        
        self.btn_about = self._create_tool_button("About", "GenericButtonBlue32.png", "About GBDS Tools")
        self.btn_about.clicked.connect(lambda: QMessageBox.information(self, "About", "GBDS QGIS Tools\nVersion 1.0"))
        layout.addWidget(self.btn_about)

    def _setup_browse_tab(self):
        layout = self._add_tab("Browse")
        
        self.btn_maps = self._create_tool_button("Maps", "GenericButtonOrange32.png", "Browse Preconstructed Maps")
        self.btn_maps.clicked.connect(lambda: self._open_gbds_path("Preconstructed_Maps"))
        layout.addWidget(self.btn_maps)
        
        self.btn_references = self._create_tool_button("References", "References32.png", "Open Reference Library")
        self.btn_references.clicked.connect(lambda: self._open_gbds_path("References", "Library"))
        layout.addWidget(self.btn_references)
        
        self.btn_map_layers = self._create_tool_button("Map Layers", "MapLayers32.png", "Toggle Catalog Pane", checkable=True)
        self.btn_map_layers.clicked.connect(lambda checked: self.plugin.dock_widget.setVisible(checked))
        layout.addWidget(self.btn_map_layers)
        
        self.btn_figures = self._create_tool_button("Figures", "FigureGallery32.png", "Open Figures Gallery")
        self.btn_figures.clicked.connect(lambda: self._open_gbds_path("Documentation", "Figures"))
        layout.addWidget(self.btn_figures)

    def _setup_tools_tab(self):
        layout = self._add_tab("Tools")
        
        # Map Tools (Checkable, logic handled in gbds_plugin.py)
        self.btn_well = self._create_tool_button("Well", "Well32.png", "Query Well Tool", checkable=True)
        self.btn_las = self._create_tool_button("LAS", "Las32.png", "View LAS Tool", checkable=True)
        self.btn_cross = self._create_tool_button("Cross\nSection", "CrossSection32.png", "Open Cross Section Tool", checkable=True)
        self.btn_zircon = self._create_tool_button("Zircon", "Zircon32.png", "View Zircon Plot Tool", checkable=True)
        
        # Placeholder for future Reference selection tool
        self.btn_reference = self._create_tool_button("Reference", "SelectRef32.png", "Spatial Reference Select", checkable=True)
        
        # Explore Tool (Standard Pan/Zoom)
        self.btn_explore = self._create_tool_button("Explore", "GenericButtonBlue32.png", "Standard Navigation")
        self.btn_explore.clicked.connect(lambda: self.iface.mapCanvas().unsetMapTool(self.iface.mapCanvas().mapTool()))

        layout.addWidget(self.btn_well)
        layout.addWidget(self.btn_las)
        layout.addWidget(self.btn_cross)
        layout.addWidget(self.btn_zircon)
        layout.addWidget(self.btn_reference)
        layout.addWidget(self.btn_explore)

    def _setup_help_tab(self):
        layout = self._add_tab("Help")
        
        self.btn_guide = self._create_tool_button("User Guide", "GenericButtonPurple32.png", "Open User Guide")
        self.btn_guide.clicked.connect(lambda: self._open_gbds_path("Documentation", "GBDS_User_Guide.pdf"))
        layout.addWidget(self.btn_guide)
        
        self.btn_tutorial = self._create_tool_button("Tutorial", "GenericButtonPurple32.png", "Open Workshop Tutorial")
        self.btn_tutorial.clicked.connect(lambda: self._open_gbds_path("Documentation", "GBDS_Workshop.pdf"))
        layout.addWidget(self.btn_tutorial)
        
        self.btn_support = self._create_tool_button("Support", "GenericButtonPurple32.png", "Email GBDS Support")
        self.btn_support.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("mailto:GBDS@ig.utexas.edu")))
        layout.addWidget(self.btn_support)