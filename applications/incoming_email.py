import re
from datetime import date

from django.db import transaction
from django.utils import timezone

from .email_helpers import matching_role, suggest_company, suggest_role
from .models import Application, IncomingEmail


def clear_rejection(body):
    # Ignore quoted earlier messages when identifying the current update.
    current_text = re.split(
        r"(?im)^On .+wrote:\s*$|^-{2,}\s*Original Message\s*-{2,}",
        body,
        maxsplit=1,
    )[0]

    return bool(re.search(
        r"\bwe (?:have decided|have chosen|will|are) "
        r"(?:not to|not) (?:move|moving|proceed|proceeding)\b"
        r"|\bwe will not be moving forward\b"
        r"|\bwe (?:have decided|have chosen) to move forward "
        r"with other candidates\b"
        r"|\byou have not been selected\b"
        r"|\byour application (?:was|has been) unsuccessful\b",
        current_text,
        flags=re.IGNORECASE,
    ))


def finish(email, status, note):
    email.processing_status = status
    email.processing_note = note
    email.processed_at = timezone.now()
    email.save()
    return email


@transaction.atomic
def process_incoming_email(email_id):
    email = (
        IncomingEmail.objects.select_for_update()
        .select_related("mailbox")
        .get(pk=email_id)
    )

    # A repeated delivery must not update the application again.
    if email.processing_status != "Pending":
        return email

    if not email.mailbox.enabled:
        return finish(email, "Ignored", "Receiving mailbox is disabled.")

    if email.message_id and IncomingEmail.objects.filter(
        mailbox=email.mailbox,
        message_id=email.message_id,
        processing_status="Updated",
    ).exclude(pk=email.pk).exists():
        return finish(email, "Ignored", "This message was already processed.")

    if not clear_rejection(email.body):
        return finish(
            email,
            "Review",
            "No clear rejection found. Review this follow-up manually.",
        )

    email.suggested_status = "Rejected"
    company = suggest_company(email.subject, email.sender)
    role = suggest_role(" ".join(email.body.split()))

    if not company or not role:
        return finish(email, "Review", "Company or role could not be identified.")

    matches = [
        application
        for application in Application.objects.select_for_update().filter(
            owner=email.mailbox.owner,
            company__iexact=company,
        )
        if matching_role(application.role) == matching_role(role)
    ]

    if len(matches) != 1:
        return finish(
            email,
            "Review",
            "Could not match exactly one application.",
        )

    application = matches[0]
    email.application = application

    if email.sent_at is None:
        return finish(email, "Review", "The email has no reliable date.")

    email_date = timezone.localtime(email.sent_at).date()
    metadata = dict(application.email_metadata or {})

    previous_dates = [
        metadata.get("last_update_email_date"),
        metadata.get("manual_status_date"),
    ]

    for previous_date in previous_dates:
        if previous_date:
            try:
                if email_date <= date.fromisoformat(previous_date):
                    return finish(
                        email,
                        "Review",
                        "An existing update is from the same day or later.",
                    )
            except ValueError:
                return finish(email, "Review", "Existing date needs review.")

    if application.status == "Rejected":
        return finish(email, "Ignored", "Application is already rejected.")

    if application.status != "Applied":
        return finish(
            email,
            "Review",
            "Only applications currently marked Applied update automatically.",
        )

    application.status = "Rejected"

    history = list(metadata.get("email_history", []))
    history.append({
        "message_id": email.message_id or f"incoming:{email.pk}",
        "subject": email.subject,
        "email_date": email_date.isoformat(),
        "status": "Rejected",
        "source": "forwarded_email",
    })

    metadata["email_history"] = history
    metadata["last_update_email_id"] = history[-1]["message_id"]
    metadata["last_update_email_date"] = email_date.isoformat()
    application.email_metadata = metadata
    application.full_clean()
    application.save(
        update_fields=["status", "email_metadata"]
    )

    return finish(email, "Updated", "Application automatically marked Rejected.")