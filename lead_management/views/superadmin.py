from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def superadmin_dashboard(request):
    return render(request, 'lead_management/superadmin_dashboard.html')
