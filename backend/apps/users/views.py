"""User views — registration, profile."""
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.contrib.auth import get_user_model

from .serializers import RegisterSerializer, UserSerializer, ProfileUpdateSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """Register a new user account."""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                'message': 'Account created successfully.',
                'user': UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ProfileView(generics.RetrieveUpdateAPIView):
    """Retrieve or update the authenticated user's profile."""
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return ProfileUpdateSerializer
        return UserSerializer

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True  # Always partial (PATCH behaviour)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)


class HealthHistoryView(APIView):
    """Return paginated history of the user's analyses."""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        from apps.symptoms.models import SymptomAnalysis
        from apps.symptoms.serializers import SymptomAnalysisListSerializer
        from apps.prescriptions.models import Prescription
        from apps.prescriptions.serializers import PrescriptionListSerializer

        analyses = SymptomAnalysis.objects.filter(user=request.user).order_by('-created_at')[:20]
        prescriptions = Prescription.objects.filter(user=request.user).order_by('-created_at')[:20]

        return Response({
            'symptom_analyses': SymptomAnalysisListSerializer(analyses, many=True).data,
            'prescriptions': PrescriptionListSerializer(prescriptions, many=True).data,
        })
