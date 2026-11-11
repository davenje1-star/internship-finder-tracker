"""Public internship search with no account data or persistence actions."""
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.shortcuts import render
from django.views.decorators.http import require_safe

from .views import CITY_OPTIONS
from .job_sources import get_feed, filter_jobs


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
    sources = []
    if searched:
        try:
            feed = get_feed()
            sources = feed["sources"]
            jobs = filter_jobs(feed, selected_cities, company_query, software_only, hide_graduate)
        except (ValueError, OSError):
            error = "Could not load listing sources. Please try again later."
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
        'pagination_query': urlencode(params), 'sources': sources,
    })
