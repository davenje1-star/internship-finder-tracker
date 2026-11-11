from .sorting import application_ordering, sort_context
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
    'Rejected': '#dc2626', 'Ghosted': '#475569', 'Offer': '#16a34a',
}


STAGE_COLUMNS = {
    'Applied': 0, 'Assessment': 1, 'Interview': 2, 'First Interview': 2,
    'Second Interview': 3, 'Final Interview': 4,
}
OUTCOMES = {'Rejected', 'Ghosted', 'Offer'}
LABELS = dict(Application.STATUS_CHOICES)
LABELS['Interview'] = 'Interview (round unknown)'
LABELS.update({f'Current: {status}': f'Current: {LABELS[status]}' for status in STAGE_COLUMNS})



def application_path(application):
    if application.status == 'Saved':
        return []

    statuses = [entry.status for entry in application.status_history.all()]
    if not statuses or statuses[-1] != application.status:
        statuses.append(application.status)

    # Applied is the entry point, including for imported outcomes with no history.
    path = [(0, 'Applied')]
    for status in statuses:
        if status in {'Saved', 'Applied'}:
            path = [(0, 'Applied')]
        elif status in STAGE_COLUMNS:
            if path[-1][1] in OUTCOMES:
                path = [(0, 'Applied')]
            column = STAGE_COLUMNS[status]
            # A correction replaces any stage at or beyond its position.
            while path[-1][0] >= column:
                path.pop()
            path.append((column, status))
        elif status in OUTCOMES:
            # If an outcome was corrected, branch from the same recorded stage.
            if path[-1][1] in OUTCOMES:
                path.pop()
            column = 5 if status == 'Offer' else path[-1][0] + 1
            path.append((column, status))
    return path


def build_flow(applications):
    """Lay out advancing stages above separate Rejected and Ghosted lanes."""
    nodes = Counter()
    edges = Counter()
    root = (0, 'Applied')
    for application in applications:
        path = application_path(application)
        if path and path[-1][1] in STAGE_COLUMNS:
            column, status = path[-1]
            path.append((column + 1, f'Current: {status}'))
        nodes.update(path)
        edges.update(zip(path, path[1:]))

    if not nodes:
        return {'nodes': [], 'links': [], 'width': 900, 'height': 250}

    scale = min(8, 215 / nodes[root])
    column_width = 205
    gap = 28
    layers = defaultdict(list)
    for key in nodes:
        lane = key[1] if key[1] in {'Rejected', 'Ghosted'} else 'Progress'
        layers[lane, key[0]].append(key)

    positions = {}
    output_nodes = []
    lane_top = 25
    for lane in ('Progress', 'Rejected', 'Ghosted'):
        columns = {column: keys for (name, column), keys in layers.items() if name == lane}
        if not columns:
            continue
        heights = {
            column: sum(nodes[key] * scale for key in keys) + gap * (len(keys) - 1)
            for column, keys in columns.items()
        }
        lane_height = max(heights.values())
        for column, keys in sorted(columns.items()):
            x = 25 + column * column_width
            y = lane_top
            for key in sorted(keys, key=lambda key: (key[1].startswith('Current: '), key[1])):
                status = key[1]
                h = nodes[key] * scale
                bar_width = 30 if key == root else 16
                positions[key] = (x, y, bar_width)
                output_nodes.append({
                    'x': x, 'y': y, 'width': bar_width, 'height': h, 'label': LABELS[status],
                    'count': nodes[key], 'color': COLORS[status.removeprefix('Current: ')],
                    'label_x': x + bar_width + 8, 'label_y': y + h / 2 + 4,
                })
                y += h + gap
        lane_bottom = lane_top + lane_height
        lane_top = lane_bottom + (72 if lane == 'Progress' else 28)

    # Allocate each side independently so bands stack in visual lane order.
    outgoing = defaultdict(float)
    incoming = defaultdict(float)
    starts = {}
    ends = {}
    for source, target in sorted(edges, key=lambda edge: (positions[edge[1]][1], edge[1])):
        thickness = edges[source, target] * scale
        starts[source, target] = positions[source][1] + outgoing[source] + thickness / 2
        outgoing[source] += thickness
    for source, target in sorted(edges, key=lambda edge: (positions[edge[0]][1], edge[0])):
        thickness = edges[source, target] * scale
        ends[source, target] = positions[target][1] + incoming[target] + thickness / 2
        incoming[target] += thickness

    output_links = []
    for (source, target), count in sorted(edges.items()):
        source_x, _, source_width = positions[source]
        x1 = source_x + source_width
        x2 = positions[target][0]
        y1, y2 = starts[source, target], ends[source, target]
        middle = (x1 + x2) / 2
        output_links.append({
            'path': f'M {x1} {y1} C {middle} {y1}, {middle} {y2}, {x2} {y2}',
            'width': count * scale, 'count': count,
            'label': f'{LABELS[source[1]]} → {LABELS[target[1]]}',
            'color': COLORS[target[1].removeprefix('Current: ')],
        })
    return {
        'nodes': output_nodes, 'links': output_links,
        'width': max(660, max(key[0] for key in nodes) * column_width + 235),
        'height': max(140, lane_bottom + 28),
    }


@staff_member_required
def progress_dashboard(request):
    sort = request.POST.get('sort', '') if request.method == 'POST' else request.GET.get('sort', '')
    allowed_sorts = {'company_asc', 'company_desc', 'date_asc', 'date_desc', 'status_asc', 'status_desc'}
    if sort not in allowed_sorts:
        sort = 'status_desc'
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

    ordering = application_ordering()
    applications = list(Application.objects.filter(owner=request.user)
                        .order_by(*ordering[sort]).prefetch_related('status_history'))
    counts = Counter(application.status for application in applications)
    return render(request, 'applications/progress_dashboard.html', {
        'applications': applications, 'total': len(applications),
        **sort_context(sort),
        'company_next_sort': 'company_desc' if sort == 'company_asc' else 'company_asc',
        'date_next_sort': 'date_desc' if sort == 'date_asc' else 'date_asc',
        'company_aria_sort': 'ascending' if sort == 'company_asc' else 'descending' if sort == 'company_desc' else 'none',
        'date_aria_sort': 'ascending' if sort == 'date_asc' else 'descending' if sort == 'date_desc' else 'none',

        'cards': [{'label': label, 'count': counts[status]} for status, label in Application.STATUS_CHOICES],
        'flow': build_flow(applications), 'status_choices': Application.STATUS_CHOICES,
    })
