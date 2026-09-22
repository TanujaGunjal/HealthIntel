r"""
LangGraph Multi-Agent Health-Information Workflow for HealthIntel
================================================================
A stateful, multi-agent workflow orchestrated with LangGraph:

                      [START]
                         ↓
             [SymptomAnalysisAgent]
                         ↓
          (route_after_symptom_analysis)
                   /            \
    (has symptoms?)              (no symptoms / empty)
                 /                \
 [EvidenceRetrievalAgent]          \
          ↓                         \
 (route_after_evidence)              \
      /         \                     \
(evidence?)   (no_evidence)            \
    /             \                     \
[SafetyAgent]      \                     \
    ↓               \                     \
     \               \                    /
      -----> [FinalResponseAgent] <-------
                         ↓
                       [END]

Agents:
  1. SymptomAnalysisAgent   : Biomedical NER, symptom extraction, negation detection, and classification.
  2. EvidenceRetrievalAgent : MiniLM + FAISS semantic search over medical knowledge base with deduplication.
  3. SafetyAgent            : Red-flag pattern verification; distinguishes positive from denied symptoms.
  4. FinalResponseAgent     : Synthesis of evidence-backed, patient-friendly educational health guidance.

The orchestrator enforces conditional routing based on extracted symptom presence, evidence relevance,
and clinical safety flags.
"""
import logging
from typing import TypedDict, Annotated, Optional, Union
import operator
import re

logger = logging.getLogger(__name__)


# ============================================================
# 1. Shared State
# ============================================================

class AgentState(TypedDict):
    """
    Typed shared state that flows through the LangGraph multi-agent workflow.
    Provides structured fields for each agent's input, analysis, and intermediate decisions.
    """
    # User Input
    user_input: str
    raw_symptoms: str  # Backwards-compatible alias

    # Biomedical NER & Extraction
    extracted_symptoms: list[str]       # Active positive symptoms
    denied_symptoms: list[str]          # Explicitly negated/denied symptoms
    negated_symptoms: list[str]         # Backwards-compatible alias
    positive_text: str                  # Non-negated text context
    duration: Optional[str]
    severity: Optional[str]
    body_area: Optional[str]

    # Classification
    classification: str
    category: str                       # Backwards-compatible alias
    classification_probabilities: dict[str, float]
    category_confidence: float          # Backwards-compatible alias

    # Evidence Retrieval (RAG)
    evidence: list[dict]
    retrieved_passages: list[dict]      # Backwards-compatible alias
    evidence_found: bool
    sources: list[dict]

    # Safety Validation
    safety_status: str                  # 'SAFE', 'WARNING', 'NEEDS_REVIEW', 'UNAVAILABLE'
    safety_flags: list[str]
    safety_notes: str
    is_urgent: bool

    # Final Response
    response: str
    final_response: str                 # Backwards-compatible alias
    limitations: list[str]

    # Workflow Execution State
    workflow_status: str                # 'queued', 'running', 'completed', 'warning', 'no_evidence', 'failed', 'skipped'
    agent_steps: Annotated[list[dict], operator.add]
    error: Optional[str]


_LLM_FAILED = False

def _get_llm():
    """Return configured LLM based on LLM_PROVIDER env var, or None if unavailable."""
    global _LLM_FAILED
    if _LLM_FAILED:
        return None

    try:
        from django.conf import settings
        provider = getattr(settings, 'LLM_PROVIDER', 'gemini')
        api_key = getattr(settings, 'GEMINI_API_KEY', '')
        model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash')
    except Exception:
        provider = 'gemini'
        api_key = ''
        model_name = 'gemini-1.5-flash'

    if provider == 'gemini' and api_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=0.3,
                max_retries=1,
            )
        except ImportError:
            logger.warning('langchain-google-genai not installed')

    # OpenAI fallback
    try:
        from django.conf import settings as s
        oai_key = getattr(s, 'OPENAI_API_KEY', '')
        oai_model = getattr(s, 'OPENAI_MODEL', 'gpt-4o-mini')
    except Exception:
        oai_key = ''
        oai_model = 'gpt-4o-mini'

    if oai_key:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=oai_model, openai_api_key=oai_key, temperature=0.3, max_retries=1)
        except ImportError:
            logger.warning('langchain-openai not installed')

    logger.warning('No LLM configured or available — using deterministic evidence-grounded fallback')
    return None


