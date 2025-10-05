from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db.models import Count
from datetime import timedelta

from .forms import (
    OutreachLeadForm,
    AddConnectionForm,
    ConnectionStatusForm,
    ConnectionEditForm
)
from .models import (
    OutreachLead,
    Connection,
    ChatScreenshot,
    ConnectionComment,
    ColdLead,
    CustomUser
)


# lead_management/views.py

from django.shortcuts import render



def index(request):
    return render(request, 'lead_management/index.html')

# ✅ Dashboard Redirection Based on Role
@login_required
def dashboard_redirect(request):
    role_map = {
        'super_admin': 'superadmin_dashboard',
        'project_manager': 'manager_dashboard',
        'community_builder': 'builder_dashboard',
        'editor': 'editor_dashboard'
    }
    return redirect(role_map.get(request.user.role, 'login'))

# ✅ Role-Based Dashboards
@login_required
def superadmin_dashboard(request): 
    return render(request, 'lead_management/superadmin_dashboard.html')

@login_required
def manager_dashboard(request):
    if request.user.role != 'project_manager':
        return render(request, '403.html')  # Optional: create this template later

    builders = CustomUser.objects.filter(role='community_builder', userprofile__isnull=False)
    editors = CustomUser.objects.filter(role='editor', userprofile__isnull=False)
    assigned_connections = Connection.objects.filter(added_by=request.user)

    context = {
        'builder_count': builders.count(),
        'editor_count': editors.count(),
        'assigned_connections_count': assigned_connections.count(),
        'team_members': list(builders) + list(editors)
    }
    return render(request, 'lead_management/project_managers/manager_dashboard.html', context)

@login_required
def editor_dashboard(request): 
    return render(request, 'lead_management/editor_dashboard.html')


# ✅ Builder Dashboard with Analytics
@login_required
def builder_dashboard(request):
    today = timezone.now()
    last_30_days = today - timedelta(days=30)
    total_leads = OutreachLead.objects.filter(added_by=request.user, date_added__gte=last_30_days).count()
    total_connections = Connection.objects.filter(added_by=request.user, date_connected__gte=last_30_days).count()

    status_counts = {
        status: Connection.objects.filter(added_by=request.user, status=status, date_connected__gte=last_30_days).count()
        for status in ['interested', 'not_interested', 'F1', 'F2', 'cold_lead']
    }

    return render(request, 'lead_management/builder_dashboard.html', {
        'total_leads': total_leads,
        'total_connections': total_connections,
        'status_counts': status_counts
    })

# ✅ Add Outreach Lead
@login_required
def add_lead(request):
    form = OutreachLeadForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        linkedin_url = form.cleaned_data['linkedin_url']
        if OutreachLead.objects.filter(linkedin_url=linkedin_url).exists():
            messages.error(request, "This LinkedIn profile already exists.")
        else:
            lead = form.save(commit=False)
            lead.added_by = request.user
            lead.save()
            messages.success(request, "Lead added successfully.")
            return redirect('builder_dashboard')
    return render(request, 'lead_management/add_lead.html', {'form': form})

# ✅ Check Duplicate LinkedIn URL (AJAX)
@login_required
def check_linkedin_url(request):
    exists = OutreachLead.objects.filter(linkedin_url=request.GET.get('linkedin_url')).exists()
    return JsonResponse({'exists': exists})

# ✅ List of Outreach Leads
@login_required
def outreach_lead_list(request):
    leads = OutreachLead.objects.filter(added_by=request.user).order_by('-date_added')
    return render(request, 'lead_management/outreach_lead_list.html', {'leads': leads})

# ✅ Convert Lead to Connection
@login_required
def add_connection(request, lead_id):
    outreach_lead = get_object_or_404(OutreachLead, id=lead_id)
    if hasattr(outreach_lead, 'connection'):
        messages.warning(request, "This lead has already been converted.")
        return redirect('outreach_lead_list')

    form = AddConnectionForm(request.POST or None, request.FILES or None, initial={
        'full_name': outreach_lead.full_name,
        'location': outreach_lead.location,
    })
    if request.method == 'POST' and form.is_valid():
        connection = form.save(commit=False)
        connection.outreach_lead = outreach_lead
        connection.added_by = request.user
        connection.save()
        messages.success(request, "Connection added.")
        return redirect('builder_dashboard')
    return render(request, 'lead_management/add_connection.html', {'form': form, 'outreach_lead': outreach_lead})

