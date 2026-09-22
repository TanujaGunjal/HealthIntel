"""
OCR Pipeline for Prescription Image Analysis
=============================================
Primary:  EasyOCR
Fallback: Tesseract (pytesseract) if available
Post-processing: regex medicine/dosage extraction
"""
import re
import logging
import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ---- Medicine extraction patterns ----
MEDICINE_PATTERNS = [
    # Suffix-based pattern (covers most drug names)
    r'\b([A-Z][a-zA-Z]{2,}(?:mycin|cillin|zole|prazole|statin|mab|nib|pril|sartan|olol|'
    r'dipine|phylline|cycline|floxacin|oxacin|vir|navir|tidine|sulide|fenac|profen|'
    r'codone|morphine|caine|azepam|barbital|pam|lam|zepine|tidine|razole))\b',
    # Common named medicines
    r'\b(Paracetamol|Ibuprofen|Amoxicillin|Metformin|Aspirin|Omeprazole|Atorvastatin|'
    r'Amlodipine|Losartan|Metoprolol|Cetirizine|Azithromycin|Ciprofloxacin|Doxycycline|'
    r'Pantoprazole|Ranitidine|Diclofenac|Naproxen|Prednisolone|Dexamethasone|'
    r'Salbutamol|Montelukast|Levothyroxine|Insulin|Glibenclamide|Lisinopril|'
    r'Clopidogrel|Warfarin|Gabapentin|Tramadol|Codeine|Hydroxychloroquine|'
    r'Chloroquine|Ivermectin|Albendazole|Metronidazole|Fluconazole|Clotrimazole|'
    r'Ondansetron|Domperidone|Loperamide|Acyclovir|Oseltamivir|Rifampicin|Isoniazid|'
    r'Pyrazinamide|Ethambutol|Streptomycin|Amikacin|Gentamicin|Vancomycin|'
    r'Ampicillin|Cloxacillin|Erythromycin|Clarithromycin|Levofloxacin|Moxifloxacin)\b',
]

DOSAGE_PATTERNS = [
    r'(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|IU|units?|tab(?:let)?s?|cap(?:sule)?s?)(?:/\w+)?)',
    r'(\d+\s*/\s*\d+\s*mg)',
]

FREQUENCY_PATTERNS = [
    r'(\d+\s*(?:times?|x)\s*(?:a\s*)?(?:day|daily|per\s*day|/day))',
    r'(once\s*(?:a\s*)?(?:day|daily))',
    r'(twice\s*(?:a\s*)?(?:day|daily))',
    r'(thrice\s*(?:a\s*)?(?:day|daily))',
    r'(every\s*\d+\s*hours?)',
    r'\b((?:OD|BD|TDS|QDS|QID|BID|SOS|PRN|HS|AC|PC|STAT))\b',
]

DURATION_PATTERNS = [
    r'(?:for|x)\s*(\d+\s*(?:days?|weeks?|months?))',
    r'\b(\d+\s*(?:days?|weeks?|months?))\b',
    r'(\d+\s*(?:days?|weeks?|months?)\s*course)',
]

CONFIDENCE_THRESHOLD = 0.4  # Lowered from 0.5 to catch more results

_EASYOCR_READER = None


def get_easyocr_reader():
    """Lazily initialize and cache the EasyOCR reader singleton to avoid expensive reloads."""
    global _EASYOCR_READER
    if _EASYOCR_READER is None:
        import easyocr
        _EASYOCR_READER = easyocr.Reader(['en'], gpu=False, verbose=False)
        logger.info('[OCR] EasyOCR reader initialized')
    return _EASYOCR_READER


def preprocess_image_variants(image_path: str) -> list[str]:
    """
    Generate multiple preprocessed variants of the image for OCR.
    Returns list of temp file paths (original + variants).
    """
    try:
        import cv2
        import numpy as np

        img = cv2.imread(image_path)
        if img is None:
            logger.warning('[OCR] cv2.imread returned None for %s', image_path)
            return [image_path]

        logger.info('[OCR] Image shape: %s', img.shape)
        h, w = img.shape[:2]

        variants = [image_path]  # original always first
        # Keep variants in a dedicated temporary directory and clean up after use.
        tmp_dir = tempfile.mkdtemp(prefix='ocr-')

        # Grayscale + contrast enhancement (CLAHE)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        p = os.path.join(tmp_dir, 'ocr_enhanced.png')
        cv2.imwrite(p, enhanced)
        variants.append(p)
        logger.info('[OCR] Created contrast-enhanced grayscale variant')

        # Adaptive threshold (good for printed prescriptions)
        thresh = cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 11
        )
        p = os.path.join(tmp_dir, 'ocr_thresh.png')
        cv2.imwrite(p, thresh)
        variants.append(p)
        logger.info('[OCR] Created adaptive-threshold variant')

        # Upscale small images (helps OCR on low-res prescriptions)
        if max(h, w) < 1000:
            scale = 1500 / max(h, w)
            upscaled = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            p = os.path.join(tmp_dir, 'ocr_upscaled.png')
            cv2.imwrite(p, upscaled)
            variants.append(p)
            logger.info('[OCR] Created upscaled variant: %s', p)

        # Phone uploads frequently carry a sideways handwritten page. Include
        # rotations last so they are only tested if upright variants fail.
        for angle, rotated in ((90, cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)),
                               (270, cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE))):
            p = os.path.join(tmp_dir, f'ocr_rotated_{angle}.png')
            cv2.imwrite(p, rotated)
            variants.append(p)

        return variants

    except Exception as e:
        logger.warning('[OCR] Image preprocessing failed: %s — using original', e)
        return [image_path]


