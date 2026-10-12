from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/',              admin.site.urls),
    path('api/auth/',           include('analysis.urls')),
    path('api/players/',        include('players.urls')),
    path('api/assessments/',    include('assessments.urls')),
]

# Serve uploaded media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
