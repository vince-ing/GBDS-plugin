def classFactory(iface):
    from .gbds_plugin import GBDSToolsPlugin
    return GBDSToolsPlugin(iface)