def _cleanup_variants(paths: list[str], original: str) -> None:
    """Remove request-scoped OCR variants without touching the upload."""
    cleaned_dirs = set()
    for path in paths:
        if path == original:
            continue
        try:
            parent = Path(path).parent
            if parent.name.startswith('ocr-') and parent not in cleaned_dirs:
                cleaned_dirs.add(parent)
                shutil.rmtree(parent, ignore_errors=True)
            elif os.path.exists(path):
                os.remove(path)
        except OSError:
            continue


def extract_text_easyocr(image_path: str, use_variants: bool = True) -> tuple[str, float]:
    """Run EasyOCR on image (and variants); returns (text, avg_confidence)."""
    try:
        reader = get_easyocr_reader()

        paths_to_try = preprocess_image_variants(image_path) if use_variants else [image_path]

        best_text = ''
        best_conf = 0.0
        best_score = (-1, -1.0, -1)

        try:
            for path in paths_to_try:
                # If upright variants have already identified medicines, skip expensive rotations
                if best_score[0] > 0 and any(rot in path for rot in ('ocr_rotated_90', 'ocr_rotated_270')):
                    logger.info('[OCR] Upright variant already identified medicines; skipping rotation %s', path)
                    continue

                try:
                    results = reader.readtext(path)
                    logger.info('[OCR] EasyOCR on %s: %d blocks', path, len(results))
                    if not results:
                        continue
                    text_parts = [text for (_, text, _) in results]
                    confidences = [conf for (_, _, conf) in results]
                    full_text = '\n'.join(text_parts)
                    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
                    logger.info('[OCR] EasyOCR variant conf=%.2f, chars=%d', avg_conf, len(full_text))
                    parsed = extract_medicines(clean_ocr_text(full_text))
                    usable_fields = sum(
                        bool(item.get(field))
                        for item in parsed
                        for field in ('dosage', 'frequency', 'duration', 'timing')
                    )
                    # Prefer a usable prescription over a high-confidence
                    # orientation that contains only handwritten noise.
                    score = (len(parsed), usable_fields, avg_conf)
                    if score > best_score:
                        best_score = score
                        best_text = full_text
                        best_conf = avg_conf

                    # If all extracted medicines are fully populated with name, dosage,
                    # frequency, and duration with good confidence, we have a complete
                    # extraction and can safely skip subsequent variants.
                    if (
                        len(parsed) >= 1
                        and all(not item.get('needs_verification') for item in parsed)
                        and avg_conf >= CONFIDENCE_THRESHOLD
                    ):
                        logger.info('[OCR] Variant %s yielded complete extraction; skipping remaining variants', path)
                        break
                except Exception as ve:
                    logger.warning('[OCR] EasyOCR failed on variant %s: %s', path, ve)
        finally:
            _cleanup_variants(paths_to_try, image_path)

        logger.info('[OCR] EasyOCR best result: conf=%.2f, chars=%d', best_conf, len(best_text))
        return best_text, best_conf

    except ImportError:
        logger.warning('[OCR] easyocr not installed')
        return '', 0.0
    except Exception as e:
        logger.error('[OCR] EasyOCR fatal error: %s', e, exc_info=True)
        return '', 0.0


