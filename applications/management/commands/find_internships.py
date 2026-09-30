import runpy

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Find software internships and save selected listings"

    def handle(self, *args, **options):
        runpy.run_path(
            str(settings.BASE_DIR / "finder.py"),
            run_name="__main__",
        )