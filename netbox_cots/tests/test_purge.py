from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, SimpleTestCase

from netbox_cots.views import PurgeInstallationsView


class PurgeInstallationsViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        patch("netbox_cots.views.render", side_effect=lambda request, template, context: context).start()
        patch("netbox_cots.views.redirect", return_value="redirected").start()
        patch("netbox_cots.views.messages.success").start()
        self.addCleanup(patch.stopall)

    def request(self, method="get", data=None, superuser=True):
        request = getattr(self.factory, method)("/plugins/cots/installations/purge/", data or {})
        request.user = SimpleNamespace(is_authenticated=True, is_superuser=superuser)
        return request

    @patch("netbox_cots.views.Installation.objects")
    def test_get_displays_count(self, objects):
        objects.count.return_value = 12
        result = PurgeInstallationsView.as_view()(self.request())
        self.assertEqual(result["installation_count"], 12)
        self.assertEqual(result["confirmation_text"], "SUPPRIMER")

    @patch("netbox_cots.views.Installation.objects")
    def test_wrong_confirmation_does_not_delete(self, objects):
        objects.count.return_value = 12
        result = PurgeInstallationsView.as_view()(self.request("post", {"confirmation": "NON"}))
        self.assertIn("SUPPRIMER", result["error"])
        objects.all.assert_not_called()

    @patch("netbox_cots.views.transaction.atomic")
    @patch("netbox_cots.views.Installation.objects")
    def test_confirmed_purge_deletes_all_installations(self, objects, atomic):
        objects.count.return_value = 12
        objects.all.return_value.delete.return_value = (12, {"netbox_cots.Installation": 12})
        atomic.return_value.__enter__ = MagicMock()
        atomic.return_value.__exit__ = MagicMock(return_value=False)
        result = PurgeInstallationsView.as_view()(self.request("post", {"confirmation": "SUPPRIMER"}))
        self.assertEqual(result, "redirected")
        objects.all.return_value.delete.assert_called_once_with()

    def test_non_superuser_is_forbidden(self):
        with self.assertRaises(PermissionDenied):
            PurgeInstallationsView.as_view()(self.request(superuser=False))
