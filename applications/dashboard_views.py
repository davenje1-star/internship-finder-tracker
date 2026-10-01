from collections import Counter, defaultdict

from django.db.models import F
from django.db.models.functions import Lower

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import reverse

from .models import Application


COLORS = {
    'Saved': '#64748b', 'Applied': '#2563eb', 'Assessment': '#0891b2',
    'Interview': '#a16207', 'First Interview': '#a16207',
    'Second Interview': '#9333ea', 'Final Interview': '#7c3aed',
    'Rejected': '#dc2626', 'Offer': '#16a34a',
}


def build_flow(applications):
    """Use event position as the column, so corrections never create cycles."""
    nodes = Counter()
    edges = Counter()
    root = (0, 'All tracked applications')
    for application in applications:
        statuses = [entry.status for entry in application.status_history.all()]
        if not statuses or statuses[-1] != application.status:
            statuses.append(application.status)
        path = [root]
        for status in statuses:
            if len(path) > 1 and path[-1][1] == status:
                continue
            path.append((len(path), status))
        ending = ('Awaiting recorded update' if application.status == 'Applied'
                  else f'Current: {application.get_status_display()}')
        path.append((len(path), ending))
        nodes.update(path)
        edges.update(zip(path, path[1:]))
    if not nodes:
        return {'nodes': [], 'links': [], 'width': 900, 'height': 250}

    layers = defaultdict(list)
    for key in nodes:
        layers[key[0]].append(key)
    total = len(applications)
    scale = min(8, 400 / max(total, 1))
    gap = 34
    height = max(sum(nodes[key] * scale for key in keys) + gap * (len(keys) - 1)
                 for keys in layers.values()) + 100
    width = max(900, len(layers) * 260)
    positions = {}
    output_nodes = []
    for column, keys in layers.items():
        keys.sort(key=lambda key: key[1])
        occupied = sum(nodes[key] * scale for key in keys) + gap * (len(keys) - 1)
        y = (height - occupied) / 2
        for key in keys:
            x = 25 + column * 260
            h = nodes[key] * scale
            color_status = key[1].removeprefix('Current: ')
            color = COLORS.get(color_status, '#475569')
            positions[key] = (x, y, h)
            output_nodes.append({'x': x, 'y': y, 'height': h, 'label': key[1],
                                 'count': nodes[key], 'color': color,
                                 'label_x': x + 24, 'label_y': y + h / 2 + 4})
            y += h + gap
    outgoing = defaultdict(float)
    incoming = defaultdict(float)
    output_links = []
    for (source, target), count in sorted(edges.items()):
        x1, y1, _ = positions[source]
        x2, y2, _ = positions[target]
        thickness = count * scale
        y1 += outgoing[source] + thickness / 2
        y2 += incoming[target] + thickness / 2
        outgoing[source] += thickness
        incoming[target] += thickness
        middle = (x1 + 16 + x2) / 2
        output_links.append({'path': f'M {x1 + 16} {y1} C {middle} {y1}, {middle} {y2}, {x2} {y2}',
                             'width': thickness, 'count': count,
                             'label': f'{source[1]} → {target[1]}',
                             'color': COLORS.get(target[1], '#64748b')})
    return {'nodes': output_nodes, 'links': output_links, 'width': width, 'height': height}


@staff_member_required
def progress_dashboard(request):
    sort = request.POST.get('sort', '') if request.method == 'POST' else request.GET.get('sort', '')
    allowed_sorts = {'company_asc', 'company_desc', 'date_asc', 'date_desc'}
    if sort not in allowed_sorts:
        sort = 'company_asc'
    redirect_url = f"{reverse('progress_dashboard')}?sort={sort}"
    if request.method == 'POST':
        try:
            application_id = int(request.POST.get('application_id', ''))
        except (TypeError, ValueError):
            messages.error(request, 'Choose a valid application.')
            return redirect(redirect_url)
        application = get_object_or_404(Application, pk=application_id, owner=request.user)
        status = request.POST.get('status', '')
        if status not in dict(Application.STATUS_CHOICES):
            messages.error(request, 'Choose a valid status.')
        else:
            application.status = status
            fields = ['status']
            if status == 'Applied' and not application.date_applied:
                application.date_applied = timezone.localdate()
                fields.append('date_applied')
            application.save(update_fields=fields)
            messages.success(request, 'Status saved. Your progress chart is updated.')
        return redirect(redirect_url)

    ordering = {
        'company_asc': [Lower('company').asc(), Lower('role').asc(), 'id'],
        'company_desc': [Lower('company').desc(), Lower('role').asc(), 'id'],
        'date_asc': [F('date_applied').asc(nulls_last=True), Lower('company').asc(), 'id'],
        'date_desc': [F('date_applied').desc(nulls_last=True), Lower('company').asc(), 'id'],
    }
    applications = list(Application.objects.filter(owner=request.user)
                        .order_by(*ordering[sort]).prefetch_related('status_history'))
    counts = Counter(application.status for application in applications)
    return render(request, 'applications/progress_dashboard.html', {
        'applications': applications, 'total': len(applications),
        'sort': sort,
        'company_next_sort': 'company_desc' if sort == 'company_asc' else 'company_asc',
        'date_next_sort': 'date_desc' if sort == 'date_asc' else 'date_asc',
        'company_aria_sort': 'ascending' if sort == 'company_asc' else 'descending' if sort == 'company_desc' else 'none',
        'date_aria_sort': 'ascending' if sort == 'date_asc' else 'descending' if sort == 'date_desc' else 'none',

        'cards': [{'label': label, 'count': counts[status]} for status, label in Application.STATUS_CHOICES],
        'flow': build_flow(applications), 'status_choices': Application.STATUS_CHOICES,
    })
