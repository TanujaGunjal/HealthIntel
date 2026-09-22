"""Appointments views."""
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Appointment
from .serializers import AppointmentSerializer, AppointmentCreateSerializer


class AppointmentListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/appointments/        — list user's appointments
    POST /api/appointments/        — create a new appointment
    """
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Appointment.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AppointmentCreateSerializer
        return AppointmentSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # Return full appointment data
        full = AppointmentSerializer(serializer.instance)
        return Response(full.data, status=status.HTTP_201_CREATED)


class AppointmentDetailView(APIView):
    """
    GET    /api/appointments/<id>/   — retrieve appointment
    DELETE /api/appointments/<id>/   — cancel appointment
    """
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk, user):
        return get_object_or_404(Appointment, pk=pk, user=user)

    def get(self, request, pk):
        appt = self.get_object(pk, request.user)
        return Response(AppointmentSerializer(appt).data)

    def delete(self, request, pk):
        appt = self.get_object(pk, request.user)
        if appt.status == 'cancelled':
            return Response({'error': 'Already cancelled.'}, status=status.HTTP_400_BAD_REQUEST)
        appt.status = 'cancelled'
        appt.save()
        return Response({'message': 'Appointment cancelled.'}, status=status.HTTP_200_OK)
