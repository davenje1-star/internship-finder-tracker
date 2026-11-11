"""Import an audited Takeout export into a staff user's local tracker."""
import json
from collections import Counter
from pathlib import Path
import re

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from applications.models import Application


def name_key(value):
    return re.sub(r"[^a-z0-9]", "", value.casefold())


class Command(BaseCommand):
    help = "Preview audited applications, or add new rows with --apply."

    def add_arguments(self, parser):
        parser.add_argument("audit_file", type=Path)
        parser.add_argument("--username", required=True)
        parser.add_argument("--apply", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        owner = get_user_model().objects.filter(
            username=options["username"], is_active=True, is_staff=True
        ).first()
        if owner is None:
            raise CommandError("Enter your local Django Admin username.")
        try:
            records = json.loads(options["audit_file"].read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CommandError(f"Could not open the audit data: {exc}") from exc

        existing = list(Application.objects.select_for_update().filter(owner=owner))
        counts = Counter()
        allowed = dict(Application.STATUS_CHOICES)
        for record in records:
            company, role, status = (record[field] for field in ("company", "role", "status"))
            label = f"{company} | {role} | {status}"
            if status not in allowed:
                counts["review"] += 1
                self.stdout.write(f"REVIEW {label} (status unavailable in tracker)")
                continue
            if any(row.email_metadata.get("takeout_audit_key") == record["key"] for row in existing):
                counts["already imported"] += 1
                continue
            same_company = [row for row in existing if name_key(row.company) == name_key(company)]
            if same_company:
                requisition = record["requisition"]
                # Exact requisitions can distinguish different submissions.
                matches = [
                    row for row in same_company
                    if requisition and re.search(
                        rf"(?<![a-z0-9]){re.escape(requisition)}(?![a-z0-9])",
                        f"{row.role} {row.link}", re.I
                    )
                ]
                # Existing rows may reflect newer information than the archive.
                if len(matches) == 1 and matches[0].status == status:
                    counts["already tracked"] += 1
                    continue
                counts["review"] += 1
                self.stdout.write(f"REVIEW {label} (compare existing application rows)")
                continue
            candidate = Application(
                owner=owner, company=company, role=role, status=status,
                date_applied=record["application_date"],
                email_metadata={
                    "takeout_audit_key": record["key"],
                    "evidence_date": record["evidence_date"],
                    "evidence": record["evidence"],
                    "audit_notes": record["notes"],
                    "requisition": record["requisition"],
                },
            )
            candidate.full_clean()
            if options["apply"]:
                candidate.save()
            counts["added" if options["apply"] else "would add"] += 1
            self.stdout.write(f"{'ADDED' if options['apply'] else 'PREVIEW'} {label}")

        self.stdout.write(", ".join(f"{key}: {value}" for key, value in counts.items()))
        if not options["apply"]:
            self.stdout.write("Preview only. Add --apply after reviewing the results.")
