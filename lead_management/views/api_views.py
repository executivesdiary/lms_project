# lead_management/views/api_views.py

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from ..models import Connection, CustomUser, UserProfile

User = get_user_model()

# ✅ AJAX: Assign an Editor to a Connection
@csrf_exempt
def assign_editor_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            connection_id = data.get('connection_id')
            editor_id = data.get('editor_id')

            if not connection_id or not editor_id:
                return JsonResponse({'success': False, 'error': 'Missing connection_id or editor_id'})

            connection = get_object_or_404(Connection, id=connection_id)
            editor = get_object_or_404(User, id=editor_id, role='editor')

            connection.assigned_editor = editor
            connection.save()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})


# ✅ Load available community builders and status options
@login_required
def get_filter_data(request):
    if request.user.role != 'project_manager':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    builders = UserProfile.objects.filter(
        project_manager=request.user,
        user__role='community_builder'
    ).select_related('user')

    builder_data = [{
        'id': builder.user.id,
        'name': builder.user.get_full_name() or builder.user.username
    } for builder in builders]

    status_data = [{'value': key, 'label': label} for key, label in Connection.STATUS_CHOICES]

    return JsonResponse({
        'builders': builder_data,
        'statuses': status_data
    })


# ✅ Filter connections (table-based pagination)
@login_required
def get_filtered_connections(request):
    if request.user.role != 'project_manager':
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    builder_id = request.GET.get('builder_id')
    status_value = request.GET.get('status')
    page_number = request.GET.get('page', 1)

    builder_user_ids = UserProfile.objects.filter(
        project_manager=request.user,
        user__role='community_builder'
    ).values_list('user__id', flat=True)

    connections = Connection.objects.filter(added_by__id__in=builder_user_ids)

    if builder_id:
        connections = connections.filter(added_by__id=builder_id)
    if status_value:
        connections = connections.filter(status=status_value)

    connections = connections.select_related('outreach_lead', 'added_by').order_by('-date_connected')

    # ✅ Use 20 per page for table layout
    paginator = Paginator(connections, 20)
    page_obj = paginator.get_page(page_number)

    conn_list = [{
        'id': conn.id,
        'full_name': conn.full_name,
        'linkedin_url': conn.outreach_lead.linkedin_url if conn.outreach_lead else '',
        'status': conn.status,
        'added_by': conn.added_by.get_full_name() or conn.added_by.username,
        'date_connected': conn.date_connected.strftime('%b %d, %Y'),
    } for conn in page_obj]

    return JsonResponse({
        'connections': conn_list,
        'has_next': page_obj.has_next()
    })
