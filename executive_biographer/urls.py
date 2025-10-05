from django.urls import path
from . import views

urlpatterns = [
    path('', views.biographer_dashboard, name='biographer_dashboard'),                     # Optional dashboard homepage
    path('<int:connection_id>/', views.generate_biography, name='generate_biography'),      # Biography editor
    path('insights/', views.editor_insights, name='editor_insights'),                       # Editor performance chart
    path('test-api-key/', views.test_openai_key, name='test_openai_key'),                  # API Key test
]
