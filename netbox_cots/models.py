from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from netbox.models import NetBoxModel


class Application(NetBoxModel):
    name = models.CharField("Nom", max_length=200)
    slug = models.SlugField("Identifiant", max_length=100, unique=True)
    publisher = models.CharField("Éditeur", max_length=200, blank=True)
    description = models.CharField("Description", max_length=200, blank=True)

    class Meta:
        ordering = ("name", "pk")
        verbose_name = "COTS"
        verbose_name_plural = "COTS"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("plugins:netbox_cots:application", args=[self.pk])


class SoftwareVersion(NetBoxModel):
    application = models.ForeignKey(Application, on_delete=models.PROTECT, related_name="versions")
    version = models.CharField("Version", max_length=100)

    class Meta:
        ordering = ("application__name", "version", "pk")
        constraints = [models.UniqueConstraint(fields=("application", "version"), name="cots_unique_version")]
        verbose_name = "Version"
        verbose_name_plural = "Versions"

    def __str__(self):
        return f"{self.application} / {self.version}"

    def clean(self):
        super().clean()
        if self.pk:
            original = type(self).objects.filter(pk=self.pk).values("application_id", "version").first()
            if original and self.installations.exists() and (
                original["application_id"] != self.application_id or original["version"] != self.version
            ):
                raise ValidationError("Une version utilisée est immuable : créer une nouvelle version et réaffecter les installations.")

    def get_absolute_url(self):
        return reverse("plugins:netbox_cots:softwareversion", args=[self.pk])


class Installation(NetBoxModel):
    # Denormalized FK enforces one application per machine in database constraints.
    # The value is always derived from software_version, never supplied by users.
    application = models.ForeignKey(Application, on_delete=models.PROTECT, related_name="installations", editable=False)
    software_version = models.ForeignKey(SoftwareVersion, on_delete=models.PROTECT, related_name="installations")
    device = models.ForeignKey("dcim.Device", on_delete=models.CASCADE, related_name="cots_installations", null=True, blank=True)
    virtual_machine = models.ForeignKey("virtualization.VirtualMachine", on_delete=models.CASCADE, related_name="cots_installations", null=True, blank=True)
    notes = models.CharField("Notes", max_length=200, blank=True)

    class Meta:
        ordering = ("application__name", "pk")
        verbose_name = "Installation"
        verbose_name_plural = "Installations"
        constraints = [
            models.CheckConstraint(condition=(Q(device__isnull=False, virtual_machine__isnull=True) | Q(device__isnull=True, virtual_machine__isnull=False)), name="cots_exactly_one_machine"),
            models.UniqueConstraint(fields=("device", "application"), condition=Q(device__isnull=False), name="cots_unique_device_app"),
            models.UniqueConstraint(fields=("virtual_machine", "application"), condition=Q(virtual_machine__isnull=False), name="cots_unique_vm_app"),
        ]

    @property
    def machine(self):
        return self.device or self.virtual_machine

    def __str__(self):
        return f"{self.machine} : {self.software_version}"

    def full_clean(self, *args, **kwargs):
        if self.software_version_id:
            self.application_id = self.software_version.application_id
        return super().full_clean(*args, **kwargs)

    def clean(self):
        super().clean()
        if bool(self.device_id) == bool(self.virtual_machine_id):
            raise ValidationError("Choisir exactement une machine physique ou une VM.")
        if self.software_version_id:
            self.application_id = self.software_version.application_id

    def save(self, *args, **kwargs):
        self.application_id = self.software_version.application_id
        self.full_clean()
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"application"}
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("plugins:netbox_cots:installation", args=[self.pk])
