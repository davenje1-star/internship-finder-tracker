from .sorting import application_ordering, sort_context
from .email_detection import detect_company, detect_status, review_notes
import hashlib

import re

from email import policy

from email.parser import BytesParser

from email.utils import parsedate_to_datetime

from urllib.parse import urlencode
from uuid import uuid4


from bs4 import BeautifulSoup

from django.contrib import messages

from django.contrib.admin.views.decorators import staff_member_required

from django.core.cache import cache

from django.core.exceptions import ValidationError

from django.core.paginator import Paginator

from django.db.models import Q

from django.shortcuts import redirect, render

from django.urls import reverse
from django.utils import timezone

from .email_forms import (

    EmailPreviewForm,

    EmailUploadForm,

    PastedEmailForm,

)

from .email_helpers import (

    is_rejection,

    matching_role,

    suggest_company,

    suggest_role,

)

from .forms import ApplicationForm

from .models import Application, HiddenCompany

@staff_member_required

def application_list(request):

    query = request.GET.get("q", "").strip()

    status = request.GET.get("status", "").strip()

    ordering = application_ordering()
    sort = request.GET.get("sort", "status_desc")
    if sort not in ordering:
        sort = "status_desc"
    applications = Application.objects.filter(owner=request.user).order_by(*ordering[sort])

    if query:

        applications = applications.filter(

            Q(company__icontains=query) | Q(role__icontains=query)

        )

    if status:

        applications = applications.filter(status=status)

    return render(

        request,

        "applications/application_list.html",

        {

            **sort_context(sort),
            "applications": applications,

            "query": query,

            "selected_status": status,

            "status_choices": Application.STATUS_CHOICES,

        },

    )

@staff_member_required

def application_create(request):

    if request.method == "POST":

        form = ApplicationForm(request.POST)

        if form.is_valid():

            application = form.save(commit=False)

            application.owner = request.user

            application.save()

            return redirect("application_list")

    else:

        form = ApplicationForm()

    return render(

        request,

        "applications/application_form.html",

        {"form": form},

    )

from .finder_filters import (
    METRO_AREAS, CITY_OPTIONS, METRO_STATES, US_STATES, location_state, matches_metro, company_key, numeric_job_ids, is_us_location, software_title_matches, graduate_only_listing
)

def listing_is_tracked(job, owner):

    applications = Application.objects.filter(owner=owner)

    link = job.get("link", "")

    if link and applications.filter(link=link).exists():

        return True

    if applications.filter(

        company__iexact=job["company"], role__iexact=job["role"]

    ).exists():

        return True



    job_ids = numeric_job_ids(job["role"], link)

    if not job_ids:

        return False



    for application in applications.only("company", "role", "link"):

        if company_key(application.company) != company_key(job["company"]):

            continue

        if job_ids & numeric_job_ids(application.role, application.link):

            return True

    return False





def tracked_company_keys(owner):

    return {

        company_key(name)

        for name in Application.objects.filter(owner=owner)

        .values_list("company", flat=True)

    }

@staff_member_required

