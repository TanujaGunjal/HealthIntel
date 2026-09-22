"""Appointments models — local booking workflow."""
from django.db import models
from django.conf import settings


class Appointment(models.Model):
    """A booked healthcare provider appointment."""
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='appointments',
    )
    provider_name = models.CharField(max_length=300)
    provider_type = models.CharField(max_length=200, blank=True)
    provider_address = models.TextField(blank=True)
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-appointment_date', '-appointment_time']

    def __str__(self):
        return f'{self.provider_name} — {self.appointment_date}'
