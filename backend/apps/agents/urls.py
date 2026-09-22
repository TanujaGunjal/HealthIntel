"""Agents URL config — workflow status endpoint."""
from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.symptoms.models import WorkflowRun


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def workflow_status(request, run_id):
    """GET /api/agents/workflow/<run_id>/status/"""
    try:
        run = WorkflowRun.objects.get(pk=run_id, analysis__user=request.user)
        return Response({
            'id': run.id,
            'status': run.status,
            'agent_steps': run.agent_steps,
            'started_at': run.started_at,
            'completed_at': run.completed_at,
            'error': run.error_message or None,
        })
    except WorkflowRun.DoesNotExist:
        return Response({'error': 'Workflow run not found.'}, status=404)


urlpatterns = [
    path('workflow/<int:run_id>/status/', workflow_status, name='workflow-status'),
]