def internship_finder(request):

    result_key = request.session.get("broad_finder_key")

    jobs = cache.get(result_key, []) if result_key else []

    selected_cities = request.session.get("broad_finder_cities", [])

    software_only = request.session.get("broad_finder_software_only", False)
    hide_graduate = request.session.get("broad_finder_hide_graduate", False)

    company_query = request.session.get("broad_finder_company", "")

    tracked_companies = tracked_company_keys(request.user)
    hidden_companies = list(HiddenCompany.objects.filter(owner=request.user).order_by("company", "pk"))
    hidden_keys = {entry.company_key for entry in hidden_companies}
    excluded_companies = tracked_companies | hidden_keys
    show_excluded = request.session.get("finder_show_excluded", False)
    if not show_excluded:
        jobs = [job for job in jobs if company_key(job["company"]) not in excluded_companies]

    if request.method == "POST":

        action = request.POST.get("action")

        results_url = reverse("internship_finder")
        if request.GET.get("page"):
            results_url += "?" + urlencode({"page": request.GET["page"]})

        if action == "toggle_excluded":
            request.session["finder_show_excluded"] = request.POST.get("show_excluded") == "on"
            return redirect(results_url)

        if action == "hide_company":
            selected = next((job for job in jobs if job["id"] == request.POST.get("job_id")), None)
            if selected is None:
                messages.error(request, "This result is no longer available. Please search again.")
            else:
                HiddenCompany.objects.get_or_create(
                    owner=request.user,
                    company_key=company_key(selected["company"]),
                    defaults={"company": selected["company"]},
                )
                messages.success(request, f'{selected["company"]} hidden.')
            return redirect(results_url)

        if action == "unhide_company":
            HiddenCompany.objects.filter(
                owner=request.user, company_key=request.POST.get("company_key", ""),
            ).delete()
            return redirect(results_url)

        if action == "save":

            selected = next(

                (

                    job for job in jobs

                    if job["id"] == request.POST.get("job_id")

                ),

                None,

            )

            if selected is None:

                messages.error(request, "Results expired. Please search again.")

            elif listing_is_tracked(selected, request.user):

                messages.info(request, "This opportunity is already tracked.")

            else:

                application = Application(

                    owner=request.user,

                    company=selected["company"],

                    role=selected["role"],

                    status="Saved",

                    link=selected["link"],

                    location=selected["location"],

                )

                try:

                    application.full_clean()

                    application.save()

                except ValidationError as error:

                    messages.error(request, f"Could not save: {error}")

                else:

                    messages.success(request, "Opportunity saved.")

            return redirect(results_url)

        if action == "search":

            selected_cities = [

                city for city in request.POST.getlist("cities")

                if city in CITY_OPTIONS

            ]

            software_only = request.POST.get("software_only") == "on"
            hide_graduate = request.POST.get("hide_graduate") == "on"

            company_query = request.POST.get("company", "").strip()[:200]

            from .job_sources import get_feed, filter_jobs

            try:
                feed = get_feed()
            except (ValueError, OSError):
                messages.error(request, "Could not load employer sources. Check the board configuration.")
                return redirect("internship_finder")
            failed = sum(source["state"] != "available" for source in feed["sources"])
            if failed:
                messages.warning(request, f"{failed} listing sources could not refresh. Cached results are labeled when available.")
            jobs = filter_jobs(
                feed, selected_cities, company_query, software_only, hide_graduate,
            )
            request.session["finder_sources"] = feed["sources"]

            result_key = f"internship_results_{uuid4().hex}"

            cache.set(result_key, jobs, 3600)

            request.session["broad_finder_key"] = result_key

            request.session["broad_finder_cities"] = selected_cities

            request.session["broad_finder_software_only"] = software_only
            request.session["broad_finder_hide_graduate"] = hide_graduate

            request.session["broad_finder_company"] = company_query

            return redirect("internship_finder")

    page = Paginator(jobs, 25).get_page(request.GET.get("page"))
    for job in page.object_list:
        key = company_key(job["company"])
        job["company_hidden"] = key in hidden_keys
        job["company_tracked"] = key in tracked_companies
        job["tracked"] = job["company_tracked"] and listing_is_tracked(job, request.user)


    return render(

        request,

        "applications/internship_finder.html",

        {

            "company_query": company_query,
            "hidden_companies": hidden_companies,
            "show_excluded": show_excluded,

            "cities": CITY_OPTIONS,

            "selected_cities": selected_cities,

            "hide_graduate": hide_graduate,
            "software_only": software_only,

            "jobs": page,

            "page_obj": page,

            "total": len(jobs),

            "searched": bool(result_key),
            "sources": request.session.get("finder_sources", []),

        },

    )

def pasted_email_seen(email_id, owner):

    for metadata in Application.objects.filter(owner=owner).values_list("email_metadata", flat=True):

        metadata = metadata or {}

        if email_id in (

            metadata.get("source_email_id"),

            metadata.get("last_update_email_id"),

        ):

            return True

        if any(

            event.get("message_id") == email_id

            for event in metadata.get("email_history", [])

        ):

            return True

    return False

def read_uploaded_email(uploaded):

    message = BytesParser(policy=policy.default).parsebytes(uploaded.read())

    subject = str(message.get("Subject", "")).strip()

    sender = str(message.get("From", "")).strip()

    try:

        sent_at = parsedate_to_datetime(str(message.get("Date", "")))

        if timezone.is_aware(sent_at):

            sent_at = timezone.localtime(sent_at)

        email_date = sent_at.date()

    except (ValueError, TypeError, OverflowError):

        raise ValueError(

            "The email has no valid date. Use the paste form instead."

        )

    plain_parts = []

    html_parts = []

    for part in message.walk():

        if part.is_multipart():

            continue

        if part.get_content_disposition() == "attachment":

            continue

        content_type = part.get_content_type()

        if content_type not in ("text/plain", "text/html"):

            continue

        payload = part.get_payload(decode=True)

        if payload is None:

            continue

        charset = part.get_content_charset() or "utf-8"

        try:

            text = payload.decode(charset, errors="replace")

        except LookupError:

            text = payload.decode("utf-8", errors="replace")

        if content_type == "text/plain":

            plain_parts.append(text)

        else:

            html_parts.append(text)

    plain_body = "\n".join(plain_parts).strip()
    html_body = BeautifulSoup(
        "\n".join(html_parts), "html.parser"
    ).get_text(separator=" ", strip=True)
    body = "\n".join(part for part in (plain_body, html_body) if part).strip()
    if not body:

        raise ValueError("No readable email body was found.")

    return {

        "subject": subject,

        "sender": sender,

        "email_date": email_date.isoformat(),

        "body": body,

    }