# ============================================================
# 2. Symptom Analysis Agent
# ============================================================

def symptom_analysis_agent(state: AgentState) -> dict:
    """
    Agent 1: SymptomAnalysisAgent
    Extracts biomedical symptoms, handles negation, identifies duration, severity, and body area,
    and runs TF-IDF + Logistic Regression classification.
    Writes structured information into shared state. Does NOT diagnose diseases.
    """
    logger.info('[Agent] SymptomAnalysisAgent starting')
    user_input = state.get('user_input') or state.get('raw_symptoms') or ''

    # Extract entities if not pre-provided
    extracted = state.get('extracted_symptoms')
    negated = state.get('denied_symptoms') or state.get('negated_symptoms')
    positive_text = state.get('positive_text')
    duration = state.get('duration')
    severity = state.get('severity')
    body_area = state.get('body_area')
    category = state.get('classification') or state.get('category')
    confidence = state.get('category_confidence', 0.5)
    probs = state.get('classification_probabilities', {})

    if extracted is None:
        try:
            from ml.ner_pipeline import extract_entities
            entities = extract_entities(user_input)
            extracted = entities.get('positive_symptoms') or entities.get('symptoms', [])
            negated = entities.get('negated_symptoms', [])
            positive_text = entities.get('positive_text', '')
            duration = entities.get('duration')
            severity = entities.get('severity')
            body_area = entities.get('body_area')
        except Exception as exc:
            logger.error('SymptomAnalysisAgent NER error: %s', exc)
            extracted = []
            negated = []
            positive_text = user_input

    if not category:
        try:
            from ml.classifier import classify_symptoms
            classify_input = ' '.join(extracted or [])
            if positive_text and positive_text.lower() != classify_input.lower():
                classify_input = (classify_input + ' ' + positive_text).strip()
            cls_result = classify_symptoms(classify_input)
            category = cls_result.get('category', 'general')
            confidence = cls_result.get('confidence', 0.5)
            probs = cls_result.get('all_probabilities', {})
        except Exception as exc:
            logger.error('SymptomAnalysisAgent Classifier error: %s', exc)
            category = 'general'
            confidence = 0.5
            probs = {}

    extracted = extracted or []
    negated = negated or []
    has_meaningful_symptoms = len(extracted) > 0

    summary = _fallback_symptom_summary(extracted, negated, duration, severity, body_area, category)
    step_status = 'completed' if has_meaningful_symptoms else ('warning' if user_input.strip() else 'failed')

    step = {
        'agent': 'SymptomAnalysisAgent',
        'status': step_status,
        'output_preview': summary[:200],
        'symptoms': extracted,
        'negated_symptoms': negated,
        'category': category,
        'duration': duration,
        'severity': severity,
        'body_area': body_area,
        'has_meaningful_symptoms': has_meaningful_symptoms,
    }

    return {
        'user_input': user_input,
        'raw_symptoms': user_input,
        'extracted_symptoms': extracted,
        'denied_symptoms': negated,
        'negated_symptoms': negated,
        'positive_text': positive_text or '',
        'duration': duration,
        'severity': severity,
        'body_area': body_area,
        'classification': category,
        'category': category,
        'classification_probabilities': probs,
        'category_confidence': confidence,
        'agent_steps': [step],
        'error': None,
    }


def _fallback_symptom_summary(symptoms, negated, duration, severity, body_area, category):
    parts = []
    if symptoms:
        parts.append(f"Reported symptoms include: {', '.join(symptoms)}.")
    if negated:
        parts.append(f"Reported absent/denied symptoms include: {', '.join(negated)}.")
    if not symptoms and not negated:
        parts.append("No specific or identifiable symptoms were described.")
    if duration:
        parts.append(f"Reported duration is {duration}.")
    if severity:
        parts.append(f"Reported severity is {severity}.")
    if body_area:
        parts.append(f"Affected body region: {body_area}.")
    parts.append(f"Preliminary health category: {category.title()}.")
    return ' '.join(parts)


# ============================================================
# Conditional Router 1: After Symptom Analysis
# ============================================================

