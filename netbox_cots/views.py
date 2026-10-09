import secrets

from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.views import View
from netbox.views import generic
from netbox.object_actions import AddObject, BulkExport
from dcim.models import Device
from virtualization.models import VirtualMachine
from utilities.views import register_model_view, ViewTab

from . import forms, tables, filtersets
from .csv_parser import ImportFailure
from .importer import import_csv
from .models import Application, SoftwareVersion, Installation


class ApplicationListView(generic.ObjectListView):
    queryset = Application.objects.all()
    table = tables.ApplicationTable
    filterset = filtersets.ApplicationFilterSet
    filterset_form = forms.ApplicationFilterForm
    actions = (AddObject, BulkExport)


class ApplicationView(generic.ObjectView):
    queryset = Application.objects.all()
    template_name = "netbox_cots/application.html"

    def get_extra_context(self, request, instance):
        return {"versions": instance.versions.restrict(request.user, "view")}


class ApplicationEditView(generic.ObjectEditView):
    queryset = Application.objects.all()
    form = forms.ApplicationForm


class ApplicationDeleteView(generic.ObjectDeleteView):
    queryset = Application.objects.all()


class SoftwareVersionListView(generic.ObjectListView):
    queryset = SoftwareVersion.objects.select_related("application")
    table = tables.SoftwareVersionTable
    filterset = filtersets.SoftwareVersionFilterSet
    filterset_form = forms.SoftwareVersionFilterForm
    actions = (AddObject, BulkExport)


class SoftwareVersionView(generic.ObjectView):
    queryset = SoftwareVersion.objects.select_related("application")
    template_name = "netbox_cots/softwareversion.html"

    def get_extra_context(self, request, instance):
        queryset = instance.installations.restrict(request.user, "view").select_related("device", "virtual_machine", "software_version", "application")
        return {"installation_count": queryset.count(), "installations": queryset[:100]}


class SoftwareVersionEditView(generic.ObjectEditView):
    queryset = SoftwareVersion.objects.all()
    form = forms.SoftwareVersionForm


class SoftwareVersionDeleteView(generic.ObjectDeleteView):
    queryset = SoftwareVersion.objects.all()


class InstallationListView(generic.ObjectListView):
    queryset = Installation.objects.select_related("application", "software_version", "device", "virtual_machine")
    table = tables.InstallationTable
    filterset = filtersets.InstallationFilterSet
    filterset_form = forms.InstallationFilterForm
    actions = (AddObject, BulkExport)


class InstallationView(generic.ObjectView):
    queryset = Installation.objects.select_related("application", "software_version", "device", "virtual_machine")
    template_name = "netbox_cots/installation.html"


class InstallationEditView(generic.ObjectEditView):
    queryset = Installation.objects.all()
    form = forms.InstallationForm


class InstallationDeleteView(generic.ObjectDeleteView):
    queryset = Installation.objects.all()


class MachineCOTSView(generic.ObjectChildrenView):
    child_model = Installation
    table = tables.InstallationTable
    filterset = filtersets.InstallationFilterSet
    filterset_form = forms.InstallationFilterForm
    actions = ()
    tab = ViewTab(label="COTS", permission="netbox_cots.view_installation", weight=900)

    def get_children(self, request, parent):
        return parent.cots_installations.restrict(request.user, "view").select_related("application", "software_version", "device", "virtual_machine")


@register_model_view(Device, "cots", path="cots")
class DeviceCOTSView(MachineCOTSView):
    queryset = Device.objects.all()
    template_name = "netbox_cots/device_cots.html"


@register_model_view(VirtualMachine, "cots", path="cots")
class VirtualMachineCOTSView(MachineCOTSView):
    queryset = VirtualMachine.objects.all()
    template_name = "netbox_cots/vm_cots.html"


class CSVImportView(LoginRequiredMixin, View):
    """Bulk import deliberately limited to superusers in v0.1.

    Native object permissions still apply to the ordinary UI and REST endpoints.
    This avoids circumventing restricted add/change permissions during upserts.
    """
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_superuser:
            raise PermissionDenied("L'import CSV est réservé aux superutilisateurs.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, "netbox_cots/import.html", {"form": forms.CSVImportForm()})

    preview_timeout = 30 * 60

    def post(self, request):
        if request.POST.get("action") == "apply":
            return self.apply_preview(request)
        form = forms.CSVImportForm(request.POST, request.FILES)
        result = None
        preview_token = None
        if form.is_valid():
            config = settings.PLUGINS_CONFIG["netbox_cots"]
            try:
                upload = form.cleaned_data.get("file")
                if upload:
                    if upload.size > config["max_import_bytes"]:
                        raise ImportFailure("Fichier trop volumineux.")
                    text = upload.read().decode("utf-8-sig")
                else:
                    text = form.cleaned_data["csv_text"]
                if len(text.encode("utf-8")) > config["max_import_bytes"]:
                    raise ImportFailure("CSV trop volumineux.")
                result = import_csv(text, dry_run=True, max_rows=config["max_import_rows"])
                preview_token = secrets.token_urlsafe(32)
                cache.set("netbox_cots:preview:" + preview_token,
                          {"user_id": request.user.pk, "text": text}, self.preview_timeout)
            except (ImportFailure, UnicodeDecodeError) as exc:
                form.add_error(None, str(exc))
        return render(request, "netbox_cots/import.html", {
            "form": form, "result": result, "preview_token": preview_token,
        })

    def apply_preview(self, request):
        form = forms.CSVImportForm()
        token = request.POST.get("preview_token", "")
        key = "netbox_cots:preview:" + token
        pending = cache.get(key) if len(token) == 43 else None
        if not pending or pending["user_id"] != request.user.pk:
            return render(request, "netbox_cots/import.html", {
                "form": form, "error": "Simulation expirée ou indisponible. Relancer l’analyse du CSV.",
            })
        lock_key = key + ":applying"
        if not cache.add(lock_key, True, timeout=self.preview_timeout):
            return render(request, "netbox_cots/import.html", {
                "form": form, "error": "Cette intégration est déjà en cours.",
            })
        result = None
        retry_token = token
        error = None
        try:
            config = settings.PLUGINS_CONFIG["netbox_cots"]
            if len(pending["text"].encode("utf-8")) > config["max_import_bytes"]:
                raise ImportFailure("CSV trop volumineux.")
            # Revalidate against the current database; never trust the preview counts.
            result = import_csv(pending["text"], dry_run=False, max_rows=config["max_import_rows"])
            cache.delete(key)
            retry_token = None
        except ImportFailure as exc:
            error = str(exc)
        finally:
            cache.delete(lock_key)
        return render(request, "netbox_cots/import.html", {
            "form": form, "result": result, "preview_token": retry_token, "error": error,
        })
