"""Public, read-only demo using fictional data rather than database records."""
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone

from django.shortcuts import render
from django.views.decorators.http import require_safe

from .dashboard_views import build_flow
from .models import Application


@dataclass(frozen=True)
class DemoHistoryEntry:
    status: str
    recorded_at: datetime
    is_baseline: bool = False

    def get_status_display(self):
        return dict(Application.STATUS_CHOICES).get(self.status, self.status)


@dataclass(frozen=True)
class DemoHistory:
    entries: tuple

    def all(self):
        return self.entries


@dataclass(frozen=True)
class DemoApplication:
    pk: int
    company: str
    role: str
    status: str
    date_applied: date | None
    status_history: DemoHistory

    def get_status_display(self):
        return dict(Application.STATUS_CHOICES).get(self.status, self.status)


def sample_applications():
    rows = [
        ('Aster Labs', 'Software Engineering Intern', ('Applied', 'Assessment', 'First Interview', 'Second Interview', 'Final Interview', 'Offer')),
        ('Birch Systems', 'Backend Developer Intern', ('Applied', 'Assessment', 'Rejected')),
        ('Cedar Cloud', 'Software Engineering Intern', ('Applied', 'First Interview', 'Second Interview')),
        ('Delta Robotics', 'Software Developer Intern', ('Applied',)),
        ('Elm Analytics', 'Platform Engineering Intern', ('Applied', 'Assessment')),
        ('Fable Software', 'Full Stack Developer Intern', ('Saved',)),
        ('Grove Networks', 'Software Engineering Intern', ('Applied', 'First Interview', 'Rejected')),
        ('Harbor Digital', 'Backend Engineering Intern', ('Applied', 'Assessment', 'First Interview')),
        ('Indigo Apps', 'Mobile Software Intern', ('Applied',)),
        ('Juniper Studio', 'Software Engineering Intern', ('Applied', 'First Interview', 'Second Interview', 'Final Interview')),
        ('Kite Computing', 'Software Developer Intern', ('Applied', 'Rejected')),
        ('Lumen Tools', 'Developer Tools Intern', ('Saved',)),
        ('Meadow Tech', 'Software Engineering Intern', ('Applied', 'Assessment', 'First Interview', 'Second Interview', 'Rejected')),
        ('Northstar Code', 'Software Engineering Intern', ('Applied', 'Interview')),
    ]
    applications = []
    for index, (company, role, statuses) in enumerate(rows, start=1):
        start_day = 1 + index
        history = DemoHistory(tuple(
            DemoHistoryEntry(status, datetime(2026, 9, start_day + step, 14, tzinfo=timezone.utc))
            for step, status in enumerate(statuses)
        ))
        applications.append(DemoApplication(
            pk=index, company=company, role=role, status=statuses[-1],
            date_applied=None if statuses[-1] == 'Saved' else date(2026, 9, start_day),
            status_history=history,
        ))
    return applications


@require_safe
def public_demo(request):
    """Accept GET/HEAD only; never read or write personal application data."""
    sort = request.GET.get('sort', 'company_asc')
    if sort not in {'company_asc', 'company_desc', 'date_asc', 'date_desc'}:
        sort = 'company_asc'
    applications = sample_applications()
    if sort.startswith('company'):
        applications.sort(key=lambda app: (app.company.casefold(), app.role.casefold()),
                          reverse=sort == 'company_desc')
    else:
        # Preserve missing dates at the end in either direction.
        applications.sort(key=lambda app: (
            app.date_applied is None,
            (app.date_applied.toordinal() * (-1 if sort == 'date_desc' else 1))
            if app.date_applied else 0,
            app.company.casefold(),
        ))
    counts = Counter(app.status for app in applications)
    return render(request, 'applications/public_demo.html', {
        'applications': applications,
        'total': len(applications),
        'cards': [{'label': label, 'count': counts[status]}
                  for status, label in Application.STATUS_CHOICES],
        'flow': build_flow(applications),
        'sort': sort,
        'company_next_sort': 'company_desc' if sort == 'company_asc' else 'company_asc',
        'date_next_sort': 'date_desc' if sort == 'date_asc' else 'date_asc',
        'company_aria_sort': 'ascending' if sort == 'company_asc' else 'descending' if sort == 'company_desc' else 'none',
        'date_aria_sort': 'ascending' if sort == 'date_asc' else 'descending' if sort == 'date_desc' else 'none',
    })
