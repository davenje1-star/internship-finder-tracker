from django.shortcuts import render, redirect
from .models import Application
from django.db.models import Q
from .forms import ApplicationForm
import json
import re
from pathlib import Path

import requests

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from uuid import uuid4
from django.core.cache import cache
from django.core.paginator import Paginator
def application_list(request):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    applications = Application.objects.all().order_by("-id")

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
def application_create(request):
    if request.method == "POST":
        form = ApplicationForm(request.POST)

        if form.is_valid():
            form.save()
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
    "Dallas–Fort Worth": ["Dallas", "Fort Worth", "Plano", "Irving", "Richardson"],
    "Denver–Boulder": ["Denver", "Boulder", "Broomfield", "Aurora"],
    "Detroit–Ann Arbor": ["Detroit", "Ann Arbor", "Dearborn", "Troy"],
    "Houston": ["Houston"],
    "Indianapolis": ["Indianapolis", "Carmel", "Westfield"],
    "Kansas City": ["Kansas City", "Overland Park"],
    "Los Angeles": ["Los Angeles", "Santa Monica", "Culver City", "Pasadena"],
    "Miami–Fort Lauderdale": ["Miami", "Fort Lauderdale", "Boca Raton"],
    "Minneapolis–St. Paul": ["Minneapolis", "St. Paul", "Saint Paul", "Bloomington"],
    "Nashville": ["Nashville", "Franklin"],
    "New York City": ["New York", "NYC", "Brooklyn", "Jersey City", "Hoboken"],
    "Philadelphia": ["Philadelphia", "King of Prussia"],
    "Phoenix": ["Phoenix", "Tempe", "Scottsdale", "Chandler", "Mesa"],
    "Pittsburgh": ["Pittsburgh"],
    "Portland": ["Portland", "Hillsboro", "Beaverton"],
    "Raleigh–Durham": ["Raleigh", "Durham", "Cary", "Research Triangle Park"],
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

    city_text = location.split(",")[0].strip()

    return any(
        city_text.casefold() == alias.casefold()
        for alias in METRO_AREAS[metro]
    )

def company_key(name):
    return re.sub(r"[^a-z0-9]", "", name.casefold())


def listing_is_tracked(job):
    return (
        Application.objects.filter(link=job["link"]).exists()
        or Application.objects.filter(
            company__iexact=job["company"],
            role__iexact=job["role"],
        ).exists()
    )


DATASET_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/"
    "Summer2027-Internships/dev/.github/scripts/listings.json"
)

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}


def is_us_location(location):
    if re.search(r"\b(?:USA|United States)\b", location, re.IGNORECASE):
        return True

    match = re.search(r",\s*([A-Z]{2})\s*$", location)
    return bool(match and match.group(1) in US_STATES)


@staff_member_required
def internship_finder(request):
    result_key = request.session.get("broad_finder_key")
    jobs = cache.get(result_key, []) if result_key else []
    selected_cities = request.session.get("broad_finder_cities", [])
    hide_applied = request.session.get("broad_finder_hide_applied", False)

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
            elif listing_is_tracked(selected):
                messages.info(request, "This opportunity is already tracked.")
            else:
                application = Application(
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

            applied_companies = {
                company_key(name)
                for name in Application.objects.exclude(status="Saved")
                .values_list("company", flat=True)
            }

            jobs = []
            seen_links = set()

            for listing in listings:
                if not isinstance(listing, dict):
                    continue

                title = listing.get("title", "")
                company = listing.get("company_name", "")
                link = listing.get("url", "")
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
                    for location in listing.get("locations", [])
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

            return redirect("internship_finder")

    applied_companies = {
        company_key(name)
        for name in Application.objects.exclude(status="Saved")
        .values_list("company", flat=True)
    }

    page = Paginator(jobs, 25).get_page(request.GET.get("page"))

    for job in page.object_list:
        job["tracked"] = listing_is_tracked(job)
        job["company_applied"] = (
            company_key(job["company"]) in applied_companies
        )

    return render(
        request,
        "applications/internship_finder.html",
        {
            "cities": CITY_OPTIONS,
            "selected_cities": selected_cities,
            "hide_applied": hide_applied,
            "jobs": page,
            "page_obj": page,
            "total": len(jobs),
            "searched": bool(result_key),
        },
    )