"""Prepare a role CSV from legacy data, without changing either inventory."""
import csv
import io
from .csv_parser import ImportFailure
from .models import Installation, RoleAssignment


def legacy_role_csv():
    groups = {}
    problems = []
    rows = Installation.objects.select_related("device__role", "virtual_machine__role", "application", "software_version").prefetch_related("tags")
    for row in rows:
        machine = row.machine
        if not machine.role_id:
            problems.append(f"{machine} : aucun rôle")
            continue
        key = (machine.role_id, row.application_id)
        group = groups.setdefault(key, {"role": machine.role, "application": row.application, "versions": set(), "tags": set()})
        group["versions"].add(row.software_version.version)
        group["tags"].update(row.tags.values_list("name", flat=True))
    for (role_id, application_id), group in groups.items():
        if len(group["versions"]) != 1:
            problems.append(f"{group['role'].slug} / {group['application']} : versions différentes ({', '.join(sorted(group['versions']))})")
            continue
        existing = RoleAssignment.objects.filter(role_id=role_id, application_id=application_id).select_related("software_version").first()
        if existing and existing.software_version.version not in group["versions"]:
            problems.append(f"{group['role'].slug} / {group['application']} : le rôle a déjà une autre version ({existing.software_version.version})")
        if any("|" in name for name in group["tags"]):
            problems.append(f"{group['role'].slug} : un nom de tag contient | et ne peut pas être converti")
    if problems:
        raise ImportFailure("Reprise refusée ; aucune modification : " + "; ".join(problems))
    if not groups:
        raise ImportFailure("Aucune ancienne installation à reprendre.")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(("role_id", "role", "cots_slug", "cots", "version", "publisher", "tags"))
    for (role_id, _), group in sorted(groups.items()):
        writer.writerow((role_id, group["role"].slug, group["application"].slug, group["application"].name,
                         next(iter(group["versions"])), group["application"].publisher, "|".join(sorted(group["tags"]))))
    return output.getvalue()
