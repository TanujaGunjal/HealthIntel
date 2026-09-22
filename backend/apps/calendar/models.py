from django.conf import settings
from django.db import models


class GoogleCalendarCredential(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='google_calendar_credential')
    token_data = models.TextField()
    calendar_id = models.CharField(max_length=255, default='primary')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class MedicationCalendarEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='medication_calendar_events')
    prescription = models.ForeignKey('prescriptions.Prescription', on_delete=models.CASCADE)
    medicine = models.ForeignKey('prescriptions.Medicine', on_delete=models.CASCADE)
    event_id = models.CharField(max_length=255)
    fingerprint = models.CharField(max_length=64)
    calendar_id = models.CharField(max_length=255, default='primary')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('user', 'fingerprint'),
                                    name='unique_medication_calendar_fingerprint'),
        ]
