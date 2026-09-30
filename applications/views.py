import hashlib
import re
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from uuid import uuid4
import requests
from bs4 import BeautifulSoup
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import redirect, render
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
from .models import Application
@staff_member_required
def application_list(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    applications = Application.objects.filter(owner=request.user).order_by("-id")
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
METRO_AREAS = {
    "Atlanta": ["Atlanta", "Alpharetta", "Marietta", "Duluth"],
    "Austin": ["Austin", "Round Rock"],
    "Boston": ["Boston", "Cambridge", "Somerville", "Waltham"],
    "Charlotte": ["Charlotte"],
    "Chicago": ["Chicago", "Evanston", "Schaumburg"],
    "Columbus": ["Columbus"],
    "Dallas–Fort Worth": [
        "Dallas", "Fort Worth", "Plano", "Irving", "Richardson",
    ],
    "Denver–Boulder": ["Denver", "Boulder", "Broomfield", "Aurora"],
    "Detroit–Ann Arbor": ["Detroit", "Ann Arbor", "Dearborn", "Troy"],
    "Houston": ["Houston"],
    "Indianapolis": ["Indianapolis", "Carmel", "Westfield"],
    "Kansas City": ["Kansas City", "Overland Park"],
    "Los Angeles": [
        "Los Angeles", "Santa Monica", "Culver City", "Pasadena",
    ],
    "Miami–Fort Lauderdale": [
        "Miami", "Fort Lauderdale", "Boca Raton",
    ],
    "Minneapolis–St. Paul": [
        "Minneapolis", "St. Paul", "Saint Paul", "Bloomington",
    ],
    "Nashville": ["Nashville", "Franklin"],
    "New York City": [
        "New York", "NYC", "Brooklyn", "Jersey City", "Hoboken",
    ],
    "Philadelphia": ["Philadelphia", "King of Prussia"],
    "Phoenix": ["Phoenix", "Tempe", "Scottsdale", "Chandler", "Mesa"],
    "Pittsburgh": ["Pittsburgh"],
    "Portland": ["Portland", "Hillsboro", "Beaverton"],
    "Raleigh–Durham": [
        "Raleigh", "Durham", "Cary", "Research Triangle Park",
    ],
    "Salt Lake City": ["Salt Lake City", "Lehi", "Draper", "Provo", "Sandy"],
    "San Francisco Bay Area": [
        "San Francisco", "San Jose", "Palo Alto", "Mountain View",
        "Sunnyvale", "Santa Clara", "Menlo Park", "Redwood City",
        "Foster City", "San Mateo", "Oakland", "Berkeley",
    ],
    "Seattle": ["Seattle", "Bellevue", "Redmond", "Kirkland"],
}
CITY_OPTIONS = list(METRO_AREAS)
METRO_STATES = {
    "Atlanta": {"GA"},
    "Austin": {"TX"},
    "Boston": {"MA"},
    "Charlotte": {"NC"},
    "Chicago": {"IL"},
    "Columbus": {"OH"},
    "Dallas–Fort Worth": {"TX"},
    "Denver–Boulder": {"CO"},
    "Detroit–Ann Arbor": {"MI"},
    "Houston": {"TX"},
    "Indianapolis": {"IN"},
    "Kansas City": {"MO", "KS"},
    "Los Angeles": {"CA"},
    "Miami–Fort Lauderdale": {"FL"},
    "Minneapolis–St. Paul": {"MN"},
    "Nashville": {"TN"},
    "New York City": {"NY", "NJ"},
    "Philadelphia": {"PA"},
    "Phoenix": {"AZ"},
    "Pittsburgh": {"PA"},
    "Portland": {"OR"},
    "Raleigh–Durham": {"NC"},
    "Salt Lake City": {"UT"},
    "San Francisco Bay Area": {"CA"},
    "Seattle": {"WA"},
}
US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}
DATASET_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/"
    "Summer2027-Internships/dev/.github/scripts/listings.json"
)
def location_state(location):
    match = re.search(
        r",\s*([A-Z]{2})(?:\s*,\s*(?:USA|US|United States))?\s*$",
        location,
        flags=re.IGNORECASE,
    )
    return match.group(1).upper() if match else ""
def matches_metro(location, metro):
    if location_state(location) not in METRO_STATES[metro]:
        return False
    city_text = location.split(",")[0].strip().casefold()
    return any(
        city_text == alias.casefold()
        for alias in METRO_AREAS[metro]
    )
def company_key(name):
    return re.sub(r"[^a-z0-9]", "", name.casefold())
def numeric_job_ids(role, link=""):
    # Long numeric requisition IDs; four-digit years are excluded.
    return set(re.findall(r"(?<![A-Za-z0-9])\d{6,}(?![A-Za-z0-9])", f"{role} {link}"))


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


def is_us_location(location):
    if re.search(r"\b(?:USA|United States)\b", location, re.IGNORECASE):
        return True
    return location_state(location) in US_STATES
def graduate_only_listing(listing):
    degrees = listing.get("degrees") or []
    if not isinstance(degrees, list) or not degrees:
        return False
    # Hide only when every stated degree is a graduate degree.
    return all(
        isinstance(degree, str)
        and re.fullmatch(
            r"masters?(?:degree)?|ms|msc|phd|doctorate|doctoral(?:degree)?",
            re.sub(r"[^a-z]", "", degree.casefold()),
        ) is not None
        for degree in degrees
    )