def extract_text_tesseract(image_path: str) -> tuple[str, float]:
    """Run Tesseract (pytesseract) on image; returns (text, confidence)."""
    try:
        import pytesseract
        from PIL import Image

        # Try common Windows Tesseract paths
        tess_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\Users\HP\AppData\Local\Programs\Tesseract-OCR\tesseract.exe',
            r'C:\Users\HP\AppData\Local\Tesseract-OCR\tesseract.exe',
        ]
        found = False
        for p in tess_paths:
            if os.path.exists(p):
                pytesseract.pytesseract.tesseract_cmd = p
                logger.info('[OCR] Found Tesseract at: %s', p)
                found = True
                break
        if not found:
            which_tess = shutil.which('tesseract')
            if which_tess:
                pytesseract.pytesseract.tesseract_cmd = which_tess
                logger.info('[OCR] Found Tesseract in PATH at: %s', which_tess)

        img = Image.open(image_path).convert('RGB')
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        texts = [t for t, c in zip(data['text'], data['conf']) if int(c) > 0 and str(t).strip()]
        confs = [int(c) / 100.0 for c in data['conf'] if int(c) > 0]
        full_text = ' '.join(texts)
        avg_conf = sum(confs) / len(confs) if confs else 0.0
        logger.info('[OCR] Tesseract: %d words, avg conf=%.2f', len(texts), avg_conf)
        return full_text, avg_conf
    except ImportError:
        logger.warning('[OCR] pytesseract not installed')
        return '', 0.0
    except Exception as e:
        logger.error('[OCR] Tesseract error: %s', e)
        return '', 0.0


def clean_ocr_text(text: str) -> str:
    """Clean common OCR artefacts."""
    text = re.sub(r'[ \t\r\n]+', ' ', text)       # parsing must cross OCR line breaks
    text = re.sub(r'\n{3,}', '\n\n', text)         # collapse excess blank lines
    text = re.sub(r'[|\\]', 'l', text)             # | and \ → l
    text = re.sub(r'\b0([a-zA-Z])', r'O\1', text)  # 0 before letters → O
    text = re.sub(r'([a-zA-Z])0\b', r'\1O', text)  # 0 after letters → O
    # Common OCR confusion in dosage units; require a numeric prefix so that
    # ordinary words containing "ma", "mJ", or "rng" are never changed.
    text = re.sub(r'(\d+(?:\.\d+)?\s*)(?:ma|mJ|rng)\b', r'\1mg', text, flags=re.IGNORECASE)
    # Some engines split "for 3 days" into "for 3 2" around a line.  Repair
    # only this strongly constrained prescription-duration shape.
    text = re.sub(r'\bfor\s+(\d+)\s+\d+\b', r'for \1 days', text, flags=re.IGNORECASE)
    return text.strip()


def extract_medicines(text: str, ocr_confidence: Optional[float] = None) -> list[dict]:
    """
    Extract medicine name, dosage, frequency, duration from OCR text.
    Returns list of medicine dicts.
    """
    medicines = []
    candidates = []
    for pattern in MEDICINE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            name = match.group(1).strip()
            if len(name) > 3:
                candidates.append((match.start(1), match.end(1), name))
    candidates.sort()
    found_names = set()
    unique_candidates = []
    for start, end, name in candidates:
        normalized = normalize_medicine_name(name)
        if normalized.lower() not in found_names:
            found_names.add(normalized.lower())
            unique_candidates.append((start, end, normalized))

    # Candidate offsets are from the original string; use the original for
    # boundaries and normalize each extracted segment before matching.
    for index, (start, end, name) in enumerate(unique_candidates):
                # A prescription line/segment belongs to this medicine until
                # the next candidate, rather than an arbitrary character window.
                next_start = unique_candidates[index + 1][0] if index + 1 < len(unique_candidates) else len(text)
                context = clean_ocr_text(text[start:next_start].split(';', 1)[0])

                dosage_matches = re.findall('|'.join(DOSAGE_PATTERNS), context, re.IGNORECASE)
                freq_matches   = re.findall('|'.join(FREQUENCY_PATTERNS), context, re.IGNORECASE)
                dur_matches    = re.findall('|'.join(DURATION_PATTERNS), context, re.IGNORECASE)

                def first_nonempty(matches):
                    for m in matches:
                        v = m if isinstance(m, str) else next((x for x in m if x), '')
                        if v.strip():
                            return v.strip()
                    return None

                medicines.append({
                    'name': name,
                    'dosage':    first_nonempty(dosage_matches),
                    'frequency': first_nonempty(freq_matches),
                    'duration':  first_nonempty(dur_matches),
                    'timing': first_nonempty(re.findall(
                        r'\b((?:after|before)\s+(?:meals?|breakfast)|at\s+(?:night|bedtime)|'
                        r'(?:morning|evening|night|bedtime))\b', context, re.IGNORECASE)),
                })
                if ocr_confidence is not None:
                    medicines[-1]['field_confidence'] = {
                        field: round(float(ocr_confidence), 3)
                        for field in ('name', 'dosage', 'frequency', 'duration', 'timing')
                        if medicines[-1].get(field)
                    }
                medicines[-1]['extraction_confidence'] = round(
                    float(ocr_confidence), 3
                ) if ocr_confidence is not None else None
                medicines[-1]['normalization_confidence'] = 1.0
                medicines[-1]['needs_verification'] = not all(
                    medicines[-1].get(field) for field in ('name', 'dosage', 'frequency', 'duration')
                )

    return medicines


