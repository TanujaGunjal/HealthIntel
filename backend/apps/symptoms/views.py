"""Symptom API views."""
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import SymptomAnalysis, ExtractedSymptom, AnalysisSource, WorkflowRun
from django.shortcuts import get_object_or_404
from .serializers import (
    SymptomInputSerializer, SymptomAnalysisSerializer, SymptomAnalysisListSerializer
)

logger = logging.getLogger(__name__)


class SymptomAnalyzeView(APIView):
    """
    POST /api/symptoms/analyze/
    Run NER + classifier on symptom text. Returns structured entities + category.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = SymptomInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        raw_symptoms = serializer.validated_data['symptoms']

        # NER
        try:
            from ml.ner_pipeline import extract_entities
            entities = extract_entities(raw_symptoms)
        except Exception as e:
            logger.error('NER pipeline error: %s', e)
            entities = {
                'symptoms': [], 'duration': None, 'severity': None,
                'body_area': None, 'nlp_source': 'error', 'cleaned_text': raw_symptoms
            }

        # Classifier — ONLY positive symptoms should be passed
        try:
            from ml.classifier import classify_symptoms
            pos_syms = entities.get('positive_symptoms') or entities.get('symptoms', [])
            pos_text = entities.get('positive_text', '').strip()
            classify_input = ' '.join(pos_syms)
            if pos_text and pos_text.lower() != classify_input.lower():
                classify_input = (classify_input + ' ' + pos_text).strip()
            classification = classify_symptoms(classify_input)
        except Exception as e:
            logger.error('Classifier error: %s', e)
            classification = {
                'category': 'general', 'confidence': 0.5,
                'all_probabilities': {}, 'model': 'error'
            }

        # Save to DB
        analysis = SymptomAnalysis.objects.create(
            user=request.user,
            raw_input=raw_symptoms,
            cleaned_input=entities.get('cleaned_text', ''),
            category=classification['category'],
            category_confidence=classification['confidence'],
            duration_text=entities.get('duration') or '',
            severity_text=entities.get('severity') or '',
            body_area=entities.get('body_area') or '',
        )

        for sym in entities.get('symptoms', []):
            ExtractedSymptom.objects.create(analysis=analysis, name=sym)

        return Response({
            'analysis_id': analysis.id,
            'id': analysis.id,
            'raw_input': raw_symptoms,
            'symptoms': entities.get('symptoms', []),
            'positive_symptoms': entities.get('positive_symptoms', entities.get('symptoms', [])),
            'negated_symptoms': entities.get('negated_symptoms', []),
            'extracted_symptoms': [{'name': s} for s in entities.get('symptoms', [])],
            'duration': entities.get('duration'),
            'duration_text': entities.get('duration') or '',
            'severity': entities.get('severity'),
            'severity_text': entities.get('severity') or '',
            'body_area': entities.get('body_area') or '',
            'nlp_source': entities.get('nlp_source'),
            'category': classification['category'],
            'confidence': classification['confidence'],
            'category_confidence': classification['confidence'],
            'all_probabilities': classification.get('all_probabilities', {}),
            'classifier_model': classification.get('model'),
            'workflow_status': {
                'steps': [
                    {
                        'agent': 'SymptomAnalysisAgent',
                        'status': 'completed',
                        'output_preview': 'Symptom classification completed',
                        'symptoms': entities.get('symptoms', []),
                        'negated_symptoms': entities.get('negated_symptoms', []),
                        'category': classification['category'],
                        'duration': entities.get('duration'),
                        'severity': entities.get('severity'),
                        'body_area': entities.get('body_area'),
                    },
                    {
                        'agent': 'EvidenceRetrievalAgent',
                        'status': 'unavailable',
                        'message': 'Evidence retrieval not run in Quick Mode',
                        'passages_found': 0,
                    },
                    {
                        'agent': 'SafetyAgent',
                        'status': 'unavailable',
                        'message': 'Safety checks not run in Quick Mode',
                    },
                    {
                        'agent': 'FinalResponseAgent',
                        'status': 'unavailable',
                        'message': 'Response generation not run in Quick Mode',
                    },
                ],
                'is_urgent': False,
            },
            'sources': [],
            'safety_notes': 'This information is for educational purposes only. Run the Full AI Workflow for evidence retrieval and response generation.',
        }, status=status.HTTP_200_OK)


class SymptomWorkflowView(APIView):
    """
    POST /api/symptoms/workflow/
    Run full LangGraph agentic workflow. Returns health-information report.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = SymptomInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        raw_symptoms = serializer.validated_data['symptoms']

        # NER
        try:
            from ml.ner_pipeline import extract_entities
            entities = extract_entities(raw_symptoms)
        except Exception as e:
            logger.error('NER error: %s', e)
            entities = {'symptoms': [], 'duration': None, 'severity': None,
                        'body_area': None, 'cleaned_text': raw_symptoms}

        # Classifier — ONLY positive symptoms should be passed
        try:
            from ml.classifier import classify_symptoms
            pos_syms = entities.get('positive_symptoms') or entities.get('symptoms', [])
            pos_text = entities.get('positive_text', '').strip()
            classify_input = ' '.join(pos_syms)
            if pos_text and pos_text.lower() != classify_input.lower():
                classify_input = (classify_input + ' ' + pos_text).strip()
            classification = classify_symptoms(classify_input)
        except Exception as e:
            logger.error('Classifier error: %s', e)
            classification = {'category': 'general', 'confidence': 0.5}

        # Create DB record
        analysis = SymptomAnalysis.objects.create(
            user=request.user,
            raw_input=raw_symptoms,
            cleaned_input=entities.get('cleaned_text', ''),
            category=classification['category'],
            category_confidence=classification['confidence'],
            duration_text=entities.get('duration') or '',
            severity_text=entities.get('severity') or '',
            body_area=entities.get('body_area') or '',
        )
        for sym in pos_syms:
            ExtractedSymptom.objects.create(analysis=analysis, name=sym)

        workflow_run = WorkflowRun.objects.create(analysis=analysis, status='running')

        # Run LangGraph workflow
        agent_steps = []
        try:
            from ml.agent_workflow import run_workflow
            result = run_workflow(
                raw_symptoms=raw_symptoms,
                extracted_symptoms=pos_syms,
                negated_symptoms=entities.get('negated_symptoms', []),
                positive_text=entities.get('positive_text', ''),
                duration=entities.get('duration'),
                severity=entities.get('severity'),
                body_area=entities.get('body_area'),
                category=classification['category'],
                category_confidence=classification['confidence'],
            )

            agent_steps = result.get('agent_steps', [])
            is_urgent = result.get('is_urgent', False)

            # Save evidence sources from RAG retrieval
            for passage in result.get('retrieved_passages', []):
                AnalysisSource.objects.create(
                    analysis=analysis,
                    title=passage.get('title', 'Medical Reference'),
                    snippet=passage.get('text', '')[:500],
                    similarity_score=passage.get('similarity_score'),
                    source_file=passage.get('source_file', ''),
                    chunk_index=passage.get('chunk_index'),
                )

            # Persist all workflow outputs
            analysis.llm_response = result.get('final_response', '')
            analysis.safety_notes = result.get('safety_notes', '')
            analysis.workflow_status = {
                'steps': agent_steps,
                'is_urgent': is_urgent,
            }
            analysis.save()

            workflow_run.status = 'completed'
            workflow_run.agent_steps = {
                'steps': agent_steps,
                'error': result.get('error'),
            }
            workflow_run.completed_at = timezone.now()
            workflow_run.save()

        except Exception as e:
            logger.error('Workflow error: %s', e, exc_info=True)
            agent_steps = [{'agent': 'workflow', 'status': 'error', 'error': str(e)}]
            analysis.safety_notes = (
                'This information is for educational purposes only. '
                'Please consult a healthcare professional.'
            )
            analysis.workflow_status = {'steps': agent_steps, 'is_urgent': False}
            analysis.save()

            workflow_run.status = 'failed'
            workflow_run.error_message = str(e)
            workflow_run.agent_steps = {'steps': agent_steps}
            workflow_run.completed_at = timezone.now()
            workflow_run.save()

        analysis.refresh_from_db()
        serialized = SymptomAnalysisSerializer(analysis)
        return Response(serialized.data, status=status.HTTP_200_OK)


class SymptomDetailView(APIView):
    """
    GET /api/symptoms/<pk>/
    Retrieve a single SymptomAnalysis by its primary key.
    Only accessible by the owner.
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request, pk):
        analysis = get_object_or_404(
            SymptomAnalysis, pk=pk, user=request.user
        )
        serialized = SymptomAnalysisSerializer(analysis)
        return Response(serialized.data, status=status.HTTP_200_OK)
