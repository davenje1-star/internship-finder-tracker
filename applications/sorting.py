from django.db.models import Case, F, IntegerField, Value, When
from django.db.models.functions import Lower

from .models import Application


def application_ordering():
    stage = Case(*[When(status=value, then=Value(index))
                   for index, (value, _) in enumerate(Application.STATUS_CHOICES)],
                 default=Value(len(Application.STATUS_CHOICES)), output_field=IntegerField())
    company = [Lower('company').asc(), Lower('role').asc(), 'id']
    return {
        'newest': ['-id'],
        'company_asc': company,
        'company_desc': [Lower('company').desc(), Lower('role').asc(), 'id'],
        'date_asc': [F('date_applied').asc(nulls_last=True), *company],
        'date_desc': [F('date_applied').desc(nulls_last=True), *company],
        'status_asc': [stage.asc(), *company],
        'status_desc': [stage.desc(), *company],
    }


def sort_context(sort):
    context = {'sort': sort}
    for field in ('company', 'date', 'status'):
        context[field + '_next_sort'] = field + ('_desc' if sort == field + '_asc' else '_asc')
        context[field + '_aria_sort'] = ('ascending' if sort == field + '_asc' else
                                        'descending' if sort == field + '_desc' else 'none')
    return context
