from django.urls import path
from django.contrib.auth import views as auth_views

# ✅ Editor Views
from .views.editor import pending_biographies, editor_view_connection

# ✅ Community Builder Views
from .views.community_builder import (
    builder_dashboard, add_lead, check_linkedin_url, outreach_lead_list,
    add_connection, connection_list, update_connection_status,
    view_analytics, filter_connections_by_status,
    edit_connection, upload_chat_screenshot, view_connection, add_comment as builder_add_comment,
    upload_linkedin_connections, uploaded_connections_page,
    get_uploaded_connections, convert_uploaded_connection, delete_uploaded_connection,
)

# ✅ Project Manager Views
from .views import (
    dashboard_redirect, superadmin_dashboard, manager_dashboard, editor_dashboard,
    add_editor, add_builder, view_team, view_team_connections,
)

from .views.project_manager import (
    view_builder_dashboard,
    manager_view_connection,
    assign_editor,
    manager_add_comment,
)

# ✅ API Views
from .views.api_views import (
    assign_editor_ajax,
    get_filter_data,
    get_filtered_connections,
)

urlpatterns = [

    # 🔐 Auth
    path('login/', auth_views.LoginView.as_view(template_name='lead_management/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # 🧭 Dashboard
    path('dashboard/', dashboard_redirect, name='dashboard'),
    path('dashboard/superadmin/', superadmin_dashboard, name='superadmin_dashboard'),
    path('dashboard/manager/', manager_dashboard, name='manager_dashboard'),
    path('dashboard/builder/', builder_dashboard, name='builder_dashboard'),
    path('dashboard/editor/', editor_dashboard, name='editor_dashboard'),

    # 👷 Community Builder
    path('add-lead/', add_lead, name='add_lead'),
    path('check-linkedin-url/', check_linkedin_url, name='check_linkedin_url'),
    path('outreach-leads/', outreach_lead_list, name='outreach_lead_list'),
    path('add-connection/<int:lead_id>/', add_connection, name='add_connection'),
    path('connections/', connection_list, name='connection_list'),
    path('update-connection-status/<int:connection_id>/', update_connection_status, name='update_connection_status'),
    path('dashboard/builder/analytics/', view_analytics, name='view_analytics'),
    path('analytics/filter/<str:status>/', filter_connections_by_status, name='filter_connections_by_status'),

    # 🧑‍💼 View & Edit Connection
    path('connections/<int:connection_id>/edit/', edit_connection, name='edit_connection'),
    path('connections/<int:connection_id>/upload-screenshot/', upload_chat_screenshot, name='upload_chat_screenshot'),
    path('connections/<int:connection_id>/view/', view_connection, name='view_connection'),
    path('connections/<int:connection_id>/add-comment/', builder_add_comment, name='add_comment'),

    # 🆕 LinkedIn Upload & View Uploaded Data
    path('builder/upload-connections/', upload_linkedin_connections, name='upload_linkedin_connections'),
    path('builder/uploaded-connections/', uploaded_connections_page, name='uploaded_connections_page'),
    path('builder/uploaded-connections-data/', get_uploaded_connections, name='get_uploaded_connections'),
    path('builder/convert-uploaded-connection/<int:connection_id>/', convert_uploaded_connection, name='convert_uploaded_connection'),
    path('builder/delete-uploaded-connection/<int:connection_id>/', delete_uploaded_connection, name='delete_uploaded_connection'),

    # 🧑‍💼 Project Manager Features
    path('manager/add-editor/', add_editor, name='add_editor'),
    path('manager/add-builder/', add_builder, name='add_builder'),
    path('manager/view-team/', view_team, name='view_team'),
    path('manager/connections/', view_team_connections, name='manager_connections'),
    path('manager/builder/<int:builder_id>/dashboard/', view_builder_dashboard, name='view_builder_dashboard'),

    # 👁️ PM View & Actions
    path('manager/connection/<int:connection_id>/view/', manager_view_connection, name='manager_view_connection'),
    path('manager/connection/<int:connection_id>/assign-editor/', assign_editor, name='assign_editor'),
    path('manager/connection/<int:connection_id>/add-comment/', manager_add_comment, name='manager_add_comment'),

    # ✏️ Editors
    path('dashboard/editor/pending/', pending_biographies, name='pending_biographies'),
    path('editor/connection/<int:connection_id>/view/', editor_view_connection, name='editor_view_connection'),

    # 🌐 API (AJAX)
    path('api/assign-editor/', assign_editor_ajax, name='assign-editor-ajax'),
    path('api/manager/filters/', get_filter_data, name='manager-filter-data'),
    path('api/manager/filtered-connections/', get_filtered_connections, name='manager-filtered-connections'),
]
