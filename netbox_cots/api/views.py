from netbox.api.viewsets import NetBoxModelViewSet, NetBoxReadOnlyModelViewSet
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from django.db.models import Value, CharField
from django.urls import reverse
from dcim.models import Device, DeviceRole
from virtualization.models import VirtualMachine
from ..models import Application, SoftwareVersion, Installation, RoleAssignment
from ..filtersets import ApplicationFilterSet, SoftwareVersionFilterSet, InstallationFilterSet, RoleAssignmentFilterSet
from .serializers import ApplicationSerializer, SoftwareVersionSerializer, InstallationSerializer, RoleAssignmentSerializer


class ApplicationViewSet(NetBoxModelViewSet):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    filterset_class = ApplicationFilterSet


class SoftwareVersionViewSet(NetBoxModelViewSet):
    queryset = SoftwareVersion.objects.select_related("application")
    serializer_class = SoftwareVersionSerializer
    filterset_class = SoftwareVersionFilterSet


class InstallationViewSet(NetBoxReadOnlyModelViewSet):
    queryset = Installation.objects.select_related("application", "software_version__application", "device__primary_ip4", "device__primary_ip6", "virtual_machine__primary_ip4", "virtual_machine__primary_ip6")
    serializer_class = InstallationSerializer
    filterset_class = InstallationFilterSet


def machines_for_assignments(assignments, user):
    """Query both machine types without materializing all targets in Python."""
    visible_roles = DeviceRole.objects.restrict(user, "view").values("pk")
    roles = assignments.filter(role_id__in=visible_roles).order_by().values("role_id")
    devices = Device.objects.restrict(user, "view").filter(role_id__in=roles).order_by().annotate(type=Value("device", output_field=CharField())).values("type", "id", "name", "role_id")
    vms = VirtualMachine.objects.restrict(user, "view").filter(role_id__in=roles).order_by().annotate(type=Value("virtual_machine", output_field=CharField())).values("type", "id", "name", "role_id")
    return devices.union(vms).order_by("type", "id")


class RoleAssignmentViewSet(NetBoxModelViewSet):
    queryset = RoleAssignment.objects.select_related("role", "application", "software_version__application")
    serializer_class = RoleAssignmentSerializer
    filterset_class = RoleAssignmentFilterSet

    @action(detail=False, methods=["get"])
    def machines(self, request):
        params = request.query_params
        if not params.get("application", "").strip():
            raise ValidationError("Fournir application (slug exact du COTS). Les filtres role, role_id et version sont facultatifs.")
        queryset = self.filter_queryset(self.get_queryset())
        targets = machines_for_assignments(queryset, request.user)
        page = self.paginate_queryset(targets)
        rows = page if page is not None else targets
        data = []
        for row in rows:
            url_name = "dcim-api:device-detail" if row["type"] == "device" else "virtualization-api:virtualmachine-detail"
            data.append({**row, "url": request.build_absolute_uri(reverse(url_name, args=[row["id"]]))})
        return self.get_paginated_response(data) if page is not None else Response(data)
