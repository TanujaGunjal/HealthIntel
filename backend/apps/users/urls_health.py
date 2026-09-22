"""Health check endpoint."""
from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
import django
import sys


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """System health check for monitoring/readiness probes."""
    return Response({
        'status': 'healthy',
        'service': 'HealthIntel API',
        'version': '1.0.0',
        'python': sys.version,
        'django': django.__version__,
    })


urlpatterns = [
    path('', health_check, name='health_check'),
]