def applied_company_keys(owner):
    return {
        company_key(name)
        for name in Application.objects.filter(owner=owner).exclude(status="Saved")
        .values_list("company", flat=True)
    }
@staff_member_required
def internship_finder(request):
    result_key = request.session.get("broad_finder_key")
    jobs = cache.get(result_key, []) if result_key else []
    selected_cities = request.session.get("broad_finder_cities", [])
    hide_applied = request.session.get("broad_finder_hide_applied", False)
    hide_graduate = request.session.get("broad_finder_hide_graduate", False)
    company_query = request.session.get("broad_finder_company", "")
    if request.method == "POST":
        action = request.POST.get("action")
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
            return redirect("internship_finder")
        if action == "search":
            selected_cities = [
                city for city in request.POST.getlist("cities")
                if city in CITY_OPTIONS
            ]
            hide_applied = request.POST.get("hide_applied") == "on"
            hide_graduate = request.POST.get("hide_graduate") == "on"
            company_query = request.POST.get("company", "").strip()[:200]
            try:
                listings = cache.get("summer2027_source")
                if listings is None:
                    response = requests.get(DATASET_URL, timeout=20)
                    response.raise_for_status()
                    listings = response.json()
                    if not isinstance(listings, list):
                        raise ValueError("Unexpected dataset format.")
                    cache.set("summer2027_source", listings, 900)
            except (requests.RequestException, ValueError):
                messages.error(
                    request,
                    "Could not fetch internships. Please try again later.",
                )
                return redirect("internship_finder")
            applied_companies = applied_company_keys(request.user)
            jobs = []
            seen_links = set()
            for listing in listings:
                if not isinstance(listing, dict):
                    continue
                title = listing.get("title") or ""
                company = listing.get("company_name") or ""
                link = listing.get("url") or ""
                terms = listing.get("terms") or []
                if (
                    listing.get("active") is not True
                    or listing.get("is_visible") is not True
                    or "Summer 2027" not in terms
                    or listing.get("category") != "Software"
                    or not company
                    or not title
                    or not link.startswith("https://")
                    or link in seen_links
                ):
                    continue
                locations = [
                    location
                    for location in (listing.get("locations") or [])
                    if isinstance(location, str)
                    and is_us_location(location)
                ]
                if not locations:
                    continue
                if selected_cities and not any(
                    matches_metro(location, metro)
                    for metro in selected_cities
                    for location in locations
                ):
                    continue
                if hide_graduate and graduate_only_listing(listing):
                    continue
                if company_query and company_query.casefold() not in company.casefold():
                    continue
                if hide_applied and company_key(company) in applied_companies:
                    continue
                seen_links.add(link)
                jobs.append({
                    "id": str(listing.get("id") or link),
                    "company": company,
                    "role": title,
                    "location": "; ".join(locations),
                    "link": link,
                    "date_posted": listing.get("date_posted") or 0,
                })
            jobs.sort(key=lambda job: job["date_posted"], reverse=True)
            result_key = f"internship_results_{uuid4().hex}"
            cache.set(result_key, jobs, 3600)
            request.session["broad_finder_key"] = result_key
            request.session["broad_finder_cities"] = selected_cities
            request.session["broad_finder_hide_applied"] = hide_applied
            request.session["broad_finder_hide_graduate"] = hide_graduate
            request.session["broad_finder_company"] = company_query
            return redirect("internship_finder")
    applied_companies = applied_company_keys(request.user)
    page = Paginator(jobs, 25).get_page(request.GET.get("page"))
    for job in page.object_list:
        job["tracked"] = listing_is_tracked(job, request.user)
        job["company_applied"] = company_key(job["company"]) in applied_companies
    tracked_applications = Application.objects.none()
    if company_query:
        tracked_applications = Application.objects.filter(
            owner=request.user,
            company__icontains=company_query,
        ).order_by("company", "role", "-id")

    return render(
        request,
        "applications/internship_finder.html",
        {
            "company_query": company_query,
            "tracked_applications": tracked_applications,
            "cities": CITY_OPTIONS,
            "selected_cities": selected_cities,
            "hide_applied": hide_applied,
            "hide_graduate": hide_graduate,
            "jobs": page,
            "page_obj": page,
            "total": len(jobs),
            "searched": bool(result_key),
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
    body = "\n".join(plain_parts).strip()
    if not body:
        body = BeautifulSoup(
            "\n".join(html_parts), "html.parser"
        ).get_text(separator=" ", strip=True)
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
                company = suggest_company(subject, sender)
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
                if is_rejection(body):
                    status = "Rejected"
                elif re.search(
                    r"thank you for applying|thanks for applying|"
                    r"application received|received your application|"
                    r"application has been received|received your resume",
                    subject + " " + body,
                    flags=re.IGNORECASE,
                ):
                    status = "Applied"
                else:
                    status = ""
                email = {
                    "message_id": email_id,
                    "subject": subject,
                    "email_date": data["email_date"].isoformat(),
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