@staff_member_required

def import_email(request):

    email_form = PastedEmailForm(

        initial={"email_date": timezone.localdate()}

    )

    upload_form = EmailUploadForm()

    preview_form = None

    email = request.session.get("pasted_email_preview")

    if request.method == "POST":

        action = request.POST.get("action")

        preview_data = request.POST

        if action == "upload":

            upload_form = EmailUploadForm(request.POST, request.FILES)

            if upload_form.is_valid():

                try:

                    preview_data = read_uploaded_email(

                        upload_form.cleaned_data["email_file"]

                    )

                except ValueError as error:

                    upload_form.add_error("email_file", str(error))

                else:

                    action = "preview"

        if action == "preview":

            email_form = PastedEmailForm(preview_data)

            if email_form.is_valid():

                data = email_form.cleaned_data

                body = " ".join(data["body"].split())

                subject = " ".join(data["subject"].split())

                sender = data["sender"].strip()

                fingerprint = hashlib.sha256(

                    "\n".join([

                        subject,

                        sender.casefold(),

                        data["email_date"].isoformat(),

                        body,

                    ]).encode("utf-8")

                ).hexdigest()

                email_id = f"paste:{fingerprint}"

                if pasted_email_seen(email_id, request.user):

                    messages.info(

                        request, "This email has already been saved."

                    )

                    return redirect("import_email")

                if "we saved a draft of your job application" in body.lower():

                    messages.error(

                        request,

                        "This is an unfinished application reminder. "

                        "Use the submission confirmation instead.",

                    )

                    return redirect("import_email")

                company = detect_company(
                    subject, sender, body,
                    Application.objects.filter(owner=request.user).values_list("company", flat=True),
                )

                role = suggest_role(body)

                matches = [

                    item

                    for item in Application.objects.filter(

                        owner=request.user,

                        company__iexact=company

                    )

                    if role

                    and matching_role(item.role) == matching_role(role)

                ]

                status = detect_status(subject, body)
                email = {

                    "message_id": email_id,

                    "subject": subject,

                    "email_date": data["email_date"].isoformat(),
                    "review_notes": review_notes(company, role, status),

                }

                request.session["pasted_email_preview"] = email

                preview_form = EmailPreviewForm(owner=request.user, initial={

                    "application": matches[0].pk if len(matches) == 1 else None,

                    "company": company,

                    "role": role,

                    "status": status,

                    "date_applied": (

                        data["email_date"]

                        if status == "Applied" and not matches

                        else None

                    ),

                })

                messages.info(

                    request,

                    "Check the application, role, and status before saving. "

                    "Assessment invitations are not necessarily interviews.",

                )

        elif action == "save":

            if not email:

                messages.error(request, "Import an email and preview it first.")

                return redirect("import_email")

            if pasted_email_seen(email["message_id"], request.user):

                messages.info(request, "This email is already saved.")

                return redirect("import_email")

            preview_form = EmailPreviewForm(request.POST, owner=request.user)

            if preview_form.is_valid():

                data = preview_form.cleaned_data

                application = data["application"]

                creating = application is None

                if creating:

                    duplicates = [

                        item

                        for item in Application.objects.filter(

                            owner=request.user,

                            company__iexact=data["company"]

                        )

                        if matching_role(item.role) == matching_role(data["role"])

                    ]

                    if duplicates:

                        preview_form.add_error(

                            "application",

                            "This company and role already exist. "

                            "Select the existing application above.",

                        )

                    else:

                        application = Application(

                            owner=request.user,

                            company=data["company"],

                            role=data["role"],

                            date_applied=data["date_applied"],

                        )

                if not preview_form.errors:

                    application.status = data["status"]

                    metadata = dict(application.email_metadata or {})

                    history = list(metadata.get("email_history", []))

                    history.append({

                        **email,

                        "status": data["status"],

                    })

                    metadata["email_history"] = history

                    metadata["last_update_email_id"] = email["message_id"]

                    metadata["last_update_email_date"] = email["email_date"]

                    metadata["manual_status_date"] = (

                        timezone.localdate().isoformat()

                    )

                    if creating:

                        metadata["source_email_id"] = email["message_id"]

                        metadata["source_email_subject"] = email["subject"]

                        metadata["source_email_date"] = email["email_date"]

                    application.email_metadata = metadata

                    try:

                        application.full_clean()

                        application.save()

                    except ValidationError as error:

                        preview_form.add_error(None, str(error))

                    else:

                        request.session.pop("pasted_email_preview", None)

                        messages.success(request, "Email changes saved.")

                        return redirect("import_email")

    return render(

        request,

        "applications/import_email.html",

        {

            "email_form": email_form,

            "upload_form": upload_form,

            "preview_form": preview_form,

            "email": email,

        },

    )
