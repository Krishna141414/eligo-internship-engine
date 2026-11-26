"""Import the cleaned public internship dataset written by the notebook.

    python manage.py load_internships            # create missing rows only (safe to re-run)
    python manage.py load_internships --refresh  # also refresh source fields of existing rows, and retire
                                                 # dataset rows the notebook no longer produces

Refuses to run unless artifacts/manifest.json verifies (hard rule 14). Never re-activates a row, so
internships an admin deactivated stay deactivated. Retired rows (e.g. duplicates the notebook now
drops) are deactivated, not deleted: stored recommendations still point at them.
"""
import json
from datetime import date
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from internships.models import Internship
from ml_core.artifacts import verify_manifest

SOURCE_FIELDS = ["company_name", "internship_title", "job_role", "description", "description_derived",
                 "required_qualification", "specialization", "minimum_academic_percentage", "required_skills",
                 "location", "work_mode", "stipend", "stipend_min", "stipend_max", "duration", "duration_months",
                 "eligibility_criteria", "start_date", "application_deadline", "derived_fields", "embedding_row",
                 "embedding_text_hash"]


def _nz(v, default=None):
    return default if v is None or (isinstance(v, float) and pd.isna(v)) or v == "" else v


class Command(BaseCommand):
    help = "Import artifacts/data/internships_clean.csv into the Internship table."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--refresh", action="store_true")

    def handle(self, *args, limit=None, refresh=False, **options):
        root = Path(settings.ELIGO_ARTIFACTS_DIR)
        status = verify_manifest(root)
        if not status.ok:
            detail = "; ".join(f"missing {m}" for m in status.missing) or "; ".join(f"changed {m}" for m in status.mismatched)
            raise CommandError(f"{status.message} ({detail})" if detail else status.message)
        df = pd.read_csv(root / "data" / "internships_clean.csv", dtype={"source_id": str}, keep_default_na=False)
        index = {r["source_id"]: r for r in json.loads((root / "embeddings" / "internship_index.json").read_text())}
        if limit:
            df = df.head(limit)

        existing = set(Internship.objects.filter(source_id__in=df["source_id"].tolist()).values_list("source_id", flat=True))
        objs = []
        for r in df.to_dict("records"):
            meta = index.get(r["source_id"], {})
            deadline = _nz(r["application_deadline"])
            objs.append(Internship(
                source_id=r["source_id"], company_name=r["company_name"], internship_title=r["internship_title"],
                job_role=r["job_role"], description=r["description"],
                description_derived=str(r["description_derived"]).lower() == "true",
                required_qualification=r["required_qualification"], specialization=_nz(r["specialization"], ""),
                minimum_academic_percentage=_nz(r["minimum_academic_percentage"], 0),
                required_skills=json.loads(r["required_skills"] or "[]"), location=r["location"] or "Not specified",
                work_mode=_nz(r["work_mode"], Internship.WorkMode.ONSITE), stipend=_nz(r["stipend_text"], ""),
                stipend_min=int(float(r["stipend_min"])) if _nz(r["stipend_min"]) is not None else None,
                stipend_max=int(float(r["stipend_max"])) if _nz(r["stipend_max"]) is not None else None,
                duration=_nz(r["duration_text"], ""),
                duration_months=float(r["duration_months"]) if _nz(r["duration_months"]) is not None else None,
                eligibility_criteria=_nz(r["eligibility_criteria"], ""), start_date=_nz(r.get("start_date"), ""),
                application_deadline=date.fromisoformat(deadline) if deadline else None,
                derived_fields=json.loads(r["derived_fields"] or "[]"),
                embedding_row=meta.get("row"), embedding_text_hash=meta.get("text_hash", ""),
                status=Internship.Status.ACTIVE))

        new = [o for o in objs if o.source_id not in existing]
        with transaction.atomic():
            Internship.objects.bulk_create(new, batch_size=500)
            updated = retired = 0
            if refresh:
                old = [o for o in objs if o.source_id in existing]
                by_sid = {i.source_id: i for i in Internship.objects.filter(source_id__in=[o.source_id for o in old])}
                for o in old:
                    target = by_sid[o.source_id]
                    for f in SOURCE_FIELDS:
                        setattr(target, f, getattr(o, f))
                Internship.objects.bulk_update(list(by_sid.values()), SOURCE_FIELDS, batch_size=500)
                updated = len(old)
                if not limit:      # a --limit run sees only part of the dataset, so it never retires anything
                    retired = (Internship.objects.filter(source_id__isnull=False)
                               .exclude(source_id__in=df["source_id"].tolist())
                               .update(status=Internship.Status.INACTIVE, embedding_row=None, embedding_text_hash=""))
        self.stdout.write(self.style.SUCCESS(
            f"Internships: {len(new)} created, {updated} refreshed, {len(existing) - updated} left unchanged, "
            f"{retired} retired (no longer in the cleaned dataset)."))
