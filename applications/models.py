import uuid

from django.conf import settings
from django.db import models, router, transaction


class Application(models.Model):
    STATUS_CHOICES = [
        ("Saved", "Saved"),
        ("Applied", "Applied"),
        ("Assessment", "Assessment"),
        ("Interview", "Interview (unspecified stage)"),
        ("First Interview", "First Interview"),
        ("Second Interview", "Second Interview"),
        ("Final Interview", "Final Interview"),
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

    def save(self, *args, **kwargs):
        database = kwargs.get("using") or router.db_for_write(type(self), instance=self)
        update_fields = kwargs.get("update_fields")
        records_status = update_fields is None or "status" in update_fields
        with transaction.atomic(using=database):
            previous = None
            if self.pk and not self._state.adding and records_status:
                previous = type(self).objects.using(database).select_for_update().get(pk=self.pk).status
            is_new = self._state.adding
            super().save(*args, **kwargs)
            if is_new or (records_status and previous != self.status):
                ApplicationStatusHistory.objects.using(database).create(
                    application=self,
                    previous_status=previous or "",
                    status=self.status,
                )

    def __str__(self):
        return f"{self.company} — {self.role}"


class ApplicationStatusHistory(models.Model):
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="status_history"
    )
    previous_status = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=Application.STATUS_CHOICES)
    recorded_at = models.DateTimeField(auto_now_add=True)
    is_baseline = models.BooleanField(default=False)

    class Meta:
        ordering = ["recorded_at", "id"]
        verbose_name_plural = "application status history"

    def __str__(self):
        return f"{self.previous_status or 'Starting status'} → {self.status}"



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