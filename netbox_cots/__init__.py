from netbox.plugins import PluginConfig


class COTSConfig(PluginConfig):
    name = "netbox_cots"
    verbose_name = "Inventaire COTS"
    description = "Catalogue COTS, versions et installations sur machines et VM"
    version = "0.2.0"
    base_url = "cots"
    min_version = "4.4.0"
    max_version = "4.7.2"
    default_settings = {"max_import_rows": 10000, "max_import_bytes": 5 * 1024 * 1024}


config = COTSConfig
