"""Symptom API URLs."""
from django.urls import path
from .views import SymptomAnalyzeView, SymptomWorkflowView, SymptomDetailView

urlpatterns = [
    path('analyze/', SymptomAnalyzeView.as_view(), name='symptom_analyze'),
    path('workflow/', SymptomWorkflowView.as_view(), name='symptom_workflow'),
    path('<int:pk>/', SymptomDetailView.as_view(), name='symptom_detail'),
]
