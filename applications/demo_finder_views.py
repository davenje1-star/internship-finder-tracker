"""Public internship search with no account data or persistence actions."""
from urllib.parse import urlencode

import requests
from django.core.cache import cache
from django.core.paginator import Paginator
from django.shortcuts import render
from django.views.decorators.http import require_safe

from .views import (
    CITY_OPTIONS, DATASET_URL, graduate_only_listing,
    is_us_location, matches_metro, software_title_matches,
)


@require_safe
def public_finder(request):
    company_query = request.GET.get('company', '').strip()[:200]
    selected_cities = [city for city in request.GET.getlist('cities')
                       if city in CITY_OPTIONS]
    software_only = request.GET.get('software_only') == 'on'
    hide_graduate = request.GET.get('hide_graduate') == 'on'
    searched = request.GET.get('search') == '1'
    jobs = []
    error = ''
    if searched:
        try:
            listings = cache.get('summer2027_source')
            if listings is None:
                response = requests.get(DATASET_URL, timeout=20)
                response.raise_for_status()
                listings = response.json()
                if not isinstance(listings, list):
                    raise ValueError('Unexpected dataset format.')
                cache.set('summer2027_source', listings, 900)
            seen_links = set()
            for listing in listings:
                if not isinstance(listing, dict):
                    continue
                title = listing.get('title') or ''
                company = listing.get('company_name') or ''
                link = listing.get('url') or ''
                terms = listing.get('terms') or []
                if (listing.get('active') is not True
                    or listing.get('is_visible') is not True
                    or listing.get('category') != 'Software'
                    or not isinstance(terms, list) or 'Summer 2027' not in terms
                    or not isinstance(title, str) or not title
                    or not isinstance(company, str) or not company
                    or not isinstance(link, str) or not link.startswith('https://')
                    or link in seen_links):
                    continue
                locations = listing.get('locations') or []
                if not isinstance(locations, list):
                    continue
                locations = [location for location in locations
                             if isinstance(location, str) and is_us_location(location)]
                if not locations:
                    continue
                if selected_cities and not any(
                    matches_metro(location, metro)
                    for metro in selected_cities for location in locations
                ):
                    continue
                if company_query and company_query.casefold() not in company.casefold():
                    continue
                if software_only and not software_title_matches(title):
                    continue
                if hide_graduate and graduate_only_listing(listing):
                    continue
                posted = listing.get('date_posted') or 0
                if not isinstance(posted, (int, float)):
                    posted = 0
                seen_links.add(link)
                jobs.append({'company': company, 'role': title,
                             'location': '; '.join(locations), 'link': link,
                             'date_posted': posted})
            jobs.sort(key=lambda job: job['date_posted'], reverse=True)
        except (requests.RequestException, ValueError):
            error = 'Could not fetch internships. Please try again later.'
    page = Paginator(jobs, 25).get_page(request.GET.get('page'))
    params = [('search', '1'), ('company', company_query)]
    params.extend(('cities', city) for city in selected_cities)
    if software_only:
        params.append(('software_only', 'on'))
    if hide_graduate:
        params.append(('hide_graduate', 'on'))
    return render(request, 'applications/public_finder.html', {
        'company_query': company_query, 'selected_cities': selected_cities,
        'cities': CITY_OPTIONS, 'software_only': software_only,
        'hide_graduate': hide_graduate, 'searched': searched, 'error': error,
        'jobs': page, 'page_obj': page, 'total': len(jobs),
        'pagination_query': urlencode(params),
    })
