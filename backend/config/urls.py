"""HealthIntel URL configuration."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', include('apps.users.urls_health')),
    path('api/', include('apps.users.urls')),
    path('api/symptoms/', include('apps.symptoms.urls')),
    path('api/prescription/', include('apps.prescriptions.urls')),
    path('api/rag/', include('apps.rag.urls')),
    path('api/agents/', include('apps.agents.urls')),
    path('api/appointments/', include('apps.appointments.urls')),
    path('api/calendar/', include('apps.calendar.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
