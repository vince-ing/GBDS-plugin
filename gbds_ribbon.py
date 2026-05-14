import os
import glob
from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, 
    QToolButton, QLabel, QMessageBox, QFrame, QSizePolicy, QGridLayout
)
from qgis.PyQt.QtCore import Qt, QUrl, QSize
from qgis.PyQt.QtGui import QIcon, QDesktopServices
from qgis.core import QgsSettings

class GBDSRibbon(QDockWidget):
    """A Top-Docked Widget perfectly mimicking the flattened ArcGIS Pro Ribbon."""
    def __init__(self, iface, plugin, parent=None):
        super().__init__("GBDS Tools", parent)
        self.iface = iface
        self.plugin = plugin
        self.setAllowedAreas(Qt.TopDockWidgetArea)
        
        # 1. HIDE THE CHUNKY TITLE BAR
        self.setTitleBarWidget(QWidget())

        # Main Container
        self.container = QWidget()
        # Force the widget to be as vertically compact as possible
        self.container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Flattened Horizontal Layout
        self.main_layout = QHBoxLayout(self.container)
        self.main_layout.setContentsMargins(5, 5, 5, 2)
        self.main_layout.setSpacing(10)
        self.setWidget(self.container)

        # Build Ribbon Groups
        self._build_config_group()
        self._add_separator()
        self._build_browse_group()
        self._add_separator()
        self._build_tools_group()
        self._add_separator()
        self._build_help_group()
        
        # Push everything to the left side of the screen
        self.main_layout.addStretch()

    def _get_icon(self, icon_name):
        """Loads icons relative to this plugin file's location."""
        path = os.path.join(os.path.dirname(__file__), 'images', icon_name)
        return QIcon(path)

    def _create_large_button(self, text, icon_name, tooltip="", checkable=False):
        """Builds a 32x32 button with text underneath."""
        btn = QToolButton()
        btn.setText(text)
        btn.setIcon(self._get_icon(icon_name))
        btn.setIconSize(QSize(32, 32))
        btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        btn.setToolTip(tooltip)
        btn.setCheckable(checkable)
        btn.setAutoRaise(True) # Gives it the flat ribbon feel
        btn.setMinimumWidth(55)
        return btn

    def _create_small_button(self, text, icon_name, tooltip="", checkable=False):
        """Builds a 16x16 button with text beside it."""
        btn = QToolButton()
        btn.setText(text)
        btn.setIcon(self._get_icon(icon_name))
        btn.setIconSize(QSize(16, 16))
        btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        btn.setToolTip(tooltip)
        btn.setCheckable(checkable)
        btn.setAutoRaise(True)
        # Ensure the text aligns to the left if stacked
        btn.setStyleSheet("text-align: left;")
        return btn

    def _create_group(self, title):
        """Scaffolds the layout for a ribbon section (Buttons on top, Title on bottom)."""
        group_widget = QWidget()
        layout = QVBoxLayout(group_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Where the buttons will go
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(5)
        layout.addLayout(content_layout)
        
        # The small gray text at the bottom of the group
        lbl = QLabel(title)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #666666; font-size: 8pt; margin-top: 2px;")
        layout.addWidget(lbl)
        
        self.main_layout.addWidget(group_widget)
        return content_layout

    def _add_separator(self):
        """Draws a vertical line between ribbon groups."""
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #CCCCCC;")
        self.main_layout.addWidget(line)

    def _open_gbds_path(self, *subdirs):
        root_path = QgsSettings().value("gbds/root_path", "")
        if not root_path or not os.path.exists(root_path):
            self.iface.messageBar().pushWarning("Setup Required", "Please click 'Setup' in the Config section first.")
            return

        target_path = os.path.join(root_path, *subdirs)
        if os.path.exists(target_path):
            try:
                os.startfile(target_path)
            except Exception as e:
                self.iface.messageBar().pushCritical("Error", f"Could not open path:\n{e}")
        else:
            self.iface.messageBar().pushWarning("Not Found", f"Could not find:\n{target_path}")

    # --- UI BUILDING METHODS ---

    def _build_config_group(self):
        content = self._create_group("Config")
        vbox = QVBoxLayout()
        vbox.setSpacing(2)
        
        self.btn_setup = self._create_small_button("Setup", "AddInDesktop16.png", "Configure GBDS Root Folder")
        self.btn_setup.clicked.connect(lambda: self.plugin.dock_widget.run_setup())
        
        self.btn_about = self._create_small_button("About", "AddIn16.png", "About GBDS Tools")
        self.btn_about.clicked.connect(lambda: QMessageBox.information(self, "About", "GBDS QGIS Tools\nVersion 1.0"))
        
        vbox.addWidget(self.btn_setup)
        vbox.addWidget(self.btn_about)
        content.addLayout(vbox)

    def _build_browse_group(self):
        content = self._create_group("Browse")
        
        # Vertical stack for Maps, References, and Map Layers
        vbox = QVBoxLayout()
        vbox.setSpacing(2)
        vbox.setContentsMargins(0, 0, 0, 0)
        
        self.btn_maps = self._create_small_button("Maps", "GenericButtonOrange16.png")
        self.btn_maps.clicked.connect(lambda: self._open_gbds_path("Preconstructed_Maps"))
        
        self.btn_references = self._create_small_button("References", "References16.png")
        self.btn_references.clicked.connect(lambda: self._open_gbds_path("References", "Library"))
        
        self.btn_map_layers = self._create_small_button("Map Layers", "MapLayers16.png", checkable=True)
        self.btn_map_layers.clicked.connect(lambda checked: self.plugin.dock_widget.setVisible(checked))
        
        vbox.addWidget(self.btn_maps)
        vbox.addWidget(self.btn_references)
        vbox.addWidget(self.btn_map_layers)
        
        # Large button for Figures
        self.btn_figures = self._create_large_button("Figures", "FigureGallery32.png")
        self.btn_figures.clicked.connect(lambda: self._open_gbds_path("Documentation", "Figures"))
        
        content.addLayout(vbox)
        content.addWidget(self.btn_figures)

    def _build_tools_group(self):
        content = self._create_group("Tools")
        
        self.btn_well = self._create_large_button("Well", "Well32.png", checkable=True)
        self.btn_las = self._create_large_button("LAS", "Las32.png", checkable=True)
        self.btn_cross = self._create_large_button("Cross\nSection", "CrossSection32.png", checkable=True)
        self.btn_zircon = self._create_large_button("Zircon", "Zircon32.png", checkable=True)
        self.btn_reference = self._create_large_button("Reference", "SelectRef32.png", checkable=True)
        
        self.btn_explore = self._create_large_button("Explore", "GenericButtonBlue32.png")
        self.btn_explore.clicked.connect(lambda: self.iface.mapCanvas().unsetMapTool(self.iface.mapCanvas().mapTool()))

        content.addWidget(self.btn_well)
        content.addWidget(self.btn_las)
        content.addWidget(self.btn_cross)
        content.addWidget(self.btn_zircon)
        content.addWidget(self.btn_reference)
        content.addWidget(self.btn_explore)

    def _build_help_group(self):
        content = self._create_group("Help")
        vbox = QVBoxLayout()
        vbox.setSpacing(2)
        
        self.btn_guide = self._create_small_button("User Guide", "GenericButtonPurple16.png")
        self.btn_guide.clicked.connect(lambda: self._open_gbds_path("Documentation", "GBDS_User_Guide.pdf"))
        
        self.btn_tutorial = self._create_small_button("Tutorial", "GenericButtonBlue16.png")
        self.btn_tutorial.clicked.connect(lambda: self._open_gbds_path("Documentation", "Workshop.pdf"))
        
        self.btn_support = self._create_small_button("Support", "GenericButtonRed16.png")
        self.btn_support.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("mailto:GBDS@ig.utexas.edu")))
        
        vbox.addWidget(self.btn_guide)
        vbox.addWidget(self.btn_tutorial)
        vbox.addWidget(self.btn_support)
        content.addLayout(vbox)