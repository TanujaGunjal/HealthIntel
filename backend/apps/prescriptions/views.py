"""Prescription OCR views."""
import logging
import os
import json
import re
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings

from .models import Prescription, Medicine
from .serializers import PrescriptionSerializer

logger = logging.getLogger(__name__)

ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/bmp', 'image/tiff']
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MIN_EVIDENCE_SCORE = 0.40
EXPLANATION_CONTRACT_VERSION = '1.0'

COMMON_ALIASES = {
    'paracetamol': ['paracetamol', 'acetaminophen', 'tylenol', 'panadol', 'calpol'],
    'acetaminophen': ['acetaminophen', 'paracetamol', 'tylenol'],
    'cetirizine': ['cetirizine', 'zyrtec', 'cetzine', 'alerid'],
    'pantoprazole': ['pantoprazole', 'protonix', 'pantocid', 'pan'],
    'amoxicillin': ['amoxicillin', 'amoxil', 'augmentin'],
    'ibuprofen': ['ibuprofen', 'advil', 'motrin', 'brufen'],
    'azithromycin': ['azithromycin', 'zithromax', 'azithral'],
    'atorvastatin': ['atorvastatin', 'lipitor', 'atorva'],
    'metformin': ['metformin', 'glucophage', 'glycomet'],
    'omeprazole': ['omeprazole', 'prilosec', 'omez'],
}

KNOWN_MED_INFO = {
    'paracetamol': {
        'uses': 'Analgesic and antipyretic indicated for the relief of mild to moderate pain (such as headaches, body aches, dental discomfort) and the reduction of fever.',
        'admin': 'Can be taken with or without food. Tablets should be swallowed whole with water. Adhere strictly to the prescribed interval and daily schedule.',
        'precautions': 'Maximum daily adult dose is 4,000 mg (4 g) within 24 hours. Avoid concurrent use of other over-the-counter or prescription medicines containing paracetamol or acetaminophen to prevent acute liver injury. Exercise caution in chronic liver disease or alcohol use.',
    },
    'acetaminophen': {
        'uses': 'Analgesic and antipyretic indicated for the relief of mild to moderate pain and the reduction of fever.',
        'admin': 'Can be taken with or without food. Swallow tablets whole with water.',
        'precautions': 'Do not exceed 4,000 mg in 24 hours. Avoid concurrent acetaminophen-containing medications to avoid hepatic toxicity.',
    },
    'cetirizine': {
        'uses': 'Second-generation H1-antihistamine indicated for symptomatic relief of allergic rhinitis, seasonal allergies (sneezing, runny nose, itchy/watery eyes), and urticaria (hives and skin itching).',
        'admin': 'Taken once daily, commonly in the evening or at night before bedtime due to potential mild somnolence. Can be taken with or without food.',
        'precautions': 'Although typically non-sedating, mild drowsiness can occur. Exercise caution when driving or operating machinery. Avoid concomitant alcohol consumption or other CNS depressants.',
    },
    'pantoprazole': {
        'uses': 'Proton pump inhibitor (PPI) indicated for gastroesophageal reflux disease (GERD), acid reflux, erosive esophagitis, and gastroprotection against stomach/duodenal ulceration.',
        'admin': 'Should be taken once daily in the morning, approximately 30 to 60 minutes before breakfast (or the first meal of the day) with water. Delayed-release tablets must be swallowed whole; do not chew, crush, or split.',
        'precautions': 'Do not break or chew delayed-release tablets. Long-term continuous use warrants medical monitoring. Report persistent digestive symptoms, dark stools, or difficulty swallowing to your physician.',
    },
    'amoxicillin': {
        'uses': 'Aminopenicillin antibiotic indicated for susceptible bacterial infections of the respiratory tract, ear, nose, throat, and skin.',
        'admin': 'Take at evenly spaced intervals with or without food. Complete the full prescribed course even if symptoms resolve earlier.',
        'precautions': 'Contraindicated in individuals with known penicillin allergies. Discontinue and seek urgent care if severe rash, facial swelling, or breathing difficulty occurs.',
    },
    'ibuprofen': {
        'uses': 'Nonsteroidal anti-inflammatory drug (NSAID) indicated for mild-to-moderate pain relief, inflammation, and fever.',
        'admin': 'Always take with food or milk to minimize gastric irritation.',
        'precautions': 'Increased risk of gastrointestinal irritation or bleeding. Use with caution in hypertension, heart failure, or kidney disease.',
    },
    'azithromycin': {
        'uses': 'Macrolide antibiotic indicated for respiratory infections, sinusitis, and uncomplicated skin infections.',
        'admin': 'Take once daily with or without food. Complete the full prescribed course.',
        'precautions': 'Caution in patients with cardiac arrhythmia risks or QT prolongation.',
    },
    'metformin': {
        'uses': 'Biguanide oral antihyperglycemic agent indicated as first-line therapy for type 2 diabetes mellitus.',
        'admin': 'Take with meals to minimize gastrointestinal discomfort.',
        'precautions': 'Risk of lactic acidosis; contraindicated in severe renal impairment.',
    },
    'atorvastatin': {
        'uses': 'HMG-CoA reductase inhibitor (statin) indicated for hypercholesterolemia and cardiovascular risk reduction.',
        'admin': 'Take once daily, with or without food, at roughly the same time each day (often evening).',
        'precautions': 'Promptly report unexplained muscle pain, tenderness, or weakness to your doctor.',
    },
}


