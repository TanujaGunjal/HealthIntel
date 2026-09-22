"""
Biomedical Named Entity Recognition and Negation Pipeline.

Primary: Comprehensive clinical entity matching + rule-based clinical negation (NegEx/ConText patterns).
Augmentation: spaCy en_core_web_sm (or scispaCy) for supplementary entity detection.

Features:
- Precise medical entity boundary matching (longest entity match first to prevent sub-token leakage).
- Robust negation detection:
  * "no X", "no X or Y", "not X", "don't have X", "without X", "denies X", "negative for X"
  * Multi-item lists ("no shortness of breath, wheezing, or chest pain")
- Complete entity negation:
  * "no chest pain" -> excludes "chest pain" AND excludes generic "pain"
  * "no shortness of breath" -> excludes "shortness of breath"
- Clear separation:
  * positive_symptoms
  * negated_symptoms
  * positive_text (cleaned non-negated text for downstream classifiers/safety agents)
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---- Duration patterns ----
DURATION_PATTERNS = [
    r'(?:for|since|over|past|last)\s+(?:the\s+)?(\d+\s+(?:days?|weeks?|months?|hours?|years?))',
    r'(\d+\s*(?:-|\s+)?(?:days?|weeks?|months?|hours?|years?))',
    r'(since\s+(?:yesterday|last\s+\w+|this\s+morning|this\s+week))',
    r'((?:a|an|one)\s+(?:day|week|month))',
    r'(two|three|four|five|six|seven)\s+(?:days|weeks|months)',
]

# ---- Severity patterns ----
SEVERITY_PATTERNS = [
    r'\b(mild|moderate|severe|intense|slight|extreme|unbearable|terrible|awful)\b',
    r'\b(a\s+little|a\s+lot|very\s+(?:bad|severe|mild))\b',
]

# ---- Body area patterns ----
BODY_AREA_PATTERNS = [
    r'\b(head|neck|chest|back|abdomen|stomach|shoulder|arm|leg|knee|foot|feet|'
    r'throat|nose|ear|eye|eyes|skin|joint|muscle|hip|wrist|ankle|groin|pelvis)\b',
]

# ---- Clinical Negation Triggers ----
PRE_NEGATION_PATTERNS = [
    r'\b(?:(?:i|we|patient|he|she)\s+)?(?:do|does|did)\s+not\s+(?:have|experience|feel|notice|report|complain\s+of)\b',
    r'\b(?:(?:i|we|patient|he|she)\s+)?(?:don\'?t|doesn\'?t|didn\'?t)\s+(?:have|experience|feel|notice|report|complain\s+of)\b',
    r'\b(?:(?:i|we|patient|he|she)\s+)?(?:do|does|did)\s+not\s+have\b',
    r'\b(?:(?:i|we|patient|he|she)\s+)?(?:don\'?t|doesn\'?t|didn\'?t)\s+have\b',
    r'\b(?:(?:i|we|patient|he|she)\s+)?(?:have|has|had)\s+not\s+(?:had|experienced|felt|noticed|reported)\b',
    r'\b(?:(?:i|we|patient|he|she)\s+)?(?:haven\'?t|hasn\'?t|hadn\'?t)\s+(?:had|experienced|felt|noticed|reported)\b',
    r'\b(?:(?:i|we|patient|he|she)\s+)?(?:haven\'?t|hasn\'?t|hadn\'?t)\b',
    r'\b(?:(?:i|we|patient|he|she)\s+)?(?:have|has|had)\s+no\b',
    r'\b(?:there\s+is|there\s+are|there\s+was|there\s+were)\s+no\b',
    r'\b(?:there\s+isn\'?t|there\s+aren\'?t|there\s+wasn\'?t|there\s+weren\'?t)\s+(?:any\s+)?\b',
    r'\b(?:no\s+signs?\s+of|no\s+symptoms?\s+of|no\s+evidence\s+of|no\s+history\s+of|no\s+complaint\s+of)\b',
    r'\b(?:negative\s+for|neg\s+for)\b',
    r'\b(?:denies|denied|denying|deny)\b',
    r'\b(?:without\s+any|without)\b',
    r'\b(?:free\s+of|free\s+from)\b',
    r'\b(?:rules?\s+out|ruled\s+out)\b',
    r'\b(?:never\s+had|never\s+have|never\s+experienced)\b',
    r'\b(?:not\s+experiencing|not\s+feeling|not\s+noticing|not\s+having|not\s+presenting\s+with)\b',
    r'\bnot\b',
    r'\bno\b',
    r'\bnone\b',
    r'\bneither\b',
    r'\bzero\b',
]

POST_NEGATION_PATTERNS = [
    r'\b(?:is|was|were|are)\s+ruled\s+out\b',
    r'\b(?:is|was|were|are)\s+(?:absent|negative|not\s+present|denied)\b',
    r':\s*(?:none|negative|no|denied|absent)\b',
]

TERMINATOR_PATTERNS = [
    r'[.;!?\n]',
    r'\b(?:but|however|although|except|apart\s+from|aside\s+from|yet|though|nevertheless|nonetheless|save\s+for)\b',
    r'\b(?:(?:i|we|patient)\s+(?:have|had|am\s+having|have\s+got|report|reports|developed|present|presents))\b',
]

# ---- Medical Symptom Entities (sorted by length descending for greedy match) ----
RAW_MEDICAL_ENTITIES = [
    # Critical / Red Flag Entities
    'crushing chest pain', 'severe chest pain', 'chest tightness', 'chest pressure', 'chest pain',
    'shortness of breath', 'difficulty breathing', 'trouble breathing', 'breathlessness',
    'cannot breathe', 'hard to breathe', "can't breathe", 'cant breathe',
    'loss of consciousness', 'unconscious', 'fainting', 'syncope',
    'seizure', 'convulsion',
    'facial drooping', 'slurred speech', 'arm weakness', 'leg weakness', 'stroke',
    'vomiting blood', 'blood in vomit', 'coughing blood', 'severe bleeding',
    'anaphylaxis', 'throat closing', 'swelling throat',
    # Respiratory Entities
    'persistent cough', 'productive cough', 'dry cough', 'coughing', 'cough',
    'difficulty swallowing', 'sore throat', 'throat pain', 'hoarseness',
    'wheezing', 'stridor', 'nasal congestion', 'runny nose', 'stuffy nose',
    'congestion', 'sneezing', 'phlegm', 'mucus',
    # Neurological / Sensory Entities
    'severe headache', 'cluster headache', 'migraine', 'headache',
    'blurred vision', 'double vision', 'vision problems', 'loss of vision',
    'dizziness', 'lightheadedness', 'vertigo', 'loss of balance',
    'confusion', 'disorientation', 'memory loss',
    'numbness', 'tingling', 'tremor', 'insomnia', 'anxiety',
    # Gastrointestinal Entities
    'abdominal cramps', 'abdominal pain', 'stomach cramps', 'stomach pain',
    'acid reflux', 'heartburn', 'indigestion', 'bloating', 'constipation',
    'diarrhea', 'vomiting', 'nausea', 'burping', 'gas',
    # Systemic / General Entities
    'high fever', 'fever', 'chills', 'night sweats', 'sweating',
    'fatigue', 'tiredness', 'exhaustion', 'general weakness', 'weakness', 'malaise',
    'loss of appetite', 'weight loss', 'body ache',
    # Musculoskeletal Entities
    'neck stiffness', 'neck pain', 'joint pain', 'muscle ache', 'muscle pain',
    'back pain', 'hip pain', 'knee pain', 'wrist pain', 'shoulder pain',
    # Dermatological Entities
    'skin rash', 'rash', 'hives', 'itching', 'swelling', 'skin redness', 'blisters',
    # Fallback anatomical pain keywords
    'ear pain', 'palpitations', 'pain', 'ache',
]

MEDICAL_ENTITIES = sorted(set(RAW_MEDICAL_ENTITIES), key=len, reverse=True)


def _extract_with_regex(text: str, patterns: list[str]) -> list[str]:
    """Extract all regex matches from text."""
    results = []
    for pat in patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        results.extend([m if isinstance(m, str) else ' '.join(m) for m in matches])
    return results


def _load_spacy_model():
    """Attempt to load scispaCy then fallback to en_core_web_sm."""
    try:
        import spacy
        try:
            nlp = spacy.load('en_core_sci_sm')
            logger.info('NER: loaded scispaCy en_core_sci_sm')
            return nlp, 'scispacy'
        except OSError:
            pass
        try:
            nlp = spacy.load('en_core_web_sm')
            logger.info('NER: loaded spaCy en_core_web_sm')
            return nlp, 'spacy'
        except OSError:
            logger.warning('NER: no spaCy model available, using regex fallback')
            return None, 'regex'
    except ImportError:
        logger.warning('NER: spaCy not installed, using regex fallback')
        return None, 'regex'


# Module-level model cache
_nlp_model = None
_nlp_source = None


def get_nlp():
    """Return cached NLP model (load once per process)."""
    global _nlp_model, _nlp_source
    if _nlp_model is None:
        _nlp_model, _nlp_source = _load_spacy_model()
    return _nlp_model, _nlp_source


def clean_text(text: str) -> str:
    """Strip extra whitespace, normalize characters while preserving apostrophes & basic punctuation."""
    text = re.sub(r'\s+', ' ', text.strip())
    text = re.sub(r"[^\w\s\.\,\'\-;:!?]", '', text)
    return text


def detect_negation_spans(text: str):
    """
    Detect character spans of negated clauses in the text.
    Returns:
        merged_spans: list of (start_char, end_char)
        positive_text: text with negated spans stripped
    """
    text_lower = text.lower()
    pre_pat = re.compile('|'.join(f'({p})' for p in PRE_NEGATION_PATTERNS), re.IGNORECASE)
    post_pat = re.compile('|'.join(f'({p})' for p in POST_NEGATION_PATTERNS), re.IGNORECASE)
    term_pat = re.compile('|'.join(f'({t})' for t in TERMINATOR_PATTERNS), re.IGNORECASE)

    neg_spans = []

    # Pre-negation: trigger scopes forward to next terminator or end of string
    for m in pre_pat.finditer(text_lower):
        scope_start = m.start()
        after_trigger = m.end()
        term_match = term_pat.search(text_lower, after_trigger)
        if term_match:
            if term_match.group(0) in '.;!?\n':
                scope_end = term_match.end()
            else:
                scope_end = term_match.start()
        else:
            scope_end = len(text_lower)
        neg_spans.append((scope_start, scope_end))

    # Post-negation: trigger scopes backward to preceding terminator or start of string
    for m in post_pat.finditer(text_lower):
        scope_end = m.end()
        preceding = list(term_pat.finditer(text_lower[:m.start()]))
        scope_start = preceding[-1].end() if preceding else 0
        neg_spans.append((scope_start, scope_end))

    # Merge overlapping spans
    merged_spans = []
    for s, e in sorted(neg_spans):
        if merged_spans and s <= merged_spans[-1][1]:
            merged_spans[-1] = (merged_spans[-1][0], max(merged_spans[-1][1], e))
        else:
            merged_spans.append((s, e))

    # Generate positive_text
    pos_parts = []
    curr = 0
    for s, e in merged_spans:
        if s > curr:
            pos_parts.append(text[curr:s])
        curr = max(curr, e)
    if curr < len(text):
        pos_parts.append(text[curr:])

    positive_text = ' '.join(''.join(pos_parts).split())
    # Clean trailing or leading punctuation
    positive_text = re.sub(r'\s+([.,;:!?])', r'\1', positive_text)
    positive_text = re.sub(r'^[.,;:!?\s]+|[.,;:!?\s]+$', '', positive_text)

    return merged_spans, positive_text


def extract_entities(text: str) -> dict:
    """
    Extract biomedical entities from a symptom description with strict negation handling.

    Returns:
        {
            'symptoms': [...],             # Positive symptoms only
            'positive_symptoms': [...],    # Explicit positive symptoms
            'negated_symptoms': [...],     # Explicit negated symptoms
            'positive_text': '...',        # Text with negated clauses removed
            'duration': '...' or None,
            'severity': '...' or None,
            'body_area': '...' or None,
            'nlp_source': 'scispacy' | 'spacy' | 'regex',
            'cleaned_text': cleaned,
        }
    """
    cleaned = clean_text(text)
    text_lower = cleaned.lower()
    nlp, source = get_nlp()

    merged_neg_spans, positive_text = detect_negation_spans(cleaned)

    def is_negated_span(start: int, end: int) -> bool:
        for ns, ne in merged_neg_spans:
            if not (end <= ns or start >= ne):
                return True
        return False

    # 1. Extract non-overlapping entities (longest matches first)
    extracted = []  # list of (start, end, entity_name)
    for entity in MEDICAL_ENTITIES:
        pattern = r'\b' + re.escape(entity) + r'\b'
        for m in re.finditer(pattern, text_lower):
            s, e = m.start(), m.end()
            overlap = False
            for prev_s, prev_e, _ in extracted:
                if not (e <= prev_s or s >= prev_e):
                    overlap = True
                    break
            if not overlap:
                extracted.append((s, e, entity))

    # 2. Augment with spaCy if available
    if nlp is not None and source in ('scispacy', 'spacy'):
        try:
            doc = nlp(cleaned)
            for ent in doc.ents:
                ent_text = ent.text.strip().lower()
                if len(ent_text) > 2 and ent.label_ in ('ENTITY', 'DISEASE', 'CHEMICAL', 'symptom'):
                    s, e = ent.start_char, ent.end_char
                    overlap = False
                    for prev_s, prev_e, _ in extracted:
                        if not (e <= prev_s or s >= prev_e):
                            overlap = True
                            break
                    if not overlap:
                        extracted.append((s, e, ent_text))
        except Exception as e:
            logger.warning('spaCy entity extraction error: %s', e)

    # Sort entities by appearance in text
    extracted.sort(key=lambda x: x[0])

    pos_symptoms = []
    neg_symptoms = []
    for s, e, ent in extracted:
        if is_negated_span(s, e):
            if ent not in neg_symptoms:
                neg_symptoms.append(ent)
        else:
            if ent not in pos_symptoms:
                pos_symptoms.append(ent)

    # 3. Complete entity protection:
    # If a compound entity is negated (e.g. 'chest pain', 'shortness of breath', 'wheezing'),
    # ensure generic sub-tokens (e.g. 'pain', 'breath', 'vision', 'ache') are NEVER in positive_symptoms.
    cleaned_pos = []
    for p in pos_symptoms:
        if p in neg_symptoms:
            continue
        is_sub = any(p in n.split() for n in neg_symptoms if p in ('pain', 'breath', 'vision', 'ache', 'cough'))
        if not is_sub:
            cleaned_pos.append(p)

    # 4. Extract duration, severity, and body_area from positive context (or cleaned if empty)
    context_for_attributes = positive_text if positive_text else cleaned
    durations = _extract_with_regex(context_for_attributes, DURATION_PATTERNS)
    severities = _extract_with_regex(context_for_attributes, SEVERITY_PATTERNS)
    body_areas = _extract_with_regex(context_for_attributes, BODY_AREA_PATTERNS)

    return {
        'symptoms': cleaned_pos[:15],
        'positive_symptoms': cleaned_pos[:15],
        'negated_symptoms': neg_symptoms[:15],
        'positive_text': positive_text,
        'duration': durations[0].strip() if durations else None,
        'severity': severities[0].strip() if severities else None,
        'body_area': body_areas[0].strip() if body_areas else None,
        'nlp_source': source,
        'cleaned_text': cleaned,
    }
