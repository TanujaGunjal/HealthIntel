"""Symptom app configuration."""
from django.apps import AppConfig


class SymptomsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.symptoms'
    label = 'symptoms'
