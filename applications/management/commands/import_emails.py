import runpy

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Import application emails directly into Django"

    def handle(self, *args, **options):
        runpy.run_path(
            str(settings.BASE_DIR / "email_importer.py"),
            run_name="__main__",
        )