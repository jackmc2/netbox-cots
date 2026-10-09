from netbox.plugins import PluginTemplateExtension
from .models import Installation


class MachineCOTS(PluginTemplateExtension):
    models = ["dcim.device", "virtualization.virtualmachine"]

    def full_width_page(self):
        request = self.context["request"]
        if not request.user.has_perm("netbox_cots.view_installation"):
            return ""
        machine = self.context["object"]
        target = "device" if machine._meta.label_lower == "dcim.device" else "virtual_machine"
        queryset = Installation.objects.restrict(request.user, "view").filter(**{target: machine}).select_related("application", "software_version")
        return self.render("netbox_cots/machine_panel.html", {"installations": queryset[:100], "installation_count": queryset.count(), "target_filter": target + "_id"})


template_extensions = [MachineCOTS]
