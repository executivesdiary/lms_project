from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),                      # Admin panel
    path('', include('lead_management.urls')),            # Main lead management app
    path('biographer/', include('executive_biographer.urls')),  # ✅ Executive Biographer app
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
