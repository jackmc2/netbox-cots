import json
import uuid
from contextlib import nullcontext
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from netbox.context_managers import event_tracking
from netbox_cots.csv_parser import ImportFailure
from netbox_cots.importer import import_csv


class Command(BaseCommand):
    help = "Import atomique des installations COTS (simulation par défaut)."

    def add_arguments(self, parser):
        parser.add_argument("file")
        parser.add_argument("--apply", action="store_true", help="Enregistrer les modifications.")
        parser.add_argument("--user", help="Nom du superutilisateur pour tracer un import appliqué.")

    def handle(self, *args, **options):
        config = settings.PLUGINS_CONFIG["netbox_cots"]
        tracker = nullcontext()
        if options["apply"]:
            if not options["user"]:
                raise CommandError("--user est obligatoire avec --apply.")
            user = get_user_model().objects.filter(username=options["user"], is_superuser=True, is_active=True).first()
            if user is None:
                raise CommandError("Superutilisateur actif introuvable.")
            request = RequestFactory().post("/plugins/cots/import/")
            request.user = user
            request.id = uuid.uuid4()
            tracker = event_tracking(request)
        try:
            path = Path(options["file"])
            if path.stat().st_size > config["max_import_bytes"]:
                raise ImportFailure("Fichier trop volumineux.")
            text = path.read_text(encoding="utf-8-sig")
            # Track imported changes; dry-run side effects must not escape rollback.
            with tracker:
                result = import_csv(text, dry_run=not options["apply"], max_rows=config["max_import_rows"])
        except (OSError, UnicodeDecodeError, ImportFailure) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
