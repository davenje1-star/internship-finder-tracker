import runpy

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Manage applications in the Django database"

    def handle(self, *args, **options):
        runpy.run_path(
            str(settings.BASE_DIR / "tracker.py"),
            run_name="__main__",
        )