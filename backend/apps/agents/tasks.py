"""Celery async tasks for HealthIntel."""
import logging
from config.celery import app

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3, default_retry_delay=10)
def run_ocr_task(self, prescription_id: int, image_path: str):
    """Async OCR processing task."""
    try:
        from ml.ocr_pipeline import analyze_prescription
        from apps.prescriptions.models import Prescription, Medicine

        result = analyze_prescription(image_path)

        prescription = Prescription.objects.get(pk=prescription_id)
        prescription.raw_ocr_text = result.get('raw_text', '')
        prescription.cleaned_ocr_text = result.get('cleaned_text', '')
        prescription.ocr_engine = result.get('ocr_engine', '')
        prescription.ocr_confidence = result.get('confidence', 0.0)
        prescription.low_confidence = result.get('low_confidence', False)
        prescription.warning = result.get('warning') or ''
        prescription.save()

        for med_data in result.get('medicines', []):
            Medicine.objects.create(
                prescription=prescription,
                name=med_data.get('name', ''),
                dosage=med_data.get('dosage') or '',
                frequency=med_data.get('frequency') or '',
                duration=med_data.get('duration') or '',
            )

        logger.info('OCR task completed for prescription %d', prescription_id)
        return {'status': 'completed', 'prescription_id': prescription_id}

    except Exception as exc:
        logger.error('OCR task failed: %s', exc)
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=2)
def run_workflow_task(self, analysis_id: int):
    """Async LangGraph workflow task."""
    try:
        from apps.symptoms.models import SymptomAnalysis, ExtractedSymptom, AnalysisSource, WorkflowRun
        from ml.ner_pipeline import extract_entities
        from ml.classifier import classify_symptoms
        from ml.agent_workflow import run_workflow
        from django.utils import timezone

        analysis = SymptomAnalysis.objects.get(pk=analysis_id)
        workflow_run, _ = WorkflowRun.objects.get_or_create(analysis=analysis)
        workflow_run.status = 'running'
        workflow_run.save()

        entities = extract_entities(analysis.raw_input)
        pos_syms = entities.get('positive_symptoms') or entities.get('symptoms', [])
        pos_text = entities.get('positive_text', '').strip()
        classify_input = ' '.join(pos_syms)
        if pos_text and pos_text.lower() != classify_input.lower():
            classify_input = (classify_input + ' ' + pos_text).strip()
        classification = classify_symptoms(classify_input)

        result = run_workflow(
            raw_symptoms=analysis.raw_input,
            extracted_symptoms=entities.get('symptoms', []),
            negated_symptoms=entities.get('negated_symptoms', []),
            positive_text=entities.get('positive_text', ''),
            duration=entities.get('duration'),
            severity=entities.get('severity'),
            body_area=entities.get('body_area'),
            category=classification['category'],
            category_confidence=classification['confidence'],
        )

        for passage in result.get('retrieved_passages', []):
            AnalysisSource.objects.create(
                analysis=analysis,
                title=passage.get('title', 'Medical Reference'),
                snippet=passage.get('text', '')[:500],
                similarity_score=passage.get('similarity_score'),
                source_file=passage.get('source_file', ''),
                chunk_index=passage.get('chunk_index'),
            )

        analysis.llm_response = result.get('final_response', '')
        analysis.safety_notes = result.get('safety_notes', '')
        analysis.workflow_status = {'steps': result.get('agent_steps', []), 'is_urgent': result.get('is_urgent', False)}
        analysis.save()

        workflow_run.status = 'completed'
        workflow_run.agent_steps = {'steps': result.get('agent_steps', []), 'error': result.get('error')}
        workflow_run.completed_at = timezone.now()
        workflow_run.save()

        return {'status': 'completed', 'analysis_id': analysis_id}
    except Exception as exc:
        logger.error('Workflow task failed: %s', exc)
        raise self.retry(exc=exc)
