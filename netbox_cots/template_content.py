from netbox.plugins import PluginTemplateExtension
from .models import RoleAssignment


class MachineCOTS(PluginTemplateExtension):
    models = ["dcim.device", "virtualization.virtualmachine"]

    def full_width_page(self):
        request = self.context["request"]
        if not request.user.has_perm("netbox_cots.view_roleassignment"):
            return ""
        machine = self.context["object"]
        queryset = RoleAssignment.objects.restrict(request.user, "view").filter(role_id=machine.role_id).select_related("role", "application", "software_version")
        return self.render("netbox_cots/machine_panel.html", {"assignments": queryset[:100], "assignment_count": queryset.count(), "role": machine.role})


template_extensions = [MachineCOTS]
