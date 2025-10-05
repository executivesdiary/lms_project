# 
# File: project_manager.py
# Purpose: Views for the Project Manager role — dashboard, connections, and threaded comments (with recursive replies)
#

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta

from ..models import Connection, CustomUser, UserProfile, ConnectionComment, OutreachLead


# ✅ Utility: check if the user is a project manager
def is_project_manager(user):
    return user.is_authenticated and user.role == 'project_manager'


# ✅ PM Dashboard View
@login_required
def manager_dashboard(request):
    if not is_project_manager(request.user):
        return render(request, '403.html')

    builders = CustomUser.objects.filter(role='community_builder', userprofile__isnull=False)
    editors = CustomUser.objects.filter(role='editor', userprofile__isnull=False)
    assigned = Connection.objects.filter(added_by=request.user)

    return render(request, 'lead_management/project_managers/manager_dashboard.html', {
        'builder_count': builders.count(),
        'editor_count': editors.count(),
        'assigned_connections_count': assigned.count(),
        'team_members': list(builders) + list(editors)
    })


# ✅ Static Pages
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


# ✅ View Builder’s Dashboard (read-only)
@login_required
@user_passes_test(is_project_manager)
def view_builder_dashboard(request, builder_id):
    assigned = UserProfile.objects.filter(
        user_id=builder_id,
        project_manager=request.user,
        user__role='community_builder'
    ).exists()

    if not assigned:
        return render(request, '403.html')

    today = timezone.now()
    window = today - timedelta(days=30)

    total_leads = OutreachLead.objects.filter(
        added_by_id=builder_id,
        date_added__gte=window
    ).count()

    total_connections = Connection.objects.filter(
        added_by_id=builder_id,
        date_connected__gte=window
    ).count()

    status_counts = {
        status: Connection.objects.filter(
            added_by_id=builder_id,
            status=status,
            date_connected__gte=window
        ).count()
        for status in ['interested', 'not_interested', 'F1', 'F2', 'cold_lead']
    }

    return render(request, 'lead_management/community_builder/builder_dashboard.html', {
        'total_leads': total_leads,
        'total_connections': total_connections,
        'status_counts': status_counts,
        'readonly': True
    })


# ✅ View all connections from team (with pagination)
@login_required
def view_team_connections(request):
    if not is_project_manager(request.user):
        return render(request, '403.html')

    builder_user_ids = UserProfile.objects.filter(
        project_manager=request.user,
        user__role='community_builder'
    ).values_list('user__id', flat=True)

    connections = Connection.objects.filter(
        added_by_id__in=builder_user_ids
    ).select_related('added_by').order_by('-date_connected')

    editors = CustomUser.objects.filter(role='editor')

    paginator = Paginator(connections, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'lead_management/project_managers/manager_connections.html', {
        'page_obj': page_obj,
        'connections': page_obj.object_list,
        'editors': editors
    })


# ✅ Utility function to build recursive comment tree
def build_comment_tree(comments):
    comment_lookup = {c.id: c for c in comments}
    for comment in comments:
        comment.thread_replies = []
    root_comments = []

    for comment in comments:
        if comment.parent_id:
            parent = comment_lookup.get(comment.parent_id)
            if parent:
                parent.thread_replies.append(comment)
        else:
            root_comments.append(comment)

    return root_comments


# ✅ View a single connection record with comments and screenshots
@login_required
@user_passes_test(is_project_manager)
def manager_view_connection(request, connection_id):
    connection = get_object_or_404(Connection, pk=connection_id)

    comments = ConnectionComment.objects.filter(
        connection=connection
    ).select_related('author', 'parent').order_by('timestamp')

    comment_tree = build_comment_tree(comments)

    screenshots = connection.chat_screenshots.all()
    editors = get_user_model().objects.filter(role='editor')
    comment_post_url = reverse('manager_add_comment', args=[connection.id])

    return render(request, 'lead_management/project_managers/view_connection.html', {
        'connection': connection,
        'comments': comment_tree,
        'screenshots': screenshots,
        'available_editors': editors,
        'comment_post_url': comment_post_url,
    })


# ✅ Assign editor to a connection
@login_required
@user_passes_test(is_project_manager)
def assign_editor(request, connection_id):
    if request.method == 'POST':
        editor_id = request.POST.get('editor_id')
        try:
            editor = CustomUser.objects.get(id=editor_id, role='editor')
            connection = get_object_or_404(Connection, pk=connection_id)
            connection.assigned_editor = editor
            connection.save()
            messages.success(request, f"{editor.get_full_name() or editor.username} has been assigned.")
        except CustomUser.DoesNotExist:
            messages.error(request, "Editor not found.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
    return redirect(reverse('manager_view_connection', args=[connection_id]))


# ✅ Add threaded comment via AJAX (PM only)
@login_required
@require_POST
@user_passes_test(is_project_manager)
def manager_add_comment(request, connection_id):
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
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Empty comment'}, status=400)
