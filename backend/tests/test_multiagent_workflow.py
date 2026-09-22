"""
Pytest Suite for LangGraph Multi-Agent Health-Information Workflow
==================================================================
Tests the 4 LangGraph agents:
  1. SymptomAnalysisAgent
  2. EvidenceRetrievalAgent
  3. SafetyAgent
  4. FinalResponseAgent

And validates conditional routing, shared state, negation safety, and limited-evidence states.
"""
import pytest
from ml.agent_workflow import run_workflow, build_workflow
from ml.ner_pipeline import extract_entities
from ml.classifier import classify_symptoms


@pytest.mark.django_db
class TestMultiAgentWorkflow:

    def test_workflow_compilation(self):
        """Verify the LangGraph StateGraph compiles and produces a runnable application."""
        app = build_workflow()
        assert app is not None

    def test_scenario_a_standard_symptoms(self):
        """
        Scenario A: "I have fever and cough."
        Expected: SymptomAnalysis -> Evidence -> Safety -> Response (all completed, safe)
        """
        raw = "I have fever and cough."
        entities = extract_entities(raw)
        pos = entities.get('positive_symptoms') or entities.get('symptoms', [])
        cls_res = classify_symptoms(' '.join(pos))

        result = run_workflow(
            raw_symptoms=raw,
            extracted_symptoms=pos,
            negated_symptoms=entities.get('negated_symptoms', []),
            category=cls_res['category'],
            category_confidence=cls_res['confidence'],
        )

        steps = {s['agent']: s for s in result.get('agent_steps', [])}
        assert 'SymptomAnalysisAgent' in steps
        assert 'EvidenceRetrievalAgent' in steps
        assert 'SafetyAgent' in steps
        assert 'FinalResponseAgent' in steps

        assert steps['SymptomAnalysisAgent']['status'] == 'completed'
        assert steps['EvidenceRetrievalAgent']['status'] == 'completed'
        assert steps['SafetyAgent']['status'] == 'completed'
        assert steps['FinalResponseAgent']['status'] == 'completed'

        assert result['safety_status'] == 'SAFE'
        assert result['is_urgent'] is False
        assert result['evidence_found'] is True
        assert len(result['evidence']) > 0
        assert result['workflow_status'] == 'completed'
        assert len(result['final_response']) > 50

    def test_scenario_b_negated_symptoms_no_false_warning(self):
        """
        Scenario B: "I have fever but no chest pain or difficulty breathing."
        Expected: fever positive, chest pain denied, difficulty breathing denied, NO false safety warning
        """
        raw = "I have fever but no chest pain or difficulty breathing."
        entities = extract_entities(raw)
        pos = entities.get('positive_symptoms', [])
        neg = entities.get('negated_symptoms', [])

        assert 'fever' in pos
        assert any('chest pain' in n for n in neg)
        assert any('difficulty breathing' in n or 'breathing' in n for n in neg)

        result = run_workflow(
            raw_symptoms=raw,
            extracted_symptoms=pos,
            negated_symptoms=neg,
            positive_text=entities.get('positive_text', ''),
            category='respiratory',
            category_confidence=0.8,
        )

        assert result['safety_status'] == 'SAFE'
        assert result['is_urgent'] is False
        assert len(result.get('safety_flags', [])) == 0
        # Denied symptoms must not trigger warning
        assert result['workflow_status'] == 'completed'

    def test_scenario_c_red_flag_warning(self):
        """
        Scenario C: "I have severe crushing chest pain and shortness of breath."
        Expected: SafetyAgent produces WARNING / is_urgent=True, FinalResponseAgent receives safety state.
        """
        raw = "I have severe crushing chest pain and shortness of breath."
        entities = extract_entities(raw)
        pos = entities.get('positive_symptoms') or entities.get('symptoms', [])

        result = run_workflow(
            raw_symptoms=raw,
            extracted_symptoms=pos,
            negated_symptoms=entities.get('negated_symptoms', []),
            category='cardiovascular',
            category_confidence=0.9,
        )

        steps = {s['agent']: s for s in result.get('agent_steps', [])}
        assert steps['SafetyAgent']['status'] == 'warning'
        assert result['safety_status'] == 'WARNING'
        assert result['is_urgent'] is True
        assert result['workflow_status'] == 'warning'
        assert "URGENT MEDICAL ADVISORY" in result['final_response']

    def test_scenario_d_empty_meaningless_input(self):
        """
        Scenario D: "hello good morning"
        Expected: Router skips EvidenceRetrieval and SafetyAgent; FinalResponseAgent receives insufficient-input state.
        """
        result = run_workflow(
            raw_symptoms="hello good morning",
            extracted_symptoms=[],
            negated_symptoms=[],
            category='general',
            category_confidence=0.5,
        )

        steps = {s['agent']: s for s in result.get('agent_steps', [])}
        assert steps['EvidenceRetrievalAgent']['status'] == 'skipped'
        assert steps['SafetyAgent']['status'] == 'skipped'
        assert result['evidence_found'] is False
        assert result['workflow_status'] == 'no_evidence'
        assert "Clarification Needed" in result['final_response']

    def test_scenario_e_no_matching_evidence(self):
        """
        Scenario E: Non-matching / rare symptom input where FAISS has zero matching literature.
        Expected: evidence_found=False, Router skips SafetyAgent, FinalResponse clearly states evidence limitation.
        """
        result = run_workflow(
            raw_symptoms="I have mysterious alien metamorphosis",
            extracted_symptoms=["mysterious alien metamorphosis"],
            negated_symptoms=[],
            positive_text="mysterious alien metamorphosis",
            category="general",
            category_confidence=0.5,
        )

        steps = {s['agent']: s for s in result.get('agent_steps', [])}
        assert steps['EvidenceRetrievalAgent']['status'] in ('no_evidence', 'unavailable')
        assert steps['SafetyAgent']['status'] == 'skipped'
        assert result['evidence_found'] is False
        assert len(result['evidence']) == 0
        assert "Limited Medical Evidence" in result['final_response']
