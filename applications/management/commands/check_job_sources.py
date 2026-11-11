"""Warm and report the same employer feed used by both web finders."""
from django.core.management.base import BaseCommand, CommandError
from applications.job_sources import get_feed, filter_jobs


class Command(BaseCommand):
    help = "Fetch both listing feeds and report unique internship coverage."

    def add_arguments(self, parser):
        parser.add_argument("--refresh", action="store_true", help="Bypass fresh board caches.")

    def handle(self, *args, **options):
        try:
            feed = get_feed(refresh=options["refresh"])
        except (ValueError, OSError) as error:
            raise CommandError(str(error)) from error
        for source in feed["sources"]:
            self.stdout.write(f"{source['company']} ({source['provider']}): {source['state']} {source.get('error', '')}")
        self.stdout.write(
            f"{feed['board_count']} boards; {len(feed['jobs'])} technology internships; "
            f"{len(filter_jobs(feed))} with recognized US locations."
        )
        software = filter_jobs(feed, software_only=True)
        summer = sum(bool(job.get("summer_2027")) for job in software)
        self.stdout.write(
            f"{len(software)} US software engineering title matches, "
            f"{summer} tagged Summer 2027."
        )
        if all(source["state"] == "unavailable" for source in feed["sources"]):
            raise CommandError("All listing sources are unavailable. Check connectivity and board identifiers.")
