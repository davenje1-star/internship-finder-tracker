from django.db import models


class Application(models.Model):
    STATUS_CHOICES = [
        ("Saved", "Saved"),
        ("Applied", "Applied"),
        ("Interview", "Interview"),
        ("Rejected", "Rejected"),
        ("Offer", "Offer"),
    ]

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