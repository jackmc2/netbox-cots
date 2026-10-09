from netbox.api.viewsets import NetBoxModelViewSet
from ..models import Application, SoftwareVersion, Installation
from ..filtersets import ApplicationFilterSet, SoftwareVersionFilterSet, InstallationFilterSet
from .serializers import ApplicationSerializer, SoftwareVersionSerializer, InstallationSerializer


class ApplicationViewSet(NetBoxModelViewSet):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    filterset_class = ApplicationFilterSet


class SoftwareVersionViewSet(NetBoxModelViewSet):
    queryset = SoftwareVersion.objects.select_related("application")
    serializer_class = SoftwareVersionSerializer
    filterset_class = SoftwareVersionFilterSet


class InstallationViewSet(NetBoxModelViewSet):
    queryset = Installation.objects.select_related("application", "software_version__application", "device__primary_ip4", "device__primary_ip6", "virtual_machine__primary_ip4", "virtual_machine__primary_ip6")
    serializer_class = InstallationSerializer
    filterset_class = InstallationFilterSet
