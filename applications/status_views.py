from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Application


@staff_member_required
@require_POST
def application_status_update(request, pk):
    status = request.POST.get("status", "")
    if status not in dict(Application.STATUS_CHOICES):
        return JsonResponse({"error": "Choose a valid status."}, status=400)

    with transaction.atomic():
        application = get_object_or_404(
            Application.objects.select_for_update(), pk=pk, owner=request.user
        )
        application.status = status
        fields = ["status"]
        if status == "Applied" and not application.date_applied:
            application.date_applied = timezone.localdate()
            fields.append("date_applied")
        application.save(update_fields=fields)

    return JsonResponse({
        "status": application.status,
        "label": application.get_status_display(),
        "date_applied": application.date_applied.isoformat() if application.date_applied else "—",
    })
