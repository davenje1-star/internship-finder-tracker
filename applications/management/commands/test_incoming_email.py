from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from applications.incoming_email import process_incoming_email
from applications.models import Application, EmailMailbox, IncomingEmail


class Command(BaseCommand):
    help = "Test incoming-email processing without retaining test records"

    def handle(self, *args, **options):
        with transaction.atomic():
            user = get_user_model().objects.get(username="yvngdj")
            mailbox, _ = EmailMailbox.objects.get_or_create(owner=user)

            company = f"ProcessorTest{uuid4().hex[:12]}"
            role = "Software Engineer Intern"

            application = Application.objects.create(
                owner=user,
                company=company,
                role=role,
                status="Applied",
            )

            email = IncomingEmail.objects.create(
                mailbox=mailbox,
                delivery_id=uuid4().hex,
                message_id=f"<{uuid4().hex}@example.com>",
                sender="Recruiting <recruiting@example.com>",
                subject=f"Thank you for applying to {company}",
                body=(
                    f"Thank you for applying for the {role} position. "
                    "We will not be moving forward with your application."
                ),
                sent_at=timezone.now(),
            )

            result = process_incoming_email(email.pk)
            application.refresh_from_db()

            if (
                result.processing_status != "Updated"
                or application.status != "Rejected"
            ):
                raise CommandError(
                    f"Test failed: {result.processing_status}. "
                    f"{result.processing_note}"
                )

            process_incoming_email(email.pk)
            application.refresh_from_db()

            if len(application.email_metadata["email_history"]) != 1:
                raise CommandError("Repeated processing added duplicate history.")

            self.stdout.write(
                self.style.SUCCESS(
                    "PASS: rejection updated; repeated processing skipped."
                )
            )

            # Roll back every test record.
            transaction.set_rollback(True)

        self.stdout.write("Test records removed; real applications unchanged.")