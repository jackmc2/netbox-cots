from rest_framework import serializers
from dcim.api.serializers import DeviceRoleSerializer, DeviceSerializer
from virtualization.api.serializers import VirtualMachineSerializer
from netbox.api.serializers import NetBoxModelSerializer
from ..models import Application, SoftwareVersion, Installation, RoleAssignment


COMMON = ("id", "url", "display", "created", "last_updated", "tags", "custom_fields")


class ApplicationSerializer(NetBoxModelSerializer):
    class Meta:
        model = Application
        fields = COMMON + ("name", "slug", "publisher", "description")
        brief_fields = ("id", "url", "display", "name", "slug")


class SoftwareVersionSerializer(NetBoxModelSerializer):
    application = ApplicationSerializer(nested=True)

    class Meta:
        model = SoftwareVersion
        fields = COMMON + ("application", "version")
        brief_fields = ("id", "url", "display", "application", "version")


class InstallationSerializer(NetBoxModelSerializer):
    application = ApplicationSerializer(nested=True, read_only=True)
    software_version = SoftwareVersionSerializer(nested=True)
    device = DeviceSerializer(nested=True, required=False, allow_null=True)
    virtual_machine = VirtualMachineSerializer(nested=True, required=False, allow_null=True)
    machine = serializers.SerializerMethodField()

    def get_machine(self, obj):
        machine = obj.machine
        return {"type": "device" if obj.device_id else "virtual_machine", "id": machine.pk, "name": machine.name}

    class Meta:
        model = Installation
        fields = COMMON + ("application", "software_version", "device", "virtual_machine", "machine", "notes")
        brief_fields = ("id", "url", "display", "application", "software_version", "machine")


class RoleAssignmentSerializer(NetBoxModelSerializer):
    role = DeviceRoleSerializer(nested=True)
    application = ApplicationSerializer(nested=True, read_only=True)
    software_version = SoftwareVersionSerializer(nested=True)

    class Meta:
        model = RoleAssignment
        fields = COMMON + ("role", "application", "software_version", "notes")
        brief_fields = ("id", "url", "display", "role", "application", "software_version")
