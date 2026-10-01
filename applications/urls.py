from django.urls import path
from . import views
from .dashboard_views import progress_dashboard

urlpatterns = [
    path("progress/", progress_dashboard, name="progress_dashboard"),
    path("", views.application_list, name="application_list"),
    path("add/", views.application_create, name="application_create"),
    path("finder/", views.internship_finder, name="internship_finder"),
    path("import-email/", views.import_email, name="import_email"),
]