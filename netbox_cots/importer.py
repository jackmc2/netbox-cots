from collections import Counter

from dcim.models import Device
from virtualization.models import VirtualMachine
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.text import slugify
from netbox.context import events_queue

from .csv_parser import ImportFailure, parse_csv
from .models import Application, SoftwareVersion, Installation


def resolve_machine(row):
    model = Device if row.machine_type == "device" else VirtualMachine
    query = model.objects.filter(pk=row.machine_id) if row.machine_id else model.objects.filter(name=row.machine)
    matches = list(query[:2])
    if len(matches) != 1:
        raise ImportFailure(f"Ligne {row.line} : machine inconnue ou ambiguë ({row.machine_type} / {row.machine or row.machine_id}). Utiliser machine_id en cas de doublon de nom.")
    machine = matches[0]
    if row.machine_id and row.machine and machine.name != row.machine:
        raise ImportFailure(f"Ligne {row.line} : machine_id et machine ne correspondent pas.")
    return machine


def import_csv(text, *, dry_run=True, max_rows=10000):
    """Atomic upsert. Only call from the superuser-only view or trusted CLI.

    No deletions. Locks selected machines in a deterministic order to serialize
    concurrent imports for the same targets. Database constraints protect other
    write paths too. An error, including a name collision, rolls back all rows.
    """
    rows = parse_csv(text, max_rows=max_rows)
    counts = Counter(applications_created=0, versions_created=0, installations_created=0,
                     installations_updated=0, unchanged=0, duplicates=0)
    details = []
    current_line = None
    previous_events = events_queue.get().copy()
    completed = False
    try:
        with transaction.atomic():
            resolved = [(row, resolve_machine(row)) for row in rows]
            locks = sorted({(row.machine_type, machine.pk) for row, machine in resolved})
            for kind, pk in locks:
                model = Device if kind == "device" else VirtualMachine
                model.objects.select_for_update().get(pk=pk)
            seen = {}
            app_cache = {}
            version_cache = {}
            for row, machine in resolved:
                current_line = row.line
                slug = row.cots_slug or slugify(row.cots)
                if not slug or len(slug) > 100:
                    raise ImportFailure(f"Ligne {row.line} : renseigner un cots_slug explicite de 1 à 100 caractères.")
                app = app_cache.get(slug)
                if app is None:
                    app = Application.objects.filter(slug=slug).first()
                    if app is None:
                        app = Application(name=row.cots, slug=slug, publisher=row.publisher)
                        app.full_clean()
                        app.save()
                        counts["applications_created"] += 1
                    app_cache[slug] = app
                if app.name.casefold() != row.cots.casefold():
                    raise ImportFailure(f"Ligne {row.line} : l'identifiant {slug} désigne déjà {app.name}. Choisir un identifiant distinct.")
                if row.publisher and app.publisher != row.publisher:
                    raise ImportFailure(f"Ligne {row.line} : éditeur différent pour {app.name}. Corriger la fiche COTS avant l'import.")
                key = (row.machine_type, machine.pk, app.pk)
                if key in seen:
                    if seen[key] != row.version:
                        raise ImportFailure(f"Ligne {row.line} : deux versions du même COTS sur la même machine dans le fichier.")
                    counts["duplicates"] += 1
                    continue
                seen[key] = row.version
                version_key = (app.pk, row.version)
                version = version_cache.get(version_key)
                if version is None:
                    version = SoftwareVersion.objects.filter(application=app, version=row.version).first()
                    if version is None:
                        version = SoftwareVersion(application=app, version=row.version)
                        version.full_clean()
                        version.save()
                        counts["versions_created"] += 1
                    version_cache[version_key] = version
                target = {"device": machine} if row.machine_type == "device" else {"virtual_machine": machine}
                installation = Installation.objects.select_for_update().filter(application=app, **target).first()
                old = installation.software_version.version if installation else None
                if installation is None:
                    installation = Installation(software_version=version, **target)
                    installation.save()
                    action = "created"
                    counts["installations_created"] += 1
                elif installation.software_version_id != version.pk:
                    installation.snapshot()
                    installation.software_version = version
                    installation.save()
                    action = "updated"
                    counts["installations_updated"] += 1
                else:
                    action = "unchanged"
                    counts["unchanged"] += 1
                if len(details) < 100:
                    details.append({"machine": str(machine), "cots": app.name, "before": old or "-", "after": row.version, "action": action})
            if dry_run:
                transaction.set_rollback(True)
        completed = True
    except (ValidationError, IntegrityError) as exc:
        message = "; ".join(exc.messages) if isinstance(exc, ValidationError) else "Conflit de données ou import concurrent : relancer après vérification."
        raise ImportFailure(f"Ligne {current_line or '?'} : {message}") from exc
    finally:
        # NetBox's request middleware flushes events outside the DB transaction.
        # A preview or failed import must never emit events for rolled-back rows.
        if dry_run or not completed:
            events_queue.set(previous_events)
    return {"dry_run": dry_run, "rows": len(rows), "counts": dict(counts), "details": details}
