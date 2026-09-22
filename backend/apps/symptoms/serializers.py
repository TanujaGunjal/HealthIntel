"""Symptom API serializers."""
from rest_framework import serializers
from .models import SymptomAnalysis, ExtractedSymptom, AnalysisSource, WorkflowRun


class ExtractedSymptomSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtractedSymptom
        fields = ('id', 'name', 'entity_type', 'confidence')


class AnalysisSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisSource
        fields = ('id', 'title', 'snippet', 'similarity_score', 'source_file')


class WorkflowRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowRun
        fields = ('id', 'status', 'agent_steps', 'started_at', 'completed_at')


class SymptomAnalysisSerializer(serializers.ModelSerializer):
    extracted_symptoms = ExtractedSymptomSerializer(many=True, read_only=True)
    sources = AnalysisSourceSerializer(many=True, read_only=True)
    workflow_run = WorkflowRunSerializer(read_only=True)

    class Meta:
        model = SymptomAnalysis
        fields = (
            'id', 'raw_input', 'category', 'category_confidence',
            'duration_text', 'severity_text', 'body_area',
            'llm_response', 'safety_notes', 'workflow_status',
            'extracted_symptoms', 'sources', 'workflow_run',
            'created_at',
        )


class SymptomAnalysisListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for history list view."""
    class Meta:
        model = SymptomAnalysis
        fields = ('id', 'raw_input', 'category', 'category_confidence', 'created_at')


class SymptomInputSerializer(serializers.Serializer):
    symptoms = serializers.CharField(
        max_length=2000,
        help_text='Natural language description of symptoms',
    )

    def validate_symptoms(self, value):
        value = value.strip()
        if len(value) < 5:
            raise serializers.ValidationError('Please describe your symptoms in more detail.')
        return value


class RAGQuerySerializer(serializers.Serializer):
    query = serializers.CharField(max_length=1000)
