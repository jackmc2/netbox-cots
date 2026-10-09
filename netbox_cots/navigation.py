from netbox.plugins import PluginMenu, PluginMenuItem

menu = PluginMenu(label="COTS", icon_class="mdi mdi-apps", groups=(("Inventaire logiciel", (
    PluginMenuItem(link="plugins:netbox_cots:application_list", link_text="COTS", permissions=["netbox_cots.view_application"]),
    PluginMenuItem(link="plugins:netbox_cots:softwareversion_list", link_text="Versions", permissions=["netbox_cots.view_softwareversion"]),
    PluginMenuItem(link="plugins:netbox_cots:installation_list", link_text="Installations", permissions=["netbox_cots.view_installation"]),
    PluginMenuItem(link="plugins:netbox_cots:csv_import", link_text="Import CSV", staff_only=True, auth_required=True),
)),))
