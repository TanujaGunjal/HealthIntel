"""Appointments serializers."""
from rest_framework import serializers
from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = (
            'id', 'provider_name', 'provider_type', 'provider_address',
            'appointment_date', 'appointment_time', 'notes', 'status', 'created_at',
        )
        read_only_fields = ('id', 'created_at', 'status')


class AppointmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = (
            'provider_name', 'provider_type', 'provider_address',
            'appointment_date', 'appointment_time', 'notes',
        )

    def validate_appointment_date(self, value):
        from datetime import date
        if value < date.today():
            raise serializers.ValidationError('Appointment date cannot be in the past.')
        return value
