import uuid

from django.conf import settings
from django.db import models


class Application(models.Model):
    STATUS_CHOICES = [
        ("Saved", "Saved"),
        ("Applied", "Applied"),
        ("Interview", "Interview"),
        ("Rejected", "Rejected"),
        ("Offer", "Offer"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="applications",
    )
    company = models.CharField(max_length=200)
    role = models.CharField(max_length=300)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Saved",
    )
    date_applied = models.DateField(null=True, blank=True)
    link = models.URLField(max_length=2000, blank=True)
    location = models.TextField(blank=True)
    email_metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.company} — {self.role}"


class EmailMailbox(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_mailbox",
    )
    address_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Mailbox for {self.owner}"


class IncomingEmail(models.Model):
    PROCESSING_CHOICES = [
        ("Pending", "Pending"),
        ("Updated", "Updated"),
        ("Review", "Needs review"),
        ("Ignored", "Ignored"),
    ]

    mailbox = models.ForeignKey(
        EmailMailbox,
        on_delete=models.CASCADE,
        related_name="incoming_emails",
    )
    delivery_id = models.CharField(max_length=255)
    message_id = models.CharField(max_length=998, blank=True)
    sender = models.CharField(max_length=500)
    subject = models.CharField(max_length=1000, blank=True)
    body = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    processing_status = models.CharField(
        max_length=20,
        choices=PROCESSING_CHOICES,
        default="Pending",
    )
    application = models.ForeignKey(
        Application,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incoming_emails",
    )
    suggested_status = models.CharField(
        max_length=20,
        choices=Application.STATUS_CHOICES,
        blank=True,
    )
    processing_note = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-received_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["mailbox", "delivery_id"],
                name="unique_mailbox_email_delivery",
            ),
        ]

    def __str__(self):
        return self.subject or f"Email from {self.sender}"