def route_after_symptom_analysis(state: AgentState) -> str:
    """
    Conditional router after SymptomAnalysisAgent:
    - If no meaningful positive symptoms are extracted: route directly to FinalResponseAgent.
    - Otherwise: proceed to EvidenceRetrievalAgent.
    """
    symptoms = state.get('extracted_symptoms', [])
    if not symptoms:
        logger.info('[Router] No meaningful positive symptoms -> Bypassing retrieval to FinalResponseAgent')
        return 'response_generation'
    logger.info('[Router] Meaningful symptoms present (%d) -> Routing to EvidenceRetrievalAgent', len(symptoms))
    return 'evidence_retrieval'


# ============================================================
# 3. Evidence Retrieval Agent
# ============================================================

def evidence_retrieval_agent(state: AgentState) -> dict:
    """
    Agent 2: EvidenceRetrievalAgent
    Retrieves evidence from the medical vector index using sentence-transformers MiniLM embeddings.
    Queries ONLY positive symptoms; removes duplicates and preserves metadata.
    """
    logger.info('[Agent] EvidenceRetrievalAgent starting')
    symptoms = state.get('extracted_symptoms', [])
    positive_text = state.get('positive_text', '').strip()

    if not symptoms and not positive_text:
        return {
            'evidence': [],
            'retrieved_passages': [],
            'evidence_found': False,
            'sources': [],
            'agent_steps': [{
                'agent': 'EvidenceRetrievalAgent',
                'status': 'no_evidence',
                'passages_found': 0,
                'top_sources': [],
                'evidence_found': False,
                'message': 'No positive symptoms available to query evidence',
            }],
        }

    # Construct clean retrieval query
    query = ', '.join(symptoms[:5])
    if positive_text and positive_text.lower() != query.lower():
        query = f"{query} {positive_text}".strip()

    passages = []
    engine_error = None
    try:
        from ml.rag_engine import get_rag_engine
        engine = get_rag_engine()
        raw_passages = engine.query(query, top_k=6)

        # Deduplicate passages by text/chunk
        seen_texts = set()
        for p in raw_passages:
            cleaned = re.sub(r'\s+', ' ', p.get('text', '')[:100].strip().lower())
            if cleaned not in seen_texts:
                seen_texts.add(cleaned)
                passages.append(p)
    except FileNotFoundError:
        logger.warning('Medical index not found on disk')
        engine_error = 'Medical index file not found'
    except Exception as exc:
        logger.error('EvidenceRetrievalAgent error: %s', exc)
        engine_error = str(exc)

    # Filter by minimum relevance threshold (0.35)
    valid_passages = [
        p for p in passages
        if float(p.get('similarity_score', 0) or 0) >= 0.35
    ]

    evidence_found = len(valid_passages) > 0

    sources = [
        {
            'title': p.get('title', 'Medical Reference'),
            'source_file': p.get('source_file', ''),
            'similarity_score': p.get('similarity_score'),
            'retrieval_similarity': p.get('similarity_score'),
            'snippet': p.get('text', '')[:400],
            'chunk_index': p.get('chunk_index'),
        }
        for p in valid_passages
    ]

    step_status = 'completed' if evidence_found else 'no_evidence'

    step = {
        'agent': 'EvidenceRetrievalAgent',
        'status': step_status,
        'passages_found': len(sources),
        'top_sources': sources[:3],
        'evidence_found': evidence_found,
        'error': engine_error if not evidence_found else None,
        'message': 'Medical knowledge-base passages retrieved' if evidence_found else 'No relevant medical literature passages found',
    }

    return {
        'evidence': sources,
        'retrieved_passages': sources,
        'evidence_found': evidence_found,
        'sources': sources,
        'agent_steps': [step],
    }


# ============================================================
# Conditional Router 2: After Evidence Retrieval
# ============================================================

def route_after_evidence_retrieval(state: AgentState) -> str:
    """
    Conditional router after EvidenceRetrievalAgent:
    - If evidence_found is False: route directly to FinalResponseAgent (limited-evidence state).
    - If evidence_found is True: proceed to SafetyAgent for safety validation.
    """
    evidence_found = state.get('evidence_found', False)
    if not evidence_found:
        logger.info('[Router] Evidence found is False -> Routing to FinalResponseAgent with limited-evidence state')
        return 'response_generation'
    logger.info('[Router] Evidence found is True -> Routing to SafetyAgent')
    return 'safety_check'


# ============================================================
# 4. Safety Agent
# ============================================================

