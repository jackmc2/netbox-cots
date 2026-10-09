from types import SimpleNamespace
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.db import transaction
from django.urls import reverse, NoReverseMatch
from django.contrib.contenttypes.models import ContentType
from dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site
from virtualization.models import VirtualMachine
from extras.models import Tag
from netbox.context import events_queue
from netbox_cots.csv_parser import ImportFailure
from netbox_cots.importer import import_csv
from netbox_cots.models import Application, SoftwareVersion, Installation, RoleAssignment
from netbox_cots.api.views import machines_for_assignments, RoleAssignmentViewSet, InstallationViewSet
from netbox_cots.api.serializers import RoleAssignmentSerializer
from netbox_cots.views import DeviceCOTSView
from netbox_cots.legacy import legacy_role_csv
from netbox_cots.tables import InheritedCOTSTable
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.permissions import AllowAny
user = SimpleNamespace(is_superuser=True, is_authenticated=True, is_active=True, has_perm=lambda *args: True, has_perms=lambda *args: True)

class InventoryTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name='COTS test', slug='cots-test')
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model='Test PC', slug='test-pc')
        cls.role = DeviceRole.objects.create(name='Poste', slug='poste', vm_role=True)
        cls.other_role = DeviceRole.objects.create(name='Serveur', slug='serveur', vm_role=True)
        site = Site.objects.create(name='COTS test', slug='cots-test')
        cls.device = Device.objects.create(name='PC-001', device_type=device_type, role=cls.role, site=site)
        cls.vm = VirtualMachine.objects.create(name='VM-001', role=cls.role)

    def csv(self, version='8.8', tags='Production'):
        return 'role,cots_slug,cots,version,tags\nposte,notepadpp,Notepad++,' + version + ',' + tags + '\n'

    def test_create_shared_and_preview_tags(self):
        r = import_csv(self.csv())
        self.assertEqual(r['counts']['assignments_created'], 1)
        self.assertEqual(r['created_tags'][0]['name'], 'Production')
        self.assertEqual(RoleAssignment.objects.count(), 0)
        self.assertEqual(Tag.objects.count(), 0)
        import_csv(self.csv(), dry_run=False)
        self.assertEqual(RoleAssignment.objects.get().tags.get().name, 'Production')
        self.assertEqual(Installation.objects.count(), 0)
        rows = list(machines_for_assignments(RoleAssignment.objects.all(), user))
        self.assertEqual({(x['type'], x['name']) for x in rows}, {('device', 'PC-001'), ('virtual_machine', 'VM-001')})

    def test_idempotent_and_update(self):
        import_csv(self.csv(), dry_run=False)
        pk = RoleAssignment.objects.get().pk
        r = import_csv(self.csv(), dry_run=False)
        self.assertEqual(r['counts']['unchanged'], 1)
        import_csv(self.csv('8.9', 'Windows'), dry_run=False)
        a = RoleAssignment.objects.get()
        self.assertEqual(a.pk, pk)
        self.assertEqual(a.software_version.version, '8.9')
        self.assertEqual(a.tags.count(), 2)

    def test_tags_preserved_without_column(self):
        import_csv(self.csv(), dry_run=False)
        import_csv('role,cots,version,cots_slug\nposte,Notepad++,8.8,notepadpp\n', dry_run=False)
        self.assertEqual(RoleAssignment.objects.get().tags.count(), 1)

    def test_conflicts_rollback(self):
        with self.assertRaises(ImportFailure):
            import_csv(self.csv() + 'poste,notepadpp,Notepad++,8.9,Other\n', dry_run=False)
        self.assertEqual(RoleAssignment.objects.count(), 0)
        self.assertEqual(Tag.objects.count(), 0)

    def test_unknown_and_id_mismatch(self):
        with self.assertRaises(ImportFailure):
            import_csv('role,cots,version\nmissing,Java,17\n', dry_run=False)
        with self.assertRaises(ImportFailure):
            import_csv('role_id,role,cots,version\n1,serveur,Java,17\n', dry_run=False)

    def test_duplicate_row(self):
        r = import_csv(self.csv() + 'poste,notepadpp,Notepad++,8.8,Production\n', dry_run=False)
        self.assertEqual(r['counts']['duplicates'], 1)

    def test_unique_role_app(self):
        import_csv(self.csv(), dry_run=False)
        a = RoleAssignment.objects.get()
        with self.assertRaises(ValidationError):
            RoleAssignment(role=self.role, software_version=a.software_version).save()

    def test_used_version_immutable(self):
        import_csv(self.csv(), dry_run=False)
        sv = SoftwareVersion.objects.get()
        sv.version = 'X'
        with self.assertRaises(ValidationError):
            sv.full_clean()

    def test_role_change_inheritance(self):
        import_csv(self.csv(), dry_run=False)
        self.device.role_id = self.other_role.pk
        self.device.save_base(raw=True)
        self.assertEqual(list(DeviceCOTSView().get_children(SimpleNamespace(user=user), self.device)), [])
        self.device.role_id = self.role.pk
        self.device.save_base(raw=True)
        self.assertEqual(DeviceCOTSView().get_children(SimpleNamespace(user=user), self.device).count(), 1)

    def test_readonly_tables_and_legacy_endpoints(self):
        self.assertNotIn('actions', InheritedCOTSTable.Meta.fields)
        self.assertFalse(hasattr(InstallationViewSet, 'create'))
        with self.assertRaises(NoReverseMatch):
            reverse('plugins:netbox_cots:installation_edit', args=[1])
        self.assertTrue(reverse('dcim:devicerole_cots', args=[1]))

    def test_serializer_write(self):
        app = Application.objects.create(name='Java', slug='java')
        sv = SoftwareVersion.objects.create(application=app, version='17')
        s = RoleAssignmentSerializer(data={'role': self.role.pk, 'software_version': sv.pk}, context={'request': None})
        self.assertTrue(s.is_valid(), s.errors)
        a = s.save()
        self.assertEqual(a.application_id, app.pk)

    def test_query_role_cots_version(self):
        import_csv(self.csv(), dry_run=False)
        from netbox_cots.filtersets import RoleAssignmentFilterSet
        qs = RoleAssignmentFilterSet({'role': 'poste', 'application': 'notepadpp', 'version': '8.8'}, queryset=RoleAssignment.objects.all()).qs
        self.assertEqual(len(list(machines_for_assignments(qs, user))), 2)
        qs = RoleAssignmentFilterSet({'role': 'serveur', 'application': 'notepadpp', 'version': '8.8'}, queryset=RoleAssignment.objects.all()).qs
        self.assertEqual(list(machines_for_assignments(qs, user)), [])

    def test_machine_permissions(self):
        import_csv(self.csv(), dry_run=False)
        reader = SimpleNamespace(is_superuser=False, is_authenticated=True, is_active=True, get_all_permissions=lambda: set())
        self.assertEqual(list(machines_for_assignments(RoleAssignment.objects.all(), reader)), [])

    def test_paginated_api(self):
        import_csv(self.csv(), dry_run=False)
        req = APIRequestFactory().get('/api/plugins/cots/role-assignments/machines/', {'role': 'poste', 'application': 'notepadpp', 'version': '8.8', 'limit': 1})
        force_authenticate(req, user=user)
        response = RoleAssignmentViewSet.as_view({'get': 'machines'}, permission_classes=[AllowAny])(req)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIsNotNone(response.data['next'])

    def test_api_application_optional_filters(self):
        import_csv(self.csv(), dry_run=False)
        import_csv('role,cots_slug,cots,version\nserveur,notepadpp,Notepad++,8.9\n', dry_run=False)
        machine = Device(name='PC-002', site_id=self.device.site_id, role_id=self.other_role.pk, device_type_id=self.device.device_type_id)
        machine.save()
    
        def query(**params):
            req = APIRequestFactory().get('/api/plugins/cots/role-assignments/machines/', params)
            force_authenticate(req, user=user)
            response = RoleAssignmentViewSet.as_view({'get': 'machines'}, permission_classes=[AllowAny])(req)
            self.assertEqual(response.status_code, 200, response.data)
            return response.data
        all_rows = query(application='notepadpp')
        self.assertEqual(all_rows['count'], 3)
        self.assertEqual({row['name'] for row in all_rows['results']}, {'PC-001', 'VM-001', 'PC-002'})
        self.assertEqual(query(application='notepadpp', version='8.8')['count'], 2)
        self.assertEqual(query(application='notepadpp', role='serveur')['count'], 1)
        self.assertEqual(query(application='notepadpp', role_id=self.other_role.pk)['count'], 1)
        self.assertEqual(query(application='notepadpp', role='serveur', version='8.8')['count'], 0)
        self.assertEqual(query(application='unknown')['count'], 0)
        page = query(application='notepadpp', limit=1)
        self.assertEqual(page['count'], 3)
        self.assertIsNotNone(page['next'])
        from urllib.parse import urlsplit
        names = {page['results'][0]['name']}
        while page['next']:
            req = APIRequestFactory().get(urlsplit(page['next']).path + '?' + urlsplit(page['next']).query)
            force_authenticate(req, user=user)
            response = RoleAssignmentViewSet.as_view({'get': 'machines'}, permission_classes=[AllowAny])(req)
            self.assertEqual(response.status_code, 200, response.data)
            page = response.data
            names.update((row['name'] for row in page['results']))
        self.assertEqual(names, {'PC-001', 'VM-001', 'PC-002'})

    def test_removed_legacy_ui(self):
        for name in ('installation_list', 'installation', 'convert_legacy'):
            with self.assertRaises(NoReverseMatch):
                reverse('plugins:netbox_cots:' + name, args=[1] if name == 'installation' else None)
        from django.urls import resolve, Resolver404
        for path in ('/plugins/cots/installations/', '/plugins/cots/installations/1/', '/plugins/cots/convert-legacy/'):
            with self.assertRaises(Resolver404):
                resolve(path)
        from netbox_cots.navigation import menu
        links = [item.link for group in menu.groups for item in group.items]
        self.assertEqual(len(links), 5)
        self.assertIn('plugins:netbox_cots:csv_import', links)
        self.assertNotIn('plugins:netbox_cots:installation_list', links)
        self.assertNotIn('plugins:netbox_cots:convert_legacy', links)
        self.assertTrue(reverse('plugins-api:netbox_cots-api:installation-list'))

    def test_api_requires_application(self):
        req = APIRequestFactory().get('/api/plugins/cots/role-assignments/machines/', {'role': 'poste'})
        force_authenticate(req, user=user)
        response = RoleAssignmentViewSet.as_view({'get': 'machines'}, permission_classes=[AllowAny])(req)
        self.assertEqual(response.status_code, 400)

    def legacy(self, version='8.8', target=None):
        target = target or self.device
        app, _ = Application.objects.get_or_create(name='Notepad++', slug='notepadpp')
        sv, _ = SoftwareVersion.objects.get_or_create(application=app, version=version)
        return Installation.objects.create(software_version=sv, **{'device': target} if isinstance(target, Device) else {'virtual_machine': target})

    def test_legacy_conversion_keeps_archive(self):
        self.legacy()
        self.legacy(target=self.vm)
        text = legacy_role_csv()
        r = import_csv(text)
        self.assertEqual(r['counts']['assignments_created'], 1)
        self.assertEqual(Installation.objects.count(), 2)
        import_csv(text, dry_run=False)
        self.assertEqual(Installation.objects.count(), 2)

    def test_legacy_conflicting_versions(self):
        self.legacy()
        self.legacy('8.9', self.vm)
        with self.assertRaises(ImportFailure):
            legacy_role_csv()
        self.assertEqual(RoleAssignment.objects.count(), 0)

    def test_legacy_no_role(self):
        self.vm.role_id = None
        self.vm.save_base(raw=True)
        self.legacy(target=self.vm)
        with self.assertRaises(ImportFailure):
            legacy_role_csv()

    def test_legacy_existing_role_version_conflict(self):
        self.legacy()
        import_csv(self.csv('8.9'), dry_run=False)
        with self.assertRaises(ImportFailure):
            legacy_role_csv()

    def test_tag_type_restriction(self):
        t = Tag.objects.create(name='Production', slug='production')
        t.object_types.add(ContentType.objects.get_for_model(Installation))
        with self.assertRaises(ImportFailure):
            import_csv(self.csv(), dry_run=False)

    def test_events_restore(self):
        before = events_queue.get().copy()
        import_csv(self.csv())
        self.assertEqual(before, events_queue.get())
