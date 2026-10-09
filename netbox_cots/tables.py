import django_tables2 as tables
from netbox.tables import NetBoxTable, columns
from .models import Application, SoftwareVersion, Installation


class ApplicationTable(NetBoxTable):
    name = tables.Column(linkify=True)
    tags = columns.TagColumn(url_name="plugins:netbox_cots:application_list")

    class Meta(NetBoxTable.Meta):
        model = Application
        fields = ("pk", "id", "name", "slug", "publisher", "description", "tags", "actions")
        default_columns = ("name", "slug", "publisher", "description", "tags", "actions")


class SoftwareVersionTable(NetBoxTable):
    application = tables.Column(linkify=True)
    version = tables.Column(linkify=True)
    tags = columns.TagColumn(url_name="plugins:netbox_cots:softwareversion_list")

    class Meta(NetBoxTable.Meta):
        model = SoftwareVersion
        fields = ("pk", "id", "application", "version", "tags", "actions")
        default_columns = ("application", "version", "tags", "actions")


class InstallationTable(NetBoxTable):
    application = tables.Column(linkify=True)
    software_version = tables.Column(linkify=True, verbose_name="COTS / version")
    device = tables.Column(linkify=True, verbose_name="Machine physique")
    virtual_machine = tables.Column(linkify=True, verbose_name="Machine virtuelle")
    tags = columns.TagColumn(url_name="plugins:netbox_cots:installation_list")

    class Meta(NetBoxTable.Meta):
        model = Installation
        fields = ("pk", "id", "application", "software_version", "device", "virtual_machine", "notes", "tags", "actions")
        default_columns = ("software_version", "device", "virtual_machine", "notes", "tags", "actions")