def safety_agent(state: AgentState) -> dict:
    """
    Agent 3: SafetyAgent
    Checks positive symptoms and non-negated text for urgent red flags.
    CRITICAL: Denied symptoms must NEVER trigger warnings.
    Produces structured safety status: SAFE, WARNING, or NEEDS_REVIEW.
    """
    logger.info('[Agent] SafetyAgent starting')
    symptoms = state.get('extracted_symptoms', [])
    positive_text = state.get('positive_text', '').strip()
    denied = set(s.lower() for s in (state.get('denied_symptoms') or state.get('negated_symptoms') or []))
    severity = (state.get('severity') or '').lower()
    duration = (state.get('duration') or '').lower()

    # Red-flag symptom patterns that warrant urgent care messaging
    URGENT_PATTERNS = [
        'chest pain', 'difficulty breathing', 'shortness of breath', "can't breathe",
        'unconscious', 'loss of consciousness', 'seizure', 'convulsion',
        'stroke', 'facial drooping', 'arm weakness', 'slurred speech',
        'severe bleeding', 'heavy bleeding', 'blood in vomit', 'vomiting blood',
        'severe allergic', 'anaphylaxis', 'throat closing', 'swelling throat',
        'suicidal', 'self-harm', 'overdose',
        'severe chest', 'crushing chest', 'heart attack',
        'high fever', 'fever above', 'fever over',
    ]

    text_to_check = (' '.join(symptoms) + ' ' + positive_text).lower()

    detected_flags = []
    for pattern in URGENT_PATTERNS:
        if pattern in text_to_check:
            # Strictly verify that this pattern is NOT in denied/negated symptoms
            is_denied = any(pattern == d or pattern in d or d in pattern for d in denied)
            if not is_denied:
                detected_flags.append(pattern)

    # Determine structured safety status
    if detected_flags:
        safety_status = 'WARNING'
        is_urgent = True
        safety_notes = (
            "⚠️ IMPORTANT: Potential urgent warning signs detected in your reported symptoms "
            f"({', '.join(detected_flags)}). Please seek immediate emergency medical evaluation "
            "or contact emergency services. Do not rely on educational tools for urgent situations."
        )
    elif severity == 'severe' or 'month' in duration or 'year' in duration:
        safety_status = 'NEEDS_REVIEW'
        is_urgent = False
        safety_notes = (
            "ℹ️ Clinical Review Recommended: Your reported symptoms exhibit prolonged duration or "
            "elevated severity. An in-person clinical consultation with a healthcare provider is recommended."
        )
    else:
        safety_status = 'SAFE'
        is_urgent = False
        safety_notes = (
            "✓ Verified: No acute emergency red flags detected in reported symptoms. "
            "This informational check is for educational purposes only and does not constitute "
            "a clinical diagnosis or medical clearance."
        )

    step = {
        'agent': 'SafetyAgent',
        'status': 'completed' if safety_status != 'WARNING' else 'warning',
        'safety_status': safety_status,
        'is_urgent': is_urgent,
        'safety_flags': detected_flags,
        'safety_result': (
            'Urgent warning signs detected' if safety_status == 'WARNING'
            else 'Clinical review recommended' if safety_status == 'NEEDS_REVIEW'
            else 'Verified: No urgent red flags detected'
        ),
    }

    return {
        'safety_status': safety_status,
        'safety_flags': detected_flags,
        'safety_notes': safety_notes,
        'is_urgent': is_urgent,
        'agent_steps': [step],
    }


# ============================================================
# 5. Final Response Agent
# ============================================================

