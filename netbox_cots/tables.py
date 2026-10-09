import django_tables2 as tables
from netbox.tables import NetBoxTable
from .models import Application, SoftwareVersion, Installation


class ApplicationTable(NetBoxTable):
    name = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = Application
        fields = ("pk", "id", "name", "slug", "publisher", "description", "actions")
        default_columns = ("name", "slug", "publisher", "description", "actions")


class SoftwareVersionTable(NetBoxTable):
    application = tables.Column(linkify=True)
    version = tables.Column(linkify=True)

    class Meta(NetBoxTable.Meta):
        model = SoftwareVersion
        fields = ("pk", "id", "application", "version", "actions")
        default_columns = ("application", "version", "actions")


class InstallationTable(NetBoxTable):
    application = tables.Column(linkify=True)
    software_version = tables.Column(linkify=True, verbose_name="COTS / version")
    device = tables.Column(linkify=True, verbose_name="Machine physique")
    virtual_machine = tables.Column(linkify=True, verbose_name="Machine virtuelle")

    class Meta(NetBoxTable.Meta):
        model = Installation
        fields = ("pk", "id", "application", "software_version", "device", "virtual_machine", "notes", "actions")
        default_columns = ("software_version", "device", "virtual_machine", "notes", "actions")
