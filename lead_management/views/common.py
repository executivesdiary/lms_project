from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

@login_required
def dashboard_redirect(request):
    role_map = {
        'super_admin': 'superadmin_dashboard',
        'project_manager': 'manager_dashboard',
        'community_builder': 'builder_dashboard',
        'editor': 'editor_dashboard'
    }
    return redirect(role_map.get(request.user.role, 'login'))