def final_response_agent(state: AgentState) -> dict:
    """
    Agent 4: FinalResponseAgent
    Combines symptom analysis, evidence, and safety status into a clear, patient-friendly
    educational health explanation. Handles insufficient-input, limited-evidence,
    and urgent warning states dynamically.
    """
    logger.info('[Agent] FinalResponseAgent starting')
    user_input = state.get('user_input') or state.get('raw_symptoms') or ''
    symptoms = state.get('extracted_symptoms', [])
    denied = state.get('denied_symptoms') or state.get('negated_symptoms') or []
    duration = state.get('duration')
    severity = state.get('severity')
    category = state.get('classification') or state.get('category', 'general')
    confidence = state.get('category_confidence', 0.5)
    evidence = state.get('evidence') or state.get('retrieved_passages') or []
    evidence_found = state.get('evidence_found', False)
    safety_status = state.get('safety_status', 'SAFE')
    safety_flags = state.get('safety_flags', [])
    safety_notes = state.get('safety_notes', '')

    existing_steps = state.get('agent_steps', [])
    executed_agents = set(s.get('agent') for s in existing_steps)

    # Track skipped steps for honest, complete workflow status
    synthetic_steps = []
    if 'EvidenceRetrievalAgent' not in executed_agents:
        synthetic_steps.append({
            'agent': 'EvidenceRetrievalAgent',
            'status': 'skipped',
            'passages_found': 0,
            'top_sources': [],
            'message': 'Skipped by router: Insufficient symptoms to query medical database',
        })
    if 'SafetyAgent' not in executed_agents:
        synthetic_steps.append({
            'agent': 'SafetyAgent',
            'status': 'skipped',
            'is_urgent': False,
            'safety_status': 'SAFE',
            'message': 'Skipped by router: Bypassed due to insufficient input or absent evidence',
        })

    # Scenario A: Insufficient / Empty Input
    if not symptoms:
        final_text = (
            "## Clarification Needed\n\n"
            "No specific or identifiable health symptoms could be extracted from your description. "
            "To receive relevant educational health information, please provide more details about "
            "what symptoms you are experiencing (such as fever, cough, nausea, headache), how long you have "
            "had them, and how severe they feel.\n\n"
            "**Important:** HealthIntel is an educational informational assistant and does not diagnose illnesses."
        )
        workflow_status = 'no_evidence'

    # Scenario B: No Evidence Found in Database
    elif not evidence_found:
        final_text = (
            "## Health Information Summary (Limited Medical Evidence)\n\n"
            f"**Reported active symptoms:** {', '.join(symptoms)}\n"
        )
        if denied:
            final_text += f"**Reported absent/denied:** {', '.join(denied)}\n"
        final_text += (
            f"**Preliminary health area:** {category.title()}\n\n"
            "### Medical Evidence Status\n"
            "No directly matching reference documents were retrieved from the medical knowledge base "
            "for this specific symptom combination.\n\n"
            "### Educational Guidance\n"
            "Symptom patterns can stem from diverse clinical causes. Because verified reference evidence "
            "is not available for this presentation, we do not provide unverified conjectures. "
            "Please consult a qualified healthcare professional for a tailored assessment.\n\n"
            "**Notice:** HealthIntel provides educational reference information only and does not diagnose or prescribe."
        )
        workflow_status = 'no_evidence'

    # Scenario C: Urgent Red Flags Detected
    elif safety_status == 'WARNING':
        final_text = (
            "## ⚠️ URGENT MEDICAL ADVISORY\n\n"
            f"**Warning Signs Identified:** Your description includes symptoms that may indicate "
            f"a serious medical condition: **{', '.join(safety_flags)}**.\n\n"
            "**Immediate Action Required:**\n"
            "- Please seek emergency medical care immediately or call your local emergency medical services.\n"
            "- Do not wait or rely on this educational application for emergency evaluation.\n\n"
            "### Symptom Profile\n"
            f"**Reported active symptoms:** {', '.join(symptoms)}\n"
        )
        if denied:
            final_text += f"**Reported absent/denied:** {', '.join(denied)}\n"
        final_text += (
            f"\n### General Reference Context ({category.title()})\n"
        )
        if evidence:
            for p in evidence[:2]:
                final_text += f"- *{p.get('title', 'Reference')}*: {p.get('snippet', '')[:200]}...\n"
        final_text += (
            "\n*Medical Disclaimer: HealthIntel provides educational information only. "
            "Never ignore emergency symptoms or delay seeking professional medical attention.*"
        )
        workflow_status = 'warning'

    # Scenario D: Standard Evidence-Grounded Educational Report
    else:
        llm = _get_llm()
        if llm:
            evidence_context = '\n\n'.join(
                f"[Source {i}: {p.get('title', 'Medical Reference')}]\n{p.get('snippet', '')[:350]}"
                for i, p in enumerate(evidence[:3], 1)
            )
            from langchain_core.messages import HumanMessage, SystemMessage
            system_prompt = (
                "You are HealthIntel, an educational health-information assistant. "
                "Provide evidence-backed health information — NOT medical diagnoses or prescriptions. "
                "Use hedged language: 'may suggest', 'could indicate', 'according to reference literature'. "
                "Explicitly note that denied symptoms are absent. Never invent medical facts or sources. "
                "Structure your response with: Summary | Educational Information | Evidence Notes | Recommendations."
            )
            user_prompt = (
                f"User input: {user_input}\n"
                f"Active symptoms: {', '.join(symptoms)}\n"
                f"Absent/denied symptoms: {', '.join(denied) if denied else 'none'}\n"
                f"Duration: {duration or 'not specified'} | Severity: {severity or 'not specified'}\n"
                f"Category: {category} (confidence: {confidence:.0%})\n\n"
                f"Medical Evidence:\n{evidence_context}\n\n"
                "Write an objective, evidence-grounded educational health summary (200-300 words)."
            )
            try:
                response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
                final_text = response.content
            except Exception as e:
                logger.error('FinalResponseAgent LLM error: %s', e)
                global _LLM_FAILED
                _LLM_FAILED = True
                final_text = _build_rule_based_response(symptoms, denied, duration, severity, category, evidence)
        else:
            final_text = _build_rule_based_response(symptoms, denied, duration, severity, category, evidence)

        workflow_status = 'completed'

    resp_step = {
        'agent': 'FinalResponseAgent',
        'status': 'completed',
        'response_length': len(final_text),
        'has_response': bool(final_text and len(final_text.strip()) > 20),
        'safety_status': safety_status,
        'evidence_found': evidence_found,
    }

    all_new_steps = synthetic_steps + [resp_step]

    limitations = [
        "Educational information only; does not provide clinical diagnosis or treatment plans.",
        "Always seek evaluation from a qualified, licensed healthcare professional.",
    ]

    return {
        'response': final_text,
        'final_response': final_text,
        'workflow_status': workflow_status,
        'limitations': limitations,
        'agent_steps': all_new_steps,
    }


