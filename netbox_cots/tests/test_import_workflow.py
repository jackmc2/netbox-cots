from types import SimpleNamespace
from unittest.mock import patch

from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, SimpleTestCase, override_settings

from netbox_cots.csv_parser import ImportFailure
from netbox_cots.views import CSVImportView


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
                   PLUGINS_CONFIG={"netbox_cots": {"max_import_rows": 10000, "max_import_bytes": 5000000}})
class ImportWorkflowTests(SimpleTestCase):
    csv = "machine_type,machine,cots,version\ndevice,PC-001,Notepad++,8.8\n"

    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()
        self.importer = patch("netbox_cots.views.import_csv").start()
        self.importer.return_value = {"dry_run": True, "rows": 1}
        patch("netbox_cots.views.render", side_effect=lambda request, template, context: context).start()
        self.addCleanup(patch.stopall)

    def post(self, data, user_id=1, superuser=True):
        request = self.factory.post("/plugins/cots/import/", data)
        request.user = SimpleNamespace(pk=user_id, is_authenticated=True, is_superuser=superuser)
        return CSVImportView.as_view()(request)

    def preview(self):
        return self.post({"file": SimpleUploadedFile("inventory.csv", self.csv.encode())})

    def test_upload_then_apply_without_file(self):
        preview = self.preview()
        token = preview["preview_token"]
        self.importer.assert_called_once_with(self.csv, dry_run=True, max_rows=10000)
        self.assertNotIn("dry_run", preview["form"].fields)
        self.importer.return_value = {"dry_run": False, "rows": 1}
        applied = self.post({"action": "apply", "preview_token": token})
        self.importer.assert_called_with(self.csv, dry_run=False, max_rows=10000)
        self.assertFalse(applied["result"]["dry_run"])
        self.assertIsNone(applied["preview_token"])
        self.assertIsNone(cache.get("netbox_cots:preview:" + token))
        self.importer.reset_mock()
        self.assertIn("error", self.post({"action": "apply", "preview_token": token}))
        self.importer.assert_not_called()

    def test_pasted_text_always_simulates(self):
        result = self.post({"csv_text": self.csv, "dry_run": "false"})
        self.assertTrue(result["preview_token"])
        self.importer.assert_called_once_with(self.csv.strip(), dry_run=True, max_rows=10000)

    def test_failed_simulation_cannot_be_applied(self):
        self.importer.side_effect = ImportFailure("Machine inconnue")
        result = self.preview()
        self.assertIsNone(result["preview_token"])
        self.assertIn("Machine inconnue", str(result["form"].errors))

    def test_other_user_cannot_apply(self):
        token = self.preview()["preview_token"]
        self.importer.reset_mock()
        self.assertIn("error", self.post({"action": "apply", "preview_token": token}, user_id=2))
        self.importer.assert_not_called()

    def test_expired_and_tampered_token(self):
        token = self.preview()["preview_token"]
        cache.delete("netbox_cots:preview:" + token)
        self.importer.reset_mock()
        for invalid in (token, "bad", "x" * 43):
            self.assertIn("error", self.post({"action": "apply", "preview_token": invalid}))
        self.importer.assert_not_called()

    def test_concurrent_apply_is_rejected(self):
        token = self.preview()["preview_token"]
        cache.set("netbox_cots:preview:" + token + ":applying", True)
        self.importer.reset_mock()
        result = self.post({"action": "apply", "preview_token": token})
        self.assertIn("déjà en cours", result["error"])
        self.importer.assert_not_called()

    def test_apply_revalidates_and_keeps_csv_on_conflict(self):
        token = self.preview()["preview_token"]
        self.importer.side_effect = ImportFailure("Version en conflit")
        result = self.post({"action": "apply", "preview_token": token, "csv_text": "tampered"})
        self.importer.assert_called_with(self.csv, dry_run=False, max_rows=10000)
        self.assertEqual(result["error"], "Version en conflit")
        self.assertEqual(result["preview_token"], token)
        self.assertIsNone(cache.get("netbox_cots:preview:" + token + ":applying"))

    def test_non_superuser_cannot_apply(self):
        with self.assertRaises(PermissionDenied):
            self.post({"action": "apply", "preview_token": "x" * 43}, superuser=False)

    @override_settings(PLUGINS_CONFIG={"netbox_cots": {"max_import_rows": 10, "max_import_bytes": 3}})
    def test_size_limit_rejects_upload(self):
        result = self.preview()
        self.assertIsNone(result["preview_token"])
        self.importer.assert_not_called()
