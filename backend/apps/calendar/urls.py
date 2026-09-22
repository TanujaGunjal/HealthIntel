from django.urls import path
from .views import AuthorizeView, CallbackView, DisconnectView, ScheduleMedicationView, StatusView

urlpatterns = [
    path('status/', StatusView.as_view(), name='calendar-status'),
    path('oauth/authorize/', AuthorizeView.as_view(), name='calendar-authorize'),
    path('oauth/callback/', CallbackView.as_view(), name='calendar-callback'),
    path('oauth/disconnect/', DisconnectView.as_view(), name='calendar-disconnect'),
    path('schedule/', ScheduleMedicationView.as_view(), name='calendar-schedule'),
]
