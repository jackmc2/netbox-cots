from django import forms
from dcim.models import DeviceRole, Device
from virtualization.models import VirtualMachine
from netbox.forms import NetBoxModelForm, NetBoxModelFilterSetForm
from utilities.forms.fields import DynamicModelChoiceField, SlugField

from .models import Application, SoftwareVersion, Installation, RoleAssignment


class ApplicationForm(NetBoxModelForm):
    slug = SlugField()

    class Meta:
        model = Application
        fields = ("name", "slug", "publisher", "description", "tags")


class SoftwareVersionForm(NetBoxModelForm):
    application = DynamicModelChoiceField(queryset=Application.objects.all(), label="COTS")

    class Meta:
        model = SoftwareVersion
        fields = ("application", "version", "tags")


class InstallationForm(NetBoxModelForm):
    software_version = DynamicModelChoiceField(queryset=SoftwareVersion.objects.all(), label="COTS / version")
    device = DynamicModelChoiceField(queryset=Device.objects.all(), required=False, label="Machine physique")
    virtual_machine = DynamicModelChoiceField(queryset=VirtualMachine.objects.all(), required=False, label="Machine virtuelle")

    class Meta:
        model = Installation
        fields = ("software_version", "device", "virtual_machine", "notes", "tags")


class ApplicationFilterForm(NetBoxModelFilterSetForm):
    model = Application
    publisher = forms.CharField(required=False, label="Éditeur (exact)")


class SoftwareVersionFilterForm(NetBoxModelFilterSetForm):
    model = SoftwareVersion
    application_id = DynamicModelChoiceField(queryset=Application.objects.all(), required=False, label="COTS")
    version = forms.CharField(required=False, label="Version (exacte)")


class InstallationFilterForm(NetBoxModelFilterSetForm):
    model = Installation
    application_id = DynamicModelChoiceField(queryset=Application.objects.all(), required=False, label="COTS")
    version = forms.CharField(required=False, label="Version (exacte)")
    device_id = DynamicModelChoiceField(queryset=Device.objects.all(), required=False, label="Machine physique")
    virtual_machine_id = DynamicModelChoiceField(queryset=VirtualMachine.objects.all(), required=False, label="Machine virtuelle")


class CSVImportForm(forms.Form):
    file = forms.FileField(label="Fichier CSV UTF-8", required=False)
    csv_text = forms.CharField(label="Ou coller le CSV", required=False, widget=forms.Textarea(attrs={"rows": 9, "class": "form-control"}))

    def clean(self):
        data = super().clean()
        if bool(data.get("file")) == bool(data.get("csv_text")):
            raise forms.ValidationError("Fournir soit un fichier, soit du texte CSV.")
        return data


class RoleAssignmentForm(NetBoxModelForm):
    role = DynamicModelChoiceField(queryset=DeviceRole.objects.all(), label="Rôle d’appareil")
    software_version = DynamicModelChoiceField(queryset=SoftwareVersion.objects.all(), label="COTS / version")

    class Meta:
        model = RoleAssignment
        fields = ("role", "software_version", "notes", "tags")


class RoleAssignmentFilterForm(NetBoxModelFilterSetForm):
    model = RoleAssignment
    role_id = DynamicModelChoiceField(queryset=DeviceRole.objects.all(), required=False, label="Rôle")
    application_id = DynamicModelChoiceField(queryset=Application.objects.all(), required=False, label="COTS")
    version = forms.CharField(required=False, label="Version (exacte)")
