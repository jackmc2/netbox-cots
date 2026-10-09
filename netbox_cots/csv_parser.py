"""CSV parsing has no NetBox dependency and can be tested independently."""
import csv
import io
import re
import unicodedata
from dataclasses import dataclass


class ImportFailure(ValueError):
    pass


@dataclass(frozen=True)
class ImportRow:
    line: int
    machine_type: str
    machine: str
    machine_id: int | None
    cots: str
    cots_slug: str
    version: str
    publisher: str
    tags: tuple[str, ...] = ()


def parse_csv(text, max_rows=10000):
    if "\x00" in text:
        raise ImportFailure("Le CSV contient un caractère nul.")
    text = text.lstrip("\ufeff")
    first_line = text.splitlines()[0] if text.splitlines() else ""
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter, strict=True)
    required = {"machine_type", "cots", "version"}
    allowed = required | {"machine", "machine_id", "cots_slug", "publisher", "tags"}
    try:
        headers = reader.fieldnames or []
    except csv.Error as exc:
        raise ImportFailure(f"En-tête CSV invalide : {exc}") from exc
    if len(headers) != len(set(headers)) or not required.issubset(headers) or set(headers) - allowed:
        raise ImportFailure("En-tête attendu : machine_type,machine,cots,version ; optionnels : machine_id,cots_slug,publisher,tags.")
    if not ({"machine", "machine_id"} & set(headers)):
        raise ImportFailure("Une colonne machine ou machine_id est nécessaire.")
    rows = []
    try:
        for record in reader:
            if None in record or any(v is None for v in record.values()):
                raise ImportFailure(f"Ligne {reader.line_num} : nombre de colonnes incorrect.")
            data = {key: unicodedata.normalize("NFC", value.strip()) for key, value in record.items()}
            if not any(data.values()):
                continue
            line = reader.line_num
            if data["machine_type"] not in ("device", "virtual_machine"):
                raise ImportFailure(f"Ligne {line} : machine_type doit être device ou virtual_machine.")
            if not data["cots"] or not data["version"] or not (data.get("machine") or data.get("machine_id")):
                raise ImportFailure(f"Ligne {line} : machine, COTS ou version vide.")
            for key, length in (("cots", 200), ("version", 100), ("publisher", 200), ("cots_slug", 100), ("machine", 200)):
                if len(data.get(key, "")) > length:
                    raise ImportFailure(f"Ligne {line} : {key} dépasse {length} caractères.")
            raw_id = data.get("machine_id", "")
            if raw_id and (len(raw_id) > 19 or not re.fullmatch(r"[0-9]+", raw_id) or not 0 < int(raw_id) <= 9223372036854775807):
                raise ImportFailure(f"Ligne {line} : machine_id doit être un entier positif.")
            if data.get("cots_slug") and not re.fullmatch(r"[-a-zA-Z0-9_]+", data["cots_slug"]):
                raise ImportFailure(f"Ligne {line} : cots_slug invalide.")
            raw_tags = data.get("tags", "")
            tags = tuple(sorted(set(part.strip() for part in raw_tags.split("|")))) if raw_tags else ()
            if tags and ("" in tags or any(len(tag) > 100 for tag in tags) or len(tags) > 50):
                raise ImportFailure(f"Ligne {line} : tags invalides (noms de 1 à 100 caractères, séparés par |, 50 tags maximum).")
            rows.append(ImportRow(line, data["machine_type"], data.get("machine", ""), int(raw_id) if raw_id else None,
                                  data["cots"], data.get("cots_slug", ""), data["version"], data.get("publisher", ""), tags))
            if len(rows) > max_rows:
                raise ImportFailure(f"Import limité à {max_rows} lignes.")
    except csv.Error as exc:
        raise ImportFailure(f"CSV invalide : {exc}") from exc
    if not rows:
        raise ImportFailure("Le fichier ne contient aucune installation.")
    return rows
