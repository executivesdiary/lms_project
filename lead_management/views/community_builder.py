from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Count
from datetime import timedelta
import csv
import io


from ..forms import OutreachLeadForm, AddConnectionForm, ConnectionEditForm
from ..models import (
    OutreachLead, Connection, ChatScreenshot, ConnectionComment,
    ColdLead, LinkedInConnection
)

# -------------------- Utility --------------------

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

# -------------------- Dashboard --------------------

@login_required
def builder_dashboard(request):
    today = timezone.now()
    window = today - timedelta(days=30)
    total_leads = OutreachLead.objects.filter(added_by=request.user, date_added__gte=window).count()
    total_connections = Connection.objects.filter(added_by=request.user, date_connected__gte=window).count()
    status_counts = {
        status: Connection.objects.filter(
            added_by=request.user, status=status, date_connected__gte=window
        ).count() for status in ['interested', 'not_interested', 'F1', 'F2', 'cold_lead']
    }
    return render(request, 'lead_management/community_builder/builder_dashboard.html', {
        'total_leads': total_leads,
        'total_connections': total_connections,
        'status_counts': status_counts,
    })

# -------------------- Lead Management --------------------

@login_required
def add_lead(request):
    form = OutreachLeadForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        url = form.cleaned_data['linkedin_url']
        if OutreachLead.objects.filter(linkedin_url=url).exists():
            messages.error(request, "This LinkedIn profile already exists.")
        else:
            lead = form.save(commit=False)
            lead.added_by = request.user
            lead.save()
            messages.success(request, "Lead added successfully.")
            return redirect('builder_dashboard')
    return render(request, 'lead_management/community_builder/add_lead.html', {'form': form})

@login_required
def check_linkedin_url(request):
    exists = OutreachLead.objects.filter(linkedin_url=request.GET.get('linkedin_url')).exists()
    return JsonResponse({'exists': exists})

@login_required
def outreach_lead_list(request):
    leads = OutreachLead.objects.filter(added_by=request.user).order_by('-date_added')
    return render(request, 'lead_management/community_builder/outreach_lead_list.html', {'leads': leads})

# -------------------- Connection --------------------

@login_required
def add_connection(request, lead_id):
    lead = get_object_or_404(OutreachLead, id=lead_id)
    if hasattr(lead, 'connection'):
        messages.warning(request, "This lead has already been converted.")
        return redirect('outreach_lead_list')

    form = AddConnectionForm(request.POST or None, request.FILES or None, initial={
        'full_name': lead.full_name, 'location': lead.location
    })
    if request.method == 'POST' and form.is_valid():
        conn = form.save(commit=False)
        conn.outreach_lead = lead
        conn.added_by = request.user
        conn.save()
        messages.success(request, "Connection added.")
        return redirect('builder_dashboard')

    return render(request, 'lead_management/community_builder/add_connection.html', {
        'form': form, 'outreach_lead': lead,
    })

@login_required
def connection_list(request):
    conns = Connection.objects.filter(added_by=request.user).order_by('-date_connected')
    return render(request, 'lead_management/community_builder/connection_list.html', {
        'connections': conns, 'status_choices': Connection.STATUS_CHOICES,
    })

@login_required
def update_connection_status(request, connection_id):
    conn = get_object_or_404(Connection, id=connection_id, added_by=request.user)
    if request.method == 'POST':
        new = request.POST.get('status')
        if new != conn.status:
            conn.status = new
            conn.save()
            if new == 'cold_lead':
                ColdLead.objects.get_or_create(connection=conn)
            messages.success(request, f"Status updated to '{new}'.")
        else:
            messages.info(request, "Status unchanged.")
    return redirect('connection_list')

# -------------------- Analytics --------------------

@login_required
def view_analytics(request):
    conns = Connection.objects.filter(added_by=request.user)
    chart_data = {
        entry['status']: entry['total']
        for entry in conns.values('status').annotate(total=Count('id'))
    }
    return render(request, 'lead_management/community_builder/analytics.html', {
        'chart_data': chart_data,
        'total_leads': OutreachLead.objects.filter(added_by=request.user).count(),
        'total_connections': conns.count(),
    })

@login_required
def filter_connections_by_status(request, status):
    data = Connection.objects.filter(added_by=request.user, status=status).values(
        'full_name', 'linkedin_email', 'outreach_email', 'status', 'date_connected')
    return JsonResponse(list(data), safe=False)

# -------------------- Edit & View --------------------

@login_required
def edit_connection(request, connection_id):
    conn = get_object_or_404(Connection, id=connection_id, added_by=request.user)
    form = ConnectionEditForm(request.POST or None, request.FILES or None, instance=conn)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Connection updated.")
        return redirect('connection_list')
    return render(request, 'lead_management/community_builder/edit_connection.html', {
        'form': form, 'connection': conn, 'screenshots': conn.chat_screenshots.all(),
    })

@login_required
@csrf_exempt
def upload_chat_screenshot(request, connection_id):
    if request.method == 'POST' and request.FILES.get('screenshot'):
        conn = get_object_or_404(Connection, id=connection_id, added_by=request.user)
        shot = ChatScreenshot.objects.create(image=request.FILES['screenshot'])
        conn.chat_screenshots.add(shot)
        return JsonResponse({'url': shot.image.url})
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def view_connection(request, connection_id):
    conn = get_object_or_404(Connection, id=connection_id, added_by=request.user)
    comments = ConnectionComment.objects.filter(
        connection=conn).select_related('author', 'parent').order_by('timestamp')
    return render(request, 'lead_management/community_builder/view_connection.html', {
        'connection': conn, 'screenshots': conn.chat_screenshots.all(),
        'comments': build_comment_tree(comments),
    })

