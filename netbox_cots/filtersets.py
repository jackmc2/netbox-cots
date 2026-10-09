import django_filters
from django.db.models import Q
from netbox.filtersets import NetBoxModelFilterSet
from .models import Application, SoftwareVersion, Installation, RoleAssignment


class ApplicationFilterSet(NetBoxModelFilterSet):
    class Meta:
        model = Application
        fields = ("id", "name", "slug", "publisher")

    def search(self, queryset, name, value):
        return queryset.filter(Q(name__icontains=value) | Q(slug__icontains=value) | Q(publisher__icontains=value))


class SoftwareVersionFilterSet(NetBoxModelFilterSet):
    application_id = django_filters.NumberFilter(field_name="application_id")
    application = django_filters.CharFilter(field_name="application__slug")

    class Meta:
        model = SoftwareVersion
        fields = ("id", "version")

    def search(self, queryset, name, value):
        return queryset.filter(Q(application__name__icontains=value) | Q(version__icontains=value))


class InstallationFilterSet(NetBoxModelFilterSet):
    application_id = django_filters.NumberFilter(field_name="application_id")
    application = django_filters.CharFilter(field_name="application__slug")
    software_version_id = django_filters.NumberFilter(field_name="software_version_id")
    version = django_filters.CharFilter(field_name="software_version__version")
    device_id = django_filters.NumberFilter(field_name="device_id")
    virtual_machine_id = django_filters.NumberFilter(field_name="virtual_machine_id")
    device = django_filters.CharFilter(field_name="device__name")
    virtual_machine = django_filters.CharFilter(field_name="virtual_machine__name")

    class Meta:
        model = Installation
        fields = ("id",)

    def search(self, queryset, name, value):
        return queryset.filter(Q(application__name__icontains=value) | Q(software_version__version__icontains=value) | Q(device__name__icontains=value) | Q(virtual_machine__name__icontains=value))


class RoleAssignmentFilterSet(NetBoxModelFilterSet):
    role_id = django_filters.NumberFilter(field_name="role_id")
    role = django_filters.CharFilter(field_name="role__slug")
    application_id = django_filters.NumberFilter(field_name="application_id")
    application = django_filters.CharFilter(field_name="application__slug")
    software_version_id = django_filters.NumberFilter(field_name="software_version_id")
    version = django_filters.CharFilter(field_name="software_version__version")

    class Meta:
        model = RoleAssignment
        fields = ("id",)

    def search(self, queryset, name, value):
        return queryset.filter(Q(role__name__icontains=value) | Q(application__name__icontains=value) | Q(software_version__version__icontains=value))
