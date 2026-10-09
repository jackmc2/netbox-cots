from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site
from virtualization.models import VirtualMachine
from netbox.context import events_queue
from extras.models import Tag, TaggedItem
from django.contrib.contenttypes.models import ContentType

from netbox_cots.csv_parser import ImportFailure
from netbox_cots.importer import import_csv
from netbox_cots.models import Application, SoftwareVersion, Installation
from netbox_cots.filtersets import InstallationFilterSet
from netbox_cots.api.serializers import InstallationSerializer


class InventoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="COTS test", slug="cots-test")
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="Test PC", slug="test-pc")
        role = DeviceRole.objects.create(name="COTS test", slug="cots-test")
        site = Site.objects.create(name="COTS test", slug="cots-test")
        cls.device = Device.objects.create(name="PC-001", device_type=device_type, role=role, site=site)
        cls.vm = VirtualMachine.objects.create(name="VM-001")

    def csv(self, version="8.8"):
        return f"machine_type,machine,cots_slug,cots,version\ndevice,PC-001,notepadpp,Notepad++,{version}\nvirtual_machine,VM-001,notepadpp,Notepad++,{version}\n"

    def test_create_both_target_types(self):
        result = import_csv(self.csv(), dry_run=False)
        self.assertEqual(result["counts"]["applications_created"], 1)
        self.assertEqual(SoftwareVersion.objects.count(), 1)
        self.assertEqual(Installation.objects.count(), 2)

    def test_idempotent_reimport(self):
        import_csv(self.csv(), dry_run=False)
        result = import_csv(self.csv(), dry_run=False)
        self.assertEqual(result["counts"]["unchanged"], 2)
        self.assertEqual(Installation.objects.count(), 2)

    def test_update_and_keep_unmentioned_installations(self):
        import_csv(self.csv("8.7.9"), dry_run=False)
        before = Installation.objects.get(device=self.device)
        import_csv("machine_type,machine,cots_slug,cots,version\ndevice,PC-001,notepadpp,Notepad++,8.8\n", dry_run=False)
        before.refresh_from_db()
        self.assertEqual(before.software_version.version, "8.8")
        self.assertEqual(Installation.objects.get(virtual_machine=self.vm).software_version.version, "8.7.9")

    def test_dry_run_has_no_records_or_events(self):
        previous = events_queue.get().copy()
        result = import_csv(self.csv())
        self.assertEqual(result["counts"]["installations_created"], 2)
        self.assertEqual(Application.objects.count(), 0)
        self.assertEqual(events_queue.get(), previous)

    def test_missing_machine_rolls_back_everything(self):
        with self.assertRaises(ImportFailure):
            import_csv(self.csv() + "device,MISSING,java,Java,17\n", dry_run=False)
        self.assertEqual(Application.objects.count(), 0)

    def test_conflicting_rows_roll_back_created_records(self):
        with self.assertRaises(ImportFailure):
            import_csv(self.csv() + "device,PC-001,notepadpp,Notepad++,8.9\n", dry_run=False)
        self.assertEqual(Application.objects.count(), 0)

    def test_slug_collision_is_not_silently_merged(self):
        csv = "machine_type,machine,cots,version\ndevice,PC-001,C++,1\ndevice,PC-001,C#,1\n"
        with self.assertRaises(ImportFailure):
            import_csv(csv, dry_run=False)
        self.assertEqual(Application.objects.count(), 0)

    def test_repeated_same_row_is_ignored(self):
        csv = "machine_type,machine,cots,version\ndevice,PC-001,Java,17\ndevice,PC-001,Java,17\n"
        result = import_csv(csv, dry_run=False)
        self.assertEqual(result["counts"]["duplicates"], 1)
        self.assertEqual(Installation.objects.count(), 1)

    def test_machine_id_and_name_must_agree(self):
        csv = f"machine_type,machine_id,machine,cots,version\ndevice,{self.device.pk},OTHER,Java,17\n"
        with self.assertRaises(ImportFailure):
            import_csv(csv, dry_run=False)

    def test_unique_application_per_machine(self):
        import_csv(self.csv(), dry_run=False)
        app = Application.objects.get(slug="notepadpp")
        other = SoftwareVersion.objects.create(application=app, version="8.9")
        with self.assertRaises(ValidationError):
            Installation(device=self.device, software_version=other).full_clean()

    def test_exactly_one_target(self):
        app = Application.objects.create(name="Java", slug="java")
        version = SoftwareVersion.objects.create(application=app, version="17")
        for target in ({}, {"device": self.device, "virtual_machine": self.vm}):
            with self.subTest(target=target), self.assertRaises(ValidationError):
                Installation(software_version=version, **target).full_clean()

    def test_used_version_is_immutable(self):
        import_csv(self.csv(), dry_run=False)
        version = SoftwareVersion.objects.get(version="8.8")
        version.version = "8.9"
        with self.assertRaises(ValidationError):
            version.full_clean()

    def test_filter_application_and_version(self):
        import_csv(self.csv(), dry_run=False)
        filtered = InstallationFilterSet({"application": "notepadpp", "version": "8.8"}, queryset=Installation.objects.all())
        self.assertTrue(filtered.is_valid())
        self.assertEqual(filtered.qs.count(), 2)
        self.assertEqual(InstallationFilterSet({"version": "8.8.0"}, queryset=Installation.objects.all()).qs.count(), 0)

    def test_ui_and_api_urls(self):
        import_csv(self.csv(), dry_run=False)
        version = SoftwareVersion.objects.get(version="8.8")
        self.assertEqual(reverse("plugins-api:netbox_cots-api:softwareversion-detail", args=[version.pk]), f"/api/plugins/cots/versions/{version.pk}/")

    def test_api_create_and_update(self):
        application = Application.objects.create(name="Java", slug="java")
        first = SoftwareVersion.objects.create(application=application, version="17")
        second = SoftwareVersion.objects.create(application=application, version="21")
        serializer = InstallationSerializer(data={"software_version": first.pk, "device": self.device.pk}, context={"request": None})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        instance = serializer.save()
        self.assertEqual(instance.application_id, application.pk)
        update = InstallationSerializer(instance, data={"software_version": second.pk}, partial=True, context={"request": None})
        self.assertTrue(update.is_valid(), update.errors)
        instance = update.save()
        data = InstallationSerializer(instance, context={"request": None}).data
        self.assertEqual(data["machine"]["name"], "PC-001")
        self.assertEqual(data["software_version"]["version"], "21")

    def test_import_requires_superuser(self):
        from types import SimpleNamespace
        from django.core.exceptions import PermissionDenied
        from django.test import RequestFactory
        from netbox_cots.views import CSVImportView
        request = RequestFactory().post("/plugins/cots/import/")
        request.user = SimpleNamespace(is_authenticated=True, is_superuser=False)
        with self.assertRaises(PermissionDenied):
            CSVImportView.as_view()(request)

    def tag_csv(self,tags='Production|Windows',version='8.8'):
     return 'machine_type,machine,cots_slug,cots,version,tags\ndevice,PC-001,notepadpp,Notepad++,'+version+','+tags+'\n'
    def test_tag_preview_and_apply(self):
     r=import_csv(self.tag_csv())
     self.assertEqual(r['counts']['tags_created'],2)
     self.assertEqual({t['name'] for t in r['created_tags']},{'Production','Windows'})
     self.assertEqual(Tag.objects.count(),0)
     self.assertEqual(TaggedItem.objects.count(),0)
     import_csv(self.tag_csv(),dry_run=False)
     self.assertEqual(set(Installation.objects.get(device=self.device).tags.values_list('name',flat=True)),{'Production','Windows'})
     r=import_csv(self.tag_csv(),dry_run=False)
     self.assertEqual(r['counts']['tags_created'],0)
     self.assertEqual(r['counts']['tags_added'],0)
     self.assertEqual(r['counts']['unchanged'],1)
    def test_preserve_add_blank_and_omit(self):
     import_csv(self.tag_csv('Production'),dry_run=False)
     r=import_csv(self.tag_csv('Windows'),dry_run=False)
     self.assertEqual(r['counts']['installations_updated'],1)
     self.assertEqual(r['counts']['tags_added'],1)
     self.assertEqual(r['details'][0]['tags_after'],['Production','Windows'])
     import_csv(self.tag_csv(''),dry_run=False)
     import_csv('machine_type,machine,cots_slug,cots,version\ndevice,PC-001,notepadpp,Notepad++,8.8\n',dry_run=False)
     self.assertEqual(Installation.objects.get(device=self.device).tags.count(),2)
    def test_tag_reuse(self):
     Tag.objects.create(name='Production',slug='custom-production')
     r=import_csv(self.tag_csv('Production'),dry_run=False)
     self.assertEqual(r['counts']['tags_created'],0)
     self.assertEqual(Installation.objects.get(device=self.device).tags.get().slug,'custom-production')
    def test_tags_rollback_and_collision(self):
     with self.assertRaises(ImportFailure):
      import_csv(self.tag_csv('Production')+'device,PC-001,notepadpp,Notepad++,8.8,Other\n',dry_run=False)
     self.assertEqual(Tag.objects.count(),0)
     self.assertEqual(Installation.objects.count(),0)
     Tag.objects.create(name='Existing',slug='production')
     with self.assertRaises(ImportFailure):import_csv(self.tag_csv('Production'),dry_run=False)
     self.assertEqual(Tag.objects.count(),1)
    def test_restricted_tag(self):
     t=Tag.objects.create(name='Production',slug='production')
     ct=ContentType.objects.get_for_model(Device)
     t.object_types.add(ct)
     with self.assertRaises(ImportFailure):import_csv(self.tag_csv('Production'),dry_run=False)
     self.assertEqual(Installation.objects.count(),0)
