from collections import Counter

from dcim.models import Device
from virtualization.models import VirtualMachine
from extras.models import Tag
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
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
                     installations_updated=0, unchanged=0, duplicates=0, tags_created=0, tags_added=0)
    details = []
    created_tags = []
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
            tag_cache = {}
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
                    if seen[key] != (row.version, row.tags):
                        raise ImportFailure(f"Ligne {row.line} : versions ou tags différents du même COTS sur la même machine dans le fichier.")
                    counts["duplicates"] += 1
                    continue
                seen[key] = (row.version, row.tags)
                tags = []
                for name in row.tags:
                    tag = tag_cache.get(name)
                    if tag is None:
                        tag = Tag.objects.filter(name=name).first()
                        if tag is None:
                            tag_slug = slugify(name, allow_unicode=True)
                            if not tag_slug or len(tag_slug) > 100:
                                raise ImportFailure(f"Ligne {row.line} : impossible de générer un slug pour le tag {name}.")
                            collision = Tag.objects.filter(slug=tag_slug).first()
                            if collision is not None:
                                raise ImportFailure(f"Ligne {row.line} : le slug {tag_slug} appartient déjà au tag {collision.name}. Utiliser son nom exact ou un nom distinct.")
                            tag = Tag(name=name, slug=tag_slug)
                            tag.full_clean()
                            tag.save()
                            created_tags.append({"name": name, "slug": tag_slug})
                            counts["tags_created"] += 1
                        tag_cache[name] = tag
                        if tag.object_types.exists() and not tag.object_types.filter(
                            app_label=Installation._meta.app_label, model=Installation._meta.model_name
                        ).exists():
                            raise ImportFailure(f"Ligne {row.line} : le tag {name} n’est pas autorisé pour les installations COTS.")
                    tags.append(tag)
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
                before_tags = list(installation.tags.order_by("name").values_list("name", flat=True)) if installation and tags else []
                existing_tag_ids = set(installation.tags.values_list("pk", flat=True)) if installation and tags else set()
                added_tags = [tag for tag in tags if tag.pk not in existing_tag_ids]
                if installation is None:
                    installation = Installation(software_version=version, **target)
                    installation.save()
                    action = "created"
                    counts["installations_created"] += 1
                elif installation.software_version_id != version.pk or added_tags:
                    installation.snapshot()
                    installation.software_version = version
                    installation.save()
                    action = "updated"
                    counts["installations_updated"] += 1
                else:
                    action = "unchanged"
                    counts["unchanged"] += 1
                if added_tags:
                    installation.tags.add(*added_tags)
                    counts["tags_added"] += len(added_tags)
                if len(details) < 100:
                    details.append({"machine": str(machine), "cots": app.name, "before": old or "-", "after": row.version, "action": action,
                                    "tags_added": [tag.name for tag in added_tags],
                                    "tags_after": sorted(set(before_tags) | set(row.tags)) if tags else None})
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
            ContentType.objects.clear_cache()
    return {"dry_run": dry_run, "rows": len(rows), "counts": dict(counts), "details": details, "created_tags": created_tags}