@login_required
@require_POST
def add_comment(request, connection_id):
    comment_text = request.POST.get('comment')
    parent_id = request.POST.get('parent_id')
    connection = get_object_or_404(Connection, id=connection_id)
    if comment_text:
        parent_comment = ConnectionComment.objects.filter(id=parent_id).first() if parent_id else None
        comment = ConnectionComment.objects.create(
            connection=connection, author=request.user, comment=comment_text, parent=parent_comment
        )
        return JsonResponse({
            'success': True, 'id': comment.id, 'author': comment.author.username,
            'timestamp': comment.timestamp.strftime('%b %d, %Y %I:%M %p'),
            'comment': comment.comment, 'parent_id': parent_id
        })
    return JsonResponse({'success': False}, status=400)

# -------------------- LinkedIn CSV --------------------


@login_required
def upload_linkedin_connections(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a valid CSV file.')
            return redirect('upload_linkedin_connections')

        decoded_file = csv_file.read().decode('utf-8')
        text_stream = io.StringIO(decoded_file)
        raw_reader = csv.reader(text_stream)
        rows = list(raw_reader)

        # Sanitize headers
        headers = [h.strip().replace('\xa0', ' ').replace(' ', ' ') for h in rows[0]]
        rows = rows[1:]  # skip header
        reader = [dict(zip(headers, r)) for r in rows if any(r)]

        count_created = 0
        count_skipped = 0

        for row in reader:
            linkedin_url = row.get('URL', '').strip().lower().rstrip('/')
            if not linkedin_url:
                continue

            if LinkedInConnection.objects.filter(linkedin_url=linkedin_url, community_builder=request.user).exists():
                count_skipped += 1
                continue

            try:
                connected_on = row.get('Connected On', '').strip()
                parsed_date = timezone.datetime.strptime(connected_on, "%d-%b-%y").date() if connected_on else None
            except Exception:
                try:
                    parsed_date = timezone.datetime.strptime(connected_on, "%d-%b-%Y").date()
                except:
                    parsed_date = None

            LinkedInConnection.objects.create(
                community_builder=request.user,
                first_name=row.get('First Name', '').strip(),
                last_name=row.get('Last Name', '').strip(),
                linkedin_url=linkedin_url,
                email=row.get('Email Address', '').strip() or None,
                company=row.get('Company', '').strip(),
                position=row.get('Position', '').strip(),
                connected_on=parsed_date
            )
            count_created += 1

        messages.success(request, f"{count_created} uploaded, {count_skipped} duplicates skipped.")
        return redirect('uploaded_connections_page')

    return render(request, 'lead_management/community_builder/upload_connections.html')


# -------------------- Uploaded Connections Page --------------------

@login_required
def uploaded_connections_page(request):
    return render(request, 'lead_management/community_builder/uploaded_connection.html')

@login_required
def get_uploaded_connections(request):
    page = request.GET.get('page', 1)
    per_page = 50
    all_connections = LinkedInConnection.objects.filter(community_builder=request.user).order_by('-created_at')
    paginator = Paginator(all_connections, per_page)
    page_obj = paginator.get_page(page)

    data = []
    for conn in page_obj:
        data.append({
            'id': conn.id,
            'name': f"{conn.first_name} {conn.last_name}",
            'email': conn.email or '',
            'company': conn.company or '',
            'position': conn.position or '',
            'connected_on': conn.connected_on.strftime('%b %d, %Y') if conn.connected_on else '',
            'linkedin_url': conn.linkedin_url,
        })

    return JsonResponse({
        'results': data,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'current_page': page_obj.number,
        'num_pages': paginator.num_pages,
    })

# -------------------- Convert & Delete --------------------

@login_required
@require_POST
def convert_uploaded_connection(request, connection_id):
    uploaded = get_object_or_404(LinkedInConnection, id=connection_id, community_builder=request.user)
    lead, _ = OutreachLead.objects.get_or_create(
        linkedin_url=uploaded.linkedin_url,
        defaults={
            'full_name': f"{uploaded.first_name} {uploaded.last_name}",
            'location': '', 'added_by': request.user
        }
    )
    if hasattr(lead, 'connection'):
        return JsonResponse({'success': False, 'message': 'Already converted.'})

    Connection.objects.create(
        outreach_lead=lead,
        full_name=lead.full_name,
        location=lead.location,
        added_by=request.user,
        linkedin_email=uploaded.email or '',
    )
    uploaded.delete()
    return JsonResponse({'success': True})

@login_required
@require_POST
def delete_uploaded_connection(request, connection_id):
    conn = get_object_or_404(LinkedInConnection, id=connection_id, community_builder=request.user)
    conn.delete()
    return JsonResponse({'success': True})

@login_required
def convert_uploaded_connection(request, connection_id):
    uploaded = get_object_or_404(LinkedInConnection, id=connection_id, community_builder=request.user)

    # 1. Create OutreachLead
    lead, created = OutreachLead.objects.get_or_create(
        linkedin_url=uploaded.linkedin_url,
        defaults={
            'full_name': f"{uploaded.first_name} {uploaded.last_name}",
            'location': '',
            'added_by': request.user,
        }
    )

    # 2. Delete the temp record
    uploaded.delete()

    # 3. Redirect to add-connection form
    return redirect('add_connection', lead_id=lead.id)
