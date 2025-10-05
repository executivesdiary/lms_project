from .common            import dashboard_redirect
from .superadmin        import superadmin_dashboard
from .editor            import editor_dashboard
from .project_manager   import (
    manager_dashboard,
    add_editor, add_builder, assign_editor,
    view_team, view_team_connections  # ✅ updated here
)
from .community_builder import (
    builder_dashboard, add_lead, check_linkedin_url,
    outreach_lead_list, add_connection, connection_list,
    update_connection_status, view_analytics,
    filter_connections_by_status, edit_connection,
    upload_chat_screenshot, view_connection, add_comment
)
