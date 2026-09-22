"""Focused tests for prescription extraction response semantics."""
def test_validation_is_failed_when_no_medicines():
    from apps.prescriptions.views import _validation

    result = _validation([])

    assert result['status'] == 'failed'
    assert result['warnings']


def test_validation_is_partial_for_missing_instruction_fields():
    from apps.prescriptions.views import _validation

    result = _validation([{
        'name': 'Amoxicillin',
        'dosage': '500 mg',
        'frequency': None,
        'duration': None,
    }])

    assert result['status'] == 'partial'
    assert any('Frequency' in warning for warning in result['warnings'])


def test_schedule_does_not_infer_unknown_timing():
    from apps.prescriptions.views import _schedule

    result = _schedule([{
        'name': 'Amoxicillin',
        'dosage': '500 mg',
        'frequency': 'twice a day',
        'duration': '5 days',
        'timing': None,
    }])

    assert result == [{
        'period': 'Timing not specified',
        'medicine': 'Amoxicillin',
        'dosage': '500 mg',
        'frequency': 'twice a day',
        'duration': '5 days',
        'instruction': 'twice a day',
    }]


def test_evidence_reports_no_matches_truthfully(monkeypatch):
    from apps.prescriptions import views

    class EmptyEngine:
        def query(self, name, top_k=1):
            return []

    monkeypatch.setattr('ml.rag_engine.get_rag_engine', lambda: EmptyEngine())
    result = views._evidence([{'name': 'Amoxicillin'}])

    assert result == {'status': 'NO_MATCHES', 'items': []}


def test_extractor_keeps_structured_instruction_fields():
    from ml.ocr_pipeline import extract_medicines

    result = extract_medicines(
        'Amoxicillin 500 mg twice a day for 5 days after meals',
        ocr_confidence=0.95,
    )

    assert result
    medicine = next(item for item in result if item['name'] == 'Amoxicillin')
    assert medicine['dosage'] == '500 mg'
    assert medicine['frequency'].lower() == 'twice a day'
    assert medicine['duration'] == '5 days'
    assert medicine['timing'].lower() == 'after meals'


def test_extractor_preserves_each_medicine_instruction_segment():
    from ml.ocr_pipeline import extract_medicines

    result = extract_medicines(
        'Paracetamol 500 mg twice daily 3 days; '
        'Cetirizine 10 mg once daily at night 5 days; '
        'Pantoprazole 40 mg once daily before breakfast 5 days',
        ocr_confidence=0.95,
    )

    assert [(item['name'], item['dosage'], item['frequency'], item['duration'], item['timing'])
            for item in result] == [
        ('Paracetamol', '500 mg', 'twice daily', '3 days', None),
        ('Cetirizine', '10 mg', 'once daily', '5 days', 'at night'),
        ('Pantoprazole', '40 mg', 'once daily', '5 days', 'before breakfast'),
    ]
    assert all(item['field_confidence']['dosage'] == 0.95 for item in result)


def test_evidence_filters_irrelevant_low_similarity_results(monkeypatch):
    from apps.prescriptions import views

    class IrrelevantEngine:
        def query(self, name, top_k=1):
            return [{'text': 'unrelated', 'source_file': 'x', 'similarity_score': 0.2}]

    monkeypatch.setattr('ml.rag_engine.get_rag_engine', lambda: IrrelevantEngine())
    assert views._evidence([{'name': 'Paracetamol'}]) == {
        'status': 'NO_MATCHES', 'items': []
    }


def test_extractor_repairs_ocr_line_breaks_units_and_keeps_timing_out_of_frequency():
    from ml.ocr_pipeline import extract_medicines

    result = extract_medicines(
        'Paracetamol\n500 ma\ntwice\ndaily\nfor\n3\n2; '
        'Pantoprazole\n40 ma\nbefore breakfast\nfor 5 days\nTake tablet once daily',
        ocr_confidence=0.8,
    )

    paracetamol = next(item for item in result if item['name'] == 'Paracetamol')
    pantoprazole = next(item for item in result if item['name'] == 'Pantoprazole')
    assert paracetamol['dosage'] == '500 mg'
    assert paracetamol['frequency'] == 'twice daily'
    assert paracetamol['duration'] == '3 days'
    assert pantoprazole['dosage'] == '40 mg'
    assert pantoprazole['frequency'] == 'once daily'
    assert pantoprazole['timing'] == 'before breakfast'
    assert pantoprazole['frequency'] != pantoprazole['timing']
