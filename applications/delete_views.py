from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .models import Application


@staff_member_required
@require_http_methods(["GET", "POST"])
def application_delete(request, pk):
    application = get_object_or_404(Application, pk=pk, owner=request.user)
    params = request.POST if request.method == "POST" else request.GET
    filters = {key: params.get(key, "") for key in ("q", "status", "sort")}
    list_url = reverse("application_list")
    query = urlencode({key: value for key, value in filters.items() if value})
    if query:
        list_url += "?" + query

    if request.method == "POST":
        company = application.company
        application.delete()
        messages.success(request, f"Deleted the application for {company}.")
        return redirect(list_url)

    return render(request, "applications/application_confirm_delete.html", {
        "application": application,
        "query": filters["q"],
        "selected_status": filters["status"],
        "cancel_url": list_url,
        "sort": filters["sort"],
    })