def _build_rule_based_response(symptoms, negated, duration, severity, category, passages):
    """Deterministic evidence-grounded educational response builder."""
    parts = ["## Health Information Summary\n\n"]
    if symptoms:
        parts.append(f"**Reported symptoms:** {', '.join(symptoms)}\n")
    if negated:
        parts.append(f"**Reported absent/denied:** {', '.join(negated)}\n")
    if duration:
        parts.append(f"**Reported duration:** {duration}\n")
    if severity:
        parts.append(f"**Reported severity:** {severity}\n")
    parts.append(f"**Preliminary health category:** {category.title()}\n\n")

    if passages:
        parts.append("### Retrieved Medical Literature\n")
        for p in passages[:2]:
            parts.append(f"- **{p.get('title', 'Reference')}** (Retrieval similarity: {MathRound(p.get('similarity_score'))}%):\n  {p.get('snippet', '')[:300]}...\n\n")

    parts.append(
        "### Clinical Guidance\n"
        "These educational findings outline general health concepts associated with your reported symptoms. "
        "They do not represent a diagnosis or medical evaluation. Please consult a qualified doctor for personalized advice."
    )
    return ''.join(parts)


def MathRound(val):
    if val is None:
        return 0
    return int(round(float(val) * 100))


# ============================================================
# 6. LangGraph StateGraph Construction
# ============================================================

def build_workflow():
    """
    Construct and compile the stateful LangGraph multi-agent workflow
    with conditional routing.
    """
    try:
        from langgraph.graph import StateGraph, END
    except ImportError:
        raise RuntimeError('langgraph not installed')

    workflow = StateGraph(AgentState)

    # Register the 4 agent nodes
    workflow.add_node('symptom_analysis', symptom_analysis_agent)
    workflow.add_node('evidence_retrieval', evidence_retrieval_agent)
    workflow.add_node('safety_check', safety_agent)
    workflow.add_node('response_generation', final_response_agent)

    # Set entry point
    workflow.set_entry_point('symptom_analysis')

    # Conditional router 1: After SymptomAnalysisAgent
    workflow.add_conditional_edges(
        'symptom_analysis',
        route_after_symptom_analysis,
        {
            'evidence_retrieval': 'evidence_retrieval',
            'response_generation': 'response_generation',
        }
    )

    # Conditional router 2: After EvidenceRetrievalAgent
    workflow.add_conditional_edges(
        'evidence_retrieval',
        route_after_evidence_retrieval,
        {
            'safety_check': 'safety_check',
            'response_generation': 'response_generation',
        }
    )

    # Direct edges
    workflow.add_edge('safety_check', 'response_generation')
    workflow.add_edge('response_generation', END)

    return workflow.compile()