# ✅ View All Connections
@login_required
def connection_list(request):
    connections = Connection.objects.filter(added_by=request.user).order_by('-date_connected')
    return render(request, 'lead_management/connection_list.html', {
        'connections': connections,
        'status_choices': Connection.STATUS_CHOICES
    })

# ✅ Update Connection Status
@login_required
def update_connection_status(request, connection_id):
    connection = get_object_or_404(Connection, id=connection_id, added_by=request.user)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status != connection.status:
            connection.status = new_status
            connection.save()
            messages.success(request, f"Status updated to '{new_status}'.")
            if new_status == 'cold_lead':
                ColdLead.objects.get_or_create(connection=connection)
        else:
            messages.info(request, "Status unchanged.")
    return redirect('connection_list')

# ✅ View Analytics Chart Data
@login_required
def view_analytics(request):
    connections = Connection.objects.filter(added_by=request.user)
    chart_data = {
        s['status']: s['total']
        for s in connections.values('status').annotate(total=Count('id'))
    }
    return render(request, 'lead_management/analytics.html', {
        'chart_data': chart_data,
        'total_leads': OutreachLead.objects.filter(added_by=request.user).count(),
        'total_connections': connections.count()
    })

# ✅ Filter by Status for Charts
@login_required
def filter_connections_by_status(request, status):
    filtered = Connection.objects.filter(added_by=request.user, status=status).values(
        'full_name', 'linkedin_email', 'outreach_email', 'status', 'date_connected'
    )
    return JsonResponse(list(filtered), safe=False)

# ✅ Edit Connection Details
@login_required
def edit_connection(request, connection_id):
    connection = get_object_or_404(Connection, id=connection_id, added_by=request.user)
    form = ConnectionEditForm(request.POST or None, request.FILES or None, instance=connection)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Connection updated.")
        return redirect('connection_list')
    return render(request, 'lead_management/edit_connection.html', {
        'form': form,
        'connection': connection,
        'screenshots': connection.chat_screenshots.all()
    })

# ✅ AJAX: Upload Screenshot (one-by-one)
@login_required
@csrf_exempt
def upload_chat_screenshot(request, connection_id):
    if request.method == 'POST' and request.FILES.get('screenshot'):
        connection = get_object_or_404(Connection, id=connection_id, added_by=request.user)
        screenshot = ChatScreenshot.objects.create(image=request.FILES['screenshot'])
        connection.chat_screenshots.add(screenshot)
        return JsonResponse({'url': screenshot.image.url})
    return JsonResponse({'error': 'Invalid request'}, status=400)

# ✅ View Connection Detail with Screenshots and Comments
@login_required
def view_connection(request, connection_id):
    connection = get_object_or_404(Connection, id=connection_id, added_by=request.user)
    screenshots = connection.chat_screenshots.all()
    comments = ConnectionComment.objects.filter(connection=connection).select_related('author').order_by('timestamp')
    return render(request, 'lead_management/view_connection.html', {
        'connection': connection,
        'screenshots': screenshots,
        'comments': comments
    })

# ✅ AJAX: Add Threaded Comment
@require_POST
@login_required
def add_comment(request, connection_id):
    comment_text = request.POST.get('comment')
    parent_id = request.POST.get('parent_id')
    connection = get_object_or_404(Connection, id=connection_id)

    if comment_text:
        parent_comment = ConnectionComment.objects.filter(id=parent_id).first() if parent_id else None
        comment = ConnectionComment.objects.create(
            connection=connection,
            author=request.user,
            comment=comment_text,
            parent=parent_comment
        )
        return JsonResponse({
            'success': True,
            'id': comment.id,
            'author': comment.author.username,
            'timestamp': comment.timestamp.strftime('%b %d, %Y %I:%M %p'),
            'comment': comment.comment,
            'parent_id': parent_id
        })

    return JsonResponse({'success': False}, status=400)


@login_required
def add_editor(request):
    return render(request, 'lead_management/project_managers/add_editor.html')


@login_required
def add_builder(request):
    return render(request, 'lead_management/project_managers/add_builder.html')


@login_required
def assign_editor(request):
    return render(request, 'lead_management/project_managers/assign_editor.html')


@login_required
def view_team(request):
    return render(request, 'lead_management/project_managers/view_team.html')

@login_required
def manager_connection_list(request):
    if request.user.role != 'project_manager':
        return render(request, '403.html')

    # Get all builders assigned to this manager
    builder_ids = request.user.assigned_builders.values_list('user__id', flat=True)

    # Fetch all connections made by those builders
    connections = Connection.objects.filter(added_by__id__in=builder_ids)

    return render(request, 'lead_management/project_managers/manager_connections.html', {
        'connections': connections
    })

