"""Symptom-related database models."""
from django.db import models
from django.conf import settings


class SymptomAnalysis(models.Model):
    """Stores a single symptom analysis run."""
    CATEGORY_CHOICES = [
        ('respiratory', 'Respiratory'),
        ('digestive', 'Digestive'),
        ('neurological', 'Neurological'),
        ('dermatological', 'Dermatological'),
        ('musculoskeletal', 'Musculoskeletal'),
        ('general', 'General'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='symptom_analyses',
        null=True, blank=True,
    )
    raw_input = models.TextField(help_text='Original user symptom description')
    cleaned_input = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=True)
    category_confidence = models.FloatField(null=True, blank=True)
    duration_text = models.CharField(max_length=200, blank=True)
    severity_text = models.CharField(max_length=200, blank=True)
    body_area = models.CharField(max_length=200, blank=True)
    workflow_status = models.JSONField(default=dict, blank=True)
    llm_response = models.TextField(blank=True)
    safety_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'symptom_analyses'
        ordering = ['-created_at']

    def __str__(self):
        return f'Analysis #{self.pk} — {self.category} ({self.created_at.date()})'


class ExtractedSymptom(models.Model):
    """Individual symptom entity extracted from a SymptomAnalysis."""
    analysis = models.ForeignKey(
        SymptomAnalysis,
        on_delete=models.CASCADE,
        related_name='extracted_symptoms',
    )
    name = models.CharField(max_length=300)
    entity_type = models.CharField(max_length=100, blank=True, default='symptom')
    confidence = models.FloatField(null=True, blank=True)
    start_char = models.IntegerField(null=True, blank=True)
    end_char = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'extracted_symptoms'

    def __str__(self):
        return self.name


class AnalysisSource(models.Model):
    """Evidence sources used in an analysis."""
    analysis = models.ForeignKey(
        SymptomAnalysis,
        on_delete=models.CASCADE,
        related_name='sources',
    )
    title = models.CharField(max_length=500)
    snippet = models.TextField(blank=True)
    similarity_score = models.FloatField(null=True, blank=True)
    source_file = models.CharField(max_length=500, blank=True)
    chunk_index = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'analysis_sources'

    def __str__(self):
        return self.title


class WorkflowRun(models.Model):
    """Tracks individual LangGraph agent workflow runs."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    analysis = models.OneToOneField(
        SymptomAnalysis,
        on_delete=models.CASCADE,
        related_name='workflow_run',
        null=True, blank=True,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    agent_steps = models.JSONField(default=dict)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = 'workflow_runs'

    def __str__(self):
        return f'WorkflowRun #{self.pk} — {self.status}'
