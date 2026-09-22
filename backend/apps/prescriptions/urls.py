"""Prescription URL routes."""
from django.urls import path
from .views import PrescriptionAnalyzeView, PrescriptionExplainView

urlpatterns = [
    path('analyze/', PrescriptionAnalyzeView.as_view(), name='prescription-analyze'),
    path('<int:pk>/explain/', PrescriptionExplainView.as_view(), name='prescription-explain'),
]