# Module-level compiled graph cache
_workflow = None


def get_workflow():
    """Return cached compiled LangGraph workflow instance."""
    global _workflow
    if _workflow is None:
        _workflow = build_workflow()
    return _workflow


# ============================================================
# 7. Workflow Execution Entry Point
# ============================================================

def run_workflow(
    raw_symptoms: str,
    extracted_symptoms: Optional[list[str]] = None,
    negated_symptoms: Optional[list[str]] = None,
    positive_text: Optional[str] = None,
    duration: Optional[str] = None,
    severity: Optional[str] = None,
    body_area: Optional[str] = None,
    category: Optional[str] = None,
    category_confidence: Optional[float] = None,
) -> dict:
    """
    Execute the LangGraph multi-agent workflow and return complete state.
    """
    workflow = get_workflow()

    initial_state: AgentState = {
        'user_input': raw_symptoms,
        'raw_symptoms': raw_symptoms,
        'extracted_symptoms': extracted_symptoms if extracted_symptoms is not None else [],
        'denied_symptoms': negated_symptoms if negated_symptoms is not None else [],
        'negated_symptoms': negated_symptoms if negated_symptoms is not None else [],
        'positive_text': positive_text or '',
        'duration': duration,
        'severity': severity,
        'body_area': body_area,
        'classification': category or 'general',
        'category': category or 'general',
        'classification_probabilities': {},
        'category_confidence': category_confidence if category_confidence is not None else 0.5,
        'evidence': [],
        'retrieved_passages': [],
        'evidence_found': False,
        'sources': [],
        'safety_status': 'SAFE',
        'safety_flags': [],
        'safety_notes': '',
        'is_urgent': False,
        'response': '',
        'final_response': '',
        'limitations': [],
        'workflow_status': 'running',
        'agent_steps': [],
        'error': None,
    }

    try:
        result = workflow.invoke(initial_state)
        return {
            'response': result.get('response') or result.get('final_response', ''),
            'final_response': result.get('final_response') or result.get('response', ''),
            'retrieved_passages': result.get('retrieved_passages') or result.get('evidence', []),
            'evidence': result.get('evidence') or result.get('retrieved_passages', []),
            'evidence_found': result.get('evidence_found', False),
            'safety_notes': result.get('safety_notes', ''),
            'safety_status': result.get('safety_status', 'SAFE'),
            'safety_flags': result.get('safety_flags', []),
            'is_urgent': result.get('is_urgent', False),
            'workflow_status': result.get('workflow_status', 'completed'),
            'agent_steps': result.get('agent_steps', []),
            'limitations': result.get('limitations', []),
            'error': result.get('error'),
        }
    except Exception as exc:
        logger.error('Workflow execution exception: %s', exc, exc_info=True)
        fallback_resp = _build_rule_based_response(
            extracted_symptoms or [], negated_symptoms or [], duration, severity, category or 'general', []
        )
        return {
            'response': fallback_resp,
            'final_response': fallback_resp,
            'retrieved_passages': [],
            'evidence': [],
            'evidence_found': False,
            'safety_notes': "ℹ️ General educational notice: Please consult a healthcare professional.",
            'safety_status': 'SAFE',
            'safety_flags': [],
            'is_urgent': False,
            'workflow_status': 'failed',
            'agent_steps': [
                {
                    'agent': 'SymptomAnalysisAgent',
                    'status': 'completed' if (extracted_symptoms or raw_symptoms) else 'failed',
                    'symptoms': extracted_symptoms or [],
                    'negated_symptoms': negated_symptoms or [],
                },
                {
                    'agent': 'EvidenceRetrievalAgent',
                    'status': 'unavailable',
                    'error': str(exc),
                },
                {
                    'agent': 'SafetyAgent',
                    'status': 'unavailable',
                },
                {
                    'agent': 'FinalResponseAgent',
                    'status': 'completed' if fallback_resp else 'failed',
                },
            ],
            'limitations': ["Educational information only."],
            'error': str(exc),
        }
