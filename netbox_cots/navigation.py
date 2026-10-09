from netbox.plugins import PluginMenu, PluginMenuItem

menu = PluginMenu(label="COTS", icon_class="mdi mdi-apps", groups=(("Inventaire logiciel", (
    PluginMenuItem(link="plugins:netbox_cots:application_list", link_text="COTS", permissions=["netbox_cots.view_application"]),
    PluginMenuItem(link="plugins:netbox_cots:softwareversion_list", link_text="Versions", permissions=["netbox_cots.view_softwareversion"]),
    PluginMenuItem(link="plugins:netbox_cots:roleassignment_list", link_text="Affectations aux rôles", permissions=["netbox_cots.view_roleassignment"]),
    PluginMenuItem(link="plugins:netbox_cots:installation_list", link_text="Anciennes installations", permissions=["netbox_cots.view_installation"]),
    PluginMenuItem(link="plugins:netbox_cots:convert_legacy", link_text="Reprendre les anciennes installations", staff_only=True, auth_required=True),
    PluginMenuItem(link="plugins:netbox_cots:csv_import", link_text="Import CSV", staff_only=True, auth_required=True),
    PluginMenuItem(link="plugins:netbox_cots:purge_installations", link_text="Vider les affectations", staff_only=True, auth_required=True),
)),))