def normalize_medicine_name(name: str) -> str:
    """Canonicalize OCR casing/spacing while preserving the observed name."""
    return re.sub(r'\s+', ' ', re.sub(r'[^A-Za-z0-9\- ]', '', name)).strip().title()


UNREADABLE_MSG = (
    'Unable to confidently read this field. '
    'Please verify with a pharmacist or doctor.'
)


def analyze_prescription(image_path: str) -> dict:
    """
    Full prescription OCR pipeline.

    1. Log image info
    2. Try EasyOCR (with image preprocessing)
    3. Fallback to Tesseract if confidence is low or EasyOCR fails
    4. Extract medicines from cleaned text
    5. Return structured result with explicit status
    """
    logger.info('[OCR] ===== analyze_prescription started =====')
    logger.info('[OCR] Image path: %s', image_path)
    if os.path.exists(image_path):
        logger.info('[OCR] File size: %d bytes', os.path.getsize(image_path))
    else:
        logger.error('[OCR] File does not exist: %s', image_path)

    # Log image dimensions
    try:
        from PIL import Image as PILImage
        with PILImage.open(image_path) as pil_img:
            logger.info('[OCR] Image size: %dx%d, mode: %s', pil_img.width, pil_img.height, pil_img.mode)
    except Exception as e:
        logger.warning('[OCR] PIL cannot open image: %s', e)

    raw_text = ''
    confidence = 0.0
    ocr_engine = 'none'
    ocr_errors = []

    # ---- Step 1: EasyOCR ----
    logger.info('[OCR] Running EasyOCR...')
    text_easy, conf_easy = extract_text_easyocr(image_path)
    logger.info('[OCR] EasyOCR result: conf=%.2f, chars=%d', conf_easy, len(text_easy))

    if text_easy.strip():
        raw_text = text_easy
        confidence = conf_easy
        ocr_engine = 'easyocr' if conf_easy >= CONFIDENCE_THRESHOLD else 'easyocr_low_confidence'
        logger.info('[OCR] Using EasyOCR result (engine=%s)', ocr_engine)
    else:
        ocr_errors.append('EasyOCR returned no text')
        logger.warning('[OCR] EasyOCR returned empty text')

    # ---- Step 2: Tesseract fallback if EasyOCR empty or very low confidence ----
    if not raw_text.strip() or confidence < 0.2:
        logger.info('[OCR] Running Tesseract fallback...')
        text_tess, conf_tess = extract_text_tesseract(image_path)
        logger.info('[OCR] Tesseract result: conf=%.2f, chars=%d', conf_tess, len(text_tess))

        if text_tess.strip() and conf_tess > confidence:
            raw_text = text_tess
            confidence = conf_tess
            ocr_engine = 'tesseract'
            logger.info('[OCR] Using Tesseract result')
        elif text_tess.strip() and not raw_text.strip():
            raw_text = text_tess
            confidence = conf_tess
            ocr_engine = 'tesseract_low_confidence'
        else:
            ocr_errors.append('Tesseract returned no better text')

    cleaned_text = clean_ocr_text(raw_text)
    logger.info('[OCR] Cleaned text (%d chars):\n%s', len(cleaned_text), cleaned_text[:500])

    # ---- Step 3: Medicine extraction ----
    medicines = []
    if cleaned_text:
        medicines = extract_medicines(cleaned_text, ocr_confidence=confidence)
        logger.info('[OCR] Extracted %d medicines: %s', len(medicines), [m['name'] for m in medicines])
    else:
        logger.warning('[OCR] No text extracted — medicine extraction skipped')

    # ---- Step 4: Determine status ----
    low_confidence = confidence < CONFIDENCE_THRESHOLD

    if not cleaned_text.strip():
        pipeline_status = 'OCR_FAILED'
        warning = (
            'Unable to extract readable text from this image. '
            'Please try a clearer image (higher resolution, better lighting, or less blur). '
            'Errors: ' + '; '.join(ocr_errors) if ocr_errors else
            'Unable to extract readable text from this image.'
        )
    elif not medicines:
        pipeline_status = 'PARTIAL'
        warning = (
            'OCR extracted text but no medicine names were automatically identified. '
            'The raw text above may still contain useful information.'
        )
    else:
        pipeline_status = 'SUCCESS' if not low_confidence else 'LOW_CONFIDENCE'
        warning = UNREADABLE_MSG if low_confidence else None

    logger.info('[OCR] ===== Done: engine=%s, conf=%.2f, status=%s, medicines=%d =====',
                ocr_engine, confidence, pipeline_status, len(medicines))

    return {
        'raw_text': raw_text,
        'cleaned_text': cleaned_text,
        'ocr_engine': ocr_engine,
        'confidence': round(confidence, 3),
        'low_confidence': low_confidence,
        'medicines': medicines,
        'pipeline_status': pipeline_status,
        'warning': warning,
    }