def _normalize_for_search(name: str) -> str:
    """Normalize medicine name: strip dosage, forms, salts, and punctuation."""
    if not name:
        return ''
    clean = re.sub(r'\b(?:tab(?:let)?s?|cap(?:sule)?s?|syrup|inj(?:ection)?|drops?|suspension)\b', '', name, flags=re.IGNORECASE)
    clean = re.sub(r'\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|iu|units?)\b', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\b(?:sodium|potassium|hcl|hydrochloride|dihydrochloride|maleate|succinate|tartrate)\b', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'[^a-zA-Z\s]', ' ', clean)
    words = clean.strip().split()
    return words[0].title() if words else name.strip().title()


def _evidence_mentions_medicine(passage, medicine_name):
    """Require the retrieved passage to mention the queried medicine or its known aliases."""
    haystack = ' '.join(str(passage.get(key, '') or '') for key in ('text', 'title', 'source_file')).lower()
    norm = _normalize_for_search(medicine_name).lower()
    search_terms = {norm}
    if norm in COMMON_ALIASES:
        search_terms.update(COMMON_ALIASES[norm])
    for term in search_terms:
        if re.search(rf'\b{re.escape(term)}\b', haystack):
            return True
    return False


def _validation(medicines):
    """Report whether the extracted instructions are safe to review.

    Validation is intentionally limited to presence/quality checks. It does
    not assert that a prescription is clinically correct.
    """
    warnings = []
    for medicine in medicines:
        for field, label in (('name', 'Medicine name'), ('dosage', 'Dosage'), ('frequency', 'Frequency'), ('duration', 'Duration')):
            if not medicine.get(field):
                warnings.append(f"{medicine.get('name', 'Medicine')}: {label} could not be confidently extracted.")
        if medicine.get('needs_verification'):
            warnings.append(f"{medicine.get('name', 'Medicine')}: extraction requires verification against the original prescription.")
    if not medicines:
        return {
            'status': 'failed',
            'warnings': ['No medicine instructions could be identified from the OCR text.'],
        }
    return {'status': 'complete' if not warnings else 'partial', 'warnings': warnings}


def _schedule(medicines):
    """Group only explicitly observed timing; unknown timing is never inferred."""
    entries = []
    for medicine in medicines:
        timing = medicine.get('timing')
        lower = (timing or '').lower()
        period = (
            'Morning' if 'breakfast' in lower
            else 'Night' if ('night' in lower or 'bedtime' in lower)
            else 'Timing not specified'
        )
        instruction = ' '.join(item for item in (medicine.get('quantity'), medicine.get('frequency'), timing) if item) or 'Timing not specified'
        entries.append({
            'period': period,
            'medicine': medicine.get('name'),
            'dosage': medicine.get('dosage'),
            'frequency': medicine.get('frequency'),
            'duration': medicine.get('duration'),
            'instruction': instruction,
        })
    return entries


def _evidence(medicines):
    if not medicines:
        return {'status': 'NOT_REQUESTED', 'items': []}
    try:
        from ml.rag_engine import get_rag_engine
        engine = get_rag_engine()
        items = []
        for medicine in medicines:
            med_name = medicine.get('name', '')
            norm_name = _normalize_for_search(med_name)
            if not norm_name:
                continue

            # Query 1: Normalized name
            passages = engine.query(norm_name, top_k=5)
            matched_passage = next((
                candidate for candidate in sorted(
                    passages,
                    key=lambda item: float(item.get('similarity_score', 0) or 0),
                    reverse=True,
                )
                if float(candidate.get('similarity_score', 0) or 0) >= MIN_EVIDENCE_SCORE
                and _evidence_mentions_medicine(candidate, norm_name)
            ), None)

            # Query 2: Fallback query if exact name had no match
            if not matched_passage:
                dosage = medicine.get('dosage') or ''
                fallback_query = f"{norm_name} {dosage} general medication information common uses precautions administration".strip()
                fallback_passages = engine.query(fallback_query, top_k=5)
                matched_passage = next((
                    candidate for candidate in sorted(
                        fallback_passages,
                        key=lambda item: float(item.get('similarity_score', 0) or 0),
                        reverse=True,
                    )
                    if float(candidate.get('similarity_score', 0) or 0) >= MIN_EVIDENCE_SCORE
                    and _evidence_mentions_medicine(candidate, norm_name)
                ), None)

            if matched_passage:
                items.append({
                    'medicine': med_name,
                    'normalized_name': norm_name,
                    'title': matched_passage.get('title') or 'Medication Reference',
                    'snippet': matched_passage.get('text', '')[:400],
                    'source_file': matched_passage.get('source_file', ''),
                    'similarity_score': matched_passage.get('similarity_score'),
                })
        return {
            'status': 'AVAILABLE' if items else 'NO_MATCHES',
            'items': items,
        }
    except Exception as exc:
        logger.warning('Prescription RAG unavailable: %s', exc)
        return {'status': 'RAG_UNAVAILABLE', 'items': []}


def _generate_explanation(medicines, evidence_items):
    """
    Generate an educational explanation for each medicine grounded strictly in evidence.
    Preserves doctor's extracted instructions exactly.
    Never invents medical information; shows 'Evidence unavailable' if unbacked.
    """
    if not medicines:
        return None

    # Map evidence items by normalized medicine name
    evidence_by_name = {}
    for item in (evidence_items or []):
        norm = (item.get('normalized_name') or _normalize_for_search(item.get('medicine', ''))).lower()
        if norm:
            evidence_by_name[norm] = item
            if norm in COMMON_ALIASES:
                for alias in COMMON_ALIASES[norm]:
                    evidence_by_name[alias] = item

    med_explanations = []
    for med in medicines:
        med_name = med.get('name', '')
        norm = _normalize_for_search(med_name).lower()
        ev_item = evidence_by_name.get(norm)

        # Doctor's prescribed instruction exactly as extracted
        order_parts = []
        if med.get('dosage'):
            order_parts.append(med.get('dosage'))
        if med.get('frequency'):
            order_parts.append(med.get('frequency'))
        if med.get('duration'):
            order_parts.append(f"for {med.get('duration')}")
        if med.get('timing'):
            order_parts.append(f"({med.get('timing')})")
        prescribed_order = ' - '.join(order_parts) if order_parts else 'Prescribed instruction as labeled'

        if not ev_item:
            med_explanations.append({
                'name': med_name,
                'explanation': (
                    f"Prescribed Instruction: {prescribed_order}\n\n"
                    "Evidence unavailable for this medicine in the medical reference database. "
                    "Please consult your prescribing physician or pharmacist for clinical guidance.\n\n"
                    "Important Notice: This system provides educational information only and does NOT change, recommend, or prescribe medication."
                ),
                'evidence_available': False,
            })
            continue

        # Evidence is available
        info = KNOWN_MED_INFO.get(norm)
        if not info:
            snippet = ev_item.get('snippet', '')
            uses = f"Referenced in medical literature: {snippet[:200]}..."
            admin = "Follow prescribed administration schedule with water."
            precautions = "Adhere strictly to physician directions; review with healthcare provider."
        else:
            uses = info['uses']
            admin = info['admin']
            precautions = info['precautions']

        explanation_lines = [
            f"What this medicine is generally used for:\n{uses}",
            f"Prescribed Instruction (Doctor's Order):\n{prescribed_order}",
            f"General Administration Guidelines:\n{admin}",
            f"Important Precautions & Warnings:\n{precautions}",
            "Important Notice: This system provides educational information only and does NOT change, recommend, or prescribe medication. Always adhere strictly to your doctor's exact prescription."
        ]

        med_explanations.append({
            'name': med_name,
            'explanation': "\n\n".join(explanation_lines),
            'evidence_available': True,
        })

    summary = (
        f"Educational overview for {len(medicines)} prescribed medication(s) grounded in retrieved medical literature. "
        "Prescribed dosages, frequencies, durations, and timing are preserved exactly as ordered by your doctor."
    )

    return {
        'summary': summary,
        'medicines': med_explanations,
        'limitations': [
            "Educational explanation only; this system does not prescribe, modify, or recommend medications.",
            "Always follow your prescribing doctor's exact instructions.",
        ],
        'disclaimer': "This is an educational explanation of the uploaded prescription. It does not replace advice from your doctor or pharmacist.",
    }


def _response_payload(prescription, result):
    medicines = result.get('medicines', [])
    validation = _validation(medicines)
    evidence = _evidence(medicines)
    explanation = None
    if evidence['status'] == 'AVAILABLE' and medicines:
        explanation = _generate_explanation(medicines, evidence['items'])

    if not result.get('raw_text'):
        extraction_status = 'OCR_FAILED'
    elif not medicines:
        extraction_status = 'EXTRACTION_FAILED'
    elif result.get('low_confidence') or validation['status'] != 'complete':
        extraction_status = 'PARTIAL'
    else:
        extraction_status = 'SUCCESS'

    return {
        **PrescriptionSerializer(prescription).data,
        'status': extraction_status,
        'ocr': {'engine': result.get('ocr_engine'), 'text': result.get('raw_text'), 'confidence': result.get('confidence')},
        'medicines': medicines,
        'validation': validation,
        'safety': {
            'status': 'SAFETY_CHECK_UNAVAILABLE',
            'results': [],
            'message': 'Safety validation unavailable: no clinical interaction database is configured.',
        },
        'evidence': evidence,
        'explanation': explanation,
        'workflow': [
            {'label': 'Image Processing', 'status': 'completed' if result.get('raw_text') is not None else 'failed'},
            {'label': 'OCR Extraction', 'status': 'completed' if result.get('raw_text') else 'failed'},
            {'label': 'Medicine Identification', 'status': 'completed' if medicines else 'unavailable'},
            {'label': 'Instruction Extraction', 'status': 'completed' if medicines and validation['status'] == 'complete' else ('partial' if medicines else 'unavailable')},
            {'label': 'Evidence Retrieval', 'status': 'completed' if evidence['status'] == 'AVAILABLE' else 'unavailable'},
            {'label': 'Safety Validation', 'status': 'unavailable'},
            {'label': 'AI Explanation', 'status': 'completed' if explanation else 'unavailable'},
        ],
        'schedule': _schedule(medicines),
    }


class PrescriptionAnalyzeView(APIView):
    """
    POST /api/prescription/analyze/
    Upload prescription image → OCR → medicine extraction.
    """
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        image_file = request.FILES.get('image')
        if not image_file:
            return Response(
                {'error': 'No image file provided. Use multipart/form-data with key "image".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate type
        if image_file.content_type not in ALLOWED_TYPES:
            return Response(
                {'error': f'Unsupported file type: {image_file.content_type}. Allowed: JPEG, PNG, WEBP, BMP, TIFF'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate size
        if image_file.size > MAX_SIZE_BYTES:
            return Response(
                {'error': f'File too large. Maximum size is {MAX_SIZE_BYTES // 1024 // 1024} MB.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Save prescription record first (to get upload path)
        prescription = Prescription.objects.create(
            user=request.user,
            image=image_file,
        )

        image_path = prescription.image.path
        logger.info('[OCR] Prescription saved at: %s', image_path)
        logger.info('[OCR] File exists: %s, size: %d', os.path.exists(image_path), os.path.getsize(image_path) if os.path.exists(image_path) else 0)

        # Run OCR pipeline
        try:
            from ml.ocr_pipeline import analyze_prescription
            result = analyze_prescription(image_path)
            logger.info('[OCR] Pipeline result: engine=%s, conf=%.2f, status=%s, medicines=%d',
                        result.get('ocr_engine'), result.get('confidence'),
                        result.get('pipeline_status'), len(result.get('medicines', [])))
        except Exception as e:
            logger.error('[OCR] Pipeline exception: %s', e, exc_info=True)
            prescription.delete()
            return Response(
                {'error': f'OCR processing failed: {str(e)}. Please try again with a clearer image.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Update prescription record
        prescription.raw_ocr_text = result.get('raw_text', '')
        prescription.cleaned_ocr_text = result.get('cleaned_text', '')
        prescription.ocr_engine = result.get('ocr_engine', '')
        prescription.ocr_confidence = result.get('confidence', 0.0)
        prescription.low_confidence = result.get('low_confidence', False)
        prescription.warning = result.get('warning') or ''
        prescription.save()

        # Save backwards-compatible medicine records, retaining extended extraction metadata.
        for med_data in result.get('medicines', []):
            medicine = Medicine.objects.create(
                prescription=prescription,
                name=med_data.get('name', ''),
                dosage=med_data.get('dosage') or '',
                frequency=med_data.get('frequency') or '',
                duration=med_data.get('duration') or '',
                notes=json.dumps({key: med_data.get(key) for key in ('quantity', 'timing', 'field_confidence', 'extraction_confidence', 'normalization_confidence', 'needs_verification')}),
            )
            med_data['id'] = medicine.pk
        return Response(_response_payload(prescription, result), status=status.HTTP_200_OK)


class PrescriptionExplainView(APIView):
    """Educational explanation grounded in retrieved evidence."""
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        try:
            prescription = Prescription.objects.get(pk=pk, user=request.user)
        except Prescription.DoesNotExist:
            return Response({'error': 'Prescription not found.'}, status=status.HTTP_404_NOT_FOUND)
        from ml.ocr_pipeline import extract_medicines
        medicines = extract_medicines(prescription.cleaned_ocr_text, prescription.ocr_confidence or 0)
        evidence = _evidence(medicines)
        if evidence['status'] != 'AVAILABLE':
            return Response({
                'status': 'unavailable',
                'message': 'AI explanation is unavailable because relevant evidence could not be retrieved.',
                'evidence': evidence,
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        explanation = _generate_explanation(medicines, evidence['items'])
        if not explanation:
            return Response({
                'status': 'unavailable',
                'message': 'AI explanation could not be generated.',
                'evidence': evidence,
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({
            'status': 'available',
            'contract_version': EXPLANATION_CONTRACT_VERSION,
            'explanation': explanation,
            'evidence': evidence,
        })
