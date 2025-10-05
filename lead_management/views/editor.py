# 
# File: editor.py
# Purpose: All views specific to the Editor role — dashboard, pending bios, and recursive threaded comments.
#

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from lead_management.models import Connection, ChatScreenshot, ConnectionComment
from executive_biographer.models import BiographyDraft
from django.urls import reverse


# ✅ Editor Dashboard Overview
@login_required
def editor_dashboard(request):
    if request.user.role != 'editor':
        return render(request, '403.html')

    editor = request.user

    assigned_connections = Connection.objects.filter(assigned_editor=editor)
    all_drafts = BiographyDraft.objects.filter(author=editor)

    published_count = all_drafts.filter(is_published=True).count()
    draft_connection_ids = all_drafts.values_list('connection_id', flat=True)
    pending_count = assigned_connections.exclude(id__in=draft_connection_ids).count()
    in_progress_count = all_drafts.filter(is_published=False).count()

    return render(request, 'lead_management/editor/editor_dashboard.html', {
        'published_count': published_count,
        'pending_count': pending_count,
        'in_progress_count': in_progress_count,
    })


# ✅ View List of Connections with No Biography Draft
@login_required
def pending_biographies(request):
    if request.user.role != 'editor':
        return render(request, '403.html')

    editor = request.user
    assigned_connections = Connection.objects.filter(assigned_editor=editor)
    drafted_ids = BiographyDraft.objects.filter(author=editor).values_list('connection_id', flat=True)
    pending_connections = assigned_connections.exclude(id__in=drafted_ids)

    return render(request, 'lead_management/editor/pending_bio.html', {
        'pending_connections': pending_connections
    })


# ✅ Utility: recursive comment tree builder
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


# ✅ Detailed View of Assigned Connection with Comments + Screenshots
@login_required
def editor_view_connection(request, connection_id):
    if request.user.role != 'editor':
        return render(request, '403.html')

    connection = get_object_or_404(Connection, pk=connection_id, assigned_editor=request.user)
    screenshots = ChatScreenshot.objects.filter(connections=connection)

    comments = ConnectionComment.objects.filter(
        connection=connection
    ).select_related('author', 'parent').order_by('timestamp')

    comment_tree = build_comment_tree(comments)
    comment_post_url = reverse('add_comment', args=[connection.id])

    return render(request, 'lead_management/editor/view_connection.html', {
        'connection': connection,
        'screenshots': screenshots,
        'comments': comment_tree,
        'comment_post_url': comment_post_url
    })
