import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from applications.models import Application


class Command(BaseCommand):
    help = "Import applications from applications.json"

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(settings.BASE_DIR) / "applications.json"

        with path.open(encoding="utf-8") as file:
            records = json.load(file)

        imported = 0
        skipped = 0

        for record in records:
            company = record["company"].strip()
            role = record["role"].strip()

            if Application.objects.filter(
                company__iexact=company,
                role__iexact=role,
            ).exists():
                skipped += 1
                continue

            application = Application(
                company=company,
                role=role,
                status=record.get("status", "Saved").strip().capitalize(),
                date_applied=record.get("date_applied") or None,
                link=record.get("link", ""),
                location=record.get("location", ""),
            )
            application.full_clean()
            application.save()
            imported += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {imported} applications; skipped {skipped} duplicates."
            )
        )