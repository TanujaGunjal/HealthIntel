"""Prescription and Medicine database models."""
from django.db import models
from django.conf import settings


class Prescription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='prescriptions',
        null=True, blank=True,
    )
    image = models.ImageField(upload_to='prescriptions/')
    raw_ocr_text = models.TextField(blank=True)
    cleaned_ocr_text = models.TextField(blank=True)
    ocr_engine = models.CharField(max_length=50, blank=True)
    ocr_confidence = models.FloatField(null=True, blank=True)
    low_confidence = models.BooleanField(default=False)
    warning = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'prescriptions'
        ordering = ['-created_at']

    def __str__(self):
        return f'Prescription #{self.pk}'


class Medicine(models.Model):
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name='medicines',
    )
    name = models.CharField(max_length=300)
    dosage = models.CharField(max_length=200, blank=True)
    frequency = models.CharField(max_length=200, blank=True)
    duration = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'medicines'

    def __str__(self):
        return self.name
