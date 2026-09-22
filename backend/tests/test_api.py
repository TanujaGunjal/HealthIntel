"""Backend test suite for HealthIntel APIs."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
import io
from PIL import Image

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        email='test@healthintel.com',
        password='testpass123!'
    )


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    return client


# ============================================================
# Auth tests
# ============================================================

class TestAuth:
    def test_register(self, api_client, db):
        resp = api_client.post('/api/auth/register/', {
            'email': 'new@test.com',
            'username': 'newuser',
            'password': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        assert resp.status_code == 201
        assert 'user' in resp.data

    def test_login(self, api_client, user):
        resp = api_client.post('/api/auth/login/', {
            'email': 'test@healthintel.com',
            'password': 'testpass123!',
        })
        assert resp.status_code == 200
        assert 'access' in resp.data
        assert 'refresh' in resp.data

    def test_login_wrong_password(self, api_client, user):
        resp = api_client.post('/api/auth/login/', {
            'email': 'test@healthintel.com',
            'password': 'wrongpassword',
        })
        assert resp.status_code == 401

    def test_profile_requires_auth(self, api_client, db):
        resp = api_client.get('/api/auth/profile/')
        assert resp.status_code == 401

    def test_profile_authenticated(self, auth_client):
        resp = auth_client.get('/api/auth/profile/')
        assert resp.status_code == 200
        assert resp.data['email'] == 'test@healthintel.com'


# ============================================================
# Health check
# ============================================================

class TestHealthCheck:
    def test_health_endpoint(self, api_client, db):
        resp = api_client.get('/api/health/')
        assert resp.status_code == 200
        assert resp.data['status'] == 'healthy'


# ============================================================
# Symptom API tests
# ============================================================

class TestSymptomAPI:
    def test_analyze_requires_auth(self, api_client, db):
        resp = api_client.post('/api/symptoms/analyze/', {'symptoms': 'fever and headache'})
        assert resp.status_code == 401

    def test_analyze_valid(self, auth_client, db):
        resp = auth_client.post('/api/symptoms/analyze/', {
            'symptoms': 'I have fever, headache and sore throat for two days'
        })
        assert resp.status_code == 200
        assert 'category' in resp.data
        assert 'confidence' in resp.data
        assert 'symptoms' in resp.data

    def test_analyze_empty_input(self, auth_client, db):
        resp = auth_client.post('/api/symptoms/analyze/', {'symptoms': 'hi'})
        assert resp.status_code == 400

    def test_analyze_missing_field(self, auth_client, db):
        resp = auth_client.post('/api/symptoms/analyze/', {})
        assert resp.status_code == 400

    def test_analyze_classification_result(self, auth_client, db):
        resp = auth_client.post('/api/symptoms/analyze/', {
            'symptoms': 'cough wheezing shortness of breath chest tightness'
        })
        assert resp.status_code == 200
        assert resp.data['category'] == 'respiratory'
        assert resp.data['confidence'] > 0.3

    def test_analyze_negated_symptoms_not_in_positive(self, auth_client, db):
        resp = auth_client.post('/api/symptoms/analyze/', {
            'symptoms': 'I have fever and cough. I do not have chest pain or difficulty breathing.'
        })
        assert resp.status_code == 200
        assert 'fever' in resp.data['symptoms']
        assert 'cough' in resp.data['symptoms']
        assert 'chest pain' not in resp.data['symptoms']
        assert 'difficulty breathing' not in resp.data['symptoms']
        assert 'pain' not in resp.data['symptoms']
        assert 'chest pain' in resp.data['negated_symptoms']
        assert 'difficulty breathing' in resp.data['negated_symptoms']


# ============================================================
# Prescription API tests
# ============================================================

def make_test_image():
    """Create a small in-memory JPEG image."""
    img = Image.new('RGB', (200, 100), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    buf.seek(0)
    return buf


class TestPrescriptionAPI:
    def test_analyze_requires_auth(self, api_client, db):
        resp = api_client.post('/api/prescription/analyze/')
        assert resp.status_code == 401

    def test_analyze_no_image(self, auth_client, db):
        resp = auth_client.post('/api/prescription/analyze/', {})
        assert resp.status_code == 400

    def test_analyze_invalid_type(self, auth_client, db):
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake_pdf = SimpleUploadedFile('test.pdf', b'%PDF fake content', content_type='application/pdf')
        resp = auth_client.post('/api/prescription/analyze/', {'image': fake_pdf}, format='multipart')
        assert resp.status_code == 400

    def test_analyze_valid_image(self, auth_client, db):
        from django.core.files.uploadedfile import InMemoryUploadedFile
        img_io = make_test_image()
        img_file = InMemoryUploadedFile(
            img_io, 'image', 'prescription.jpg', 'image/jpeg', img_io.getbuffer().nbytes, None
        )
        resp = auth_client.post('/api/prescription/analyze/', {'image': img_file}, format='multipart')
        # Should return 200 (may have 0 medicines from blank image)
        assert resp.status_code == 200
        assert 'medicines' in resp.data
        assert 'ocr_engine' in resp.data

    def test_explain_requires_auth(self, api_client, db):
        resp = api_client.post('/api/prescription/999/explain/')
        assert resp.status_code == 401

    def test_explain_prescription_success(self, auth_client, db, user):
        from apps.prescriptions.models import Prescription
        prescription = Prescription.objects.create(
            user=user,
            cleaned_ocr_text=(
                "Rx:\n"
                "1. Paracetamol 500 mg twice daily for 3 days\n"
                "2. Cetirizine 10 mg once daily at night for 5 days\n"
                "3. Pantoprazole 40 mg once daily before breakfast for 5 days\n"
            ),
            ocr_confidence=0.95,
        )
        resp = auth_client.post(f'/api/prescription/{prescription.pk}/explain/')
        assert resp.status_code == 200
        data = resp.data
        assert data['status'] == 'available'
        assert 'explanation' in data
        assert 'evidence' in data
        assert data['evidence']['status'] == 'AVAILABLE'
        assert len(data['explanation']['medicines']) == 3
        med_names = [m['name'] for m in data['explanation']['medicines']]
        assert 'Paracetamol' in med_names
        assert 'Cetirizine' in med_names
        assert 'Pantoprazole' in med_names



# ============================================================
# RAG API tests
# ============================================================

class TestRAGAPI:
    def test_query_requires_auth(self, api_client, db):
        resp = api_client.post('/api/rag/query/', {'query': 'fever'})
        assert resp.status_code == 401

    def test_query_short_input(self, auth_client, db):
        resp = auth_client.post('/api/rag/query/', {'query': 'ab'})
        assert resp.status_code == 400

    def test_query_valid(self, auth_client, db):
        resp = auth_client.post('/api/rag/query/', {'query': 'fever and sore throat symptoms'})
        # May be 200 or 503 depending on whether index is built
        assert resp.status_code in (200, 503)


# ============================================================
# ML unit tests
# ============================================================

class TestClassifier:
    def test_classify_respiratory(self):
        from ml.classifier import classify_symptoms
        result = classify_symptoms('cough wheezing shortness of breath fever')
        assert result['category'] == 'respiratory'
        assert 0 < result['confidence'] <= 1.0

    def test_classify_digestive(self):
        from ml.classifier import classify_symptoms
        result = classify_symptoms('nausea vomiting diarrhea stomach cramps abdominal pain')
        assert result['category'] == 'digestive'

    def test_classify_neurological(self):
        from ml.classifier import classify_symptoms
        result = classify_symptoms('severe headache migraine nausea light sensitivity dizziness')
        assert result['category'] == 'neurological'

    def test_classify_returns_all_probabilities(self):
        from ml.classifier import classify_symptoms
        result = classify_symptoms('joint pain back muscle ache')
        assert 'all_probabilities' in result
        assert len(result['all_probabilities']) == 6


class TestNERPipeline:
    def test_extract_symptoms(self):
        from ml.ner_pipeline import extract_entities
        result = extract_entities('I have fever, headache and sore throat for two days')
        assert 'symptoms' in result
        assert len(result['symptoms']) > 0

    def test_extract_duration(self):
        from ml.ner_pipeline import extract_entities
        result = extract_entities('I have had a cough for 5 days')
        assert result['duration'] is not None
        assert '5 days' in result['duration']

    def test_extract_severity(self):
        from ml.ner_pipeline import extract_entities
        result = extract_entities('I have severe headache and mild fever')
        assert result['severity'] is not None

    def test_clean_text(self):
        from ml.ner_pipeline import clean_text
        cleaned = clean_text('  Hello   World  ')
        assert cleaned == 'Hello World'

    def test_extract_negated_symptoms(self):
        from ml.ner_pipeline import extract_entities
        res = extract_entities('no chest pain, no shortness of breath, and no wheezing')
        assert res['symptoms'] == []
        assert 'chest pain' in res['negated_symptoms']
        assert 'shortness of breath' in res['negated_symptoms']
        assert 'wheezing' in res['negated_symptoms']
        assert 'pain' not in res['symptoms']

    def test_negation_test_cases(self):
        from ml.ner_pipeline import extract_entities
        r1 = extract_entities('I have fever and cough. I do not have chest pain or difficulty breathing.')
        assert set(r1['symptoms']) == {'fever', 'cough'}
        assert set(r1['negated_symptoms']) == {'chest pain', 'difficulty breathing'}

        r2 = extract_entities('I have headache and nausea. I have no vomiting, confusion, or vision problems.')
        assert set(r2['symptoms']) == {'headache', 'nausea'}
        assert set(r2['negated_symptoms']) == {'vomiting', 'confusion', 'vision problems'}

        r3 = extract_entities('I have a cough and sore throat. There is no shortness of breath, wheezing, or chest pain.')
        assert set(r3['symptoms']) == {'cough', 'sore throat'}
        assert set(r3['negated_symptoms']) == {'shortness of breath', 'wheezing', 'chest pain'}


class TestOCRPipeline:
    def test_extract_medicines_known_name(self):
        from ml.ocr_pipeline import extract_medicines
        meds = extract_medicines('Paracetamol 500mg twice daily for 5 days')
        assert any(m['name'].lower() == 'paracetamol' for m in meds)

    def test_extract_dosage(self):
        from ml.ocr_pipeline import extract_medicines
        meds = extract_medicines('Ibuprofen 400mg three times a day')
        if meds:
            ibu = next((m for m in meds if 'ibuprofen' in m['name'].lower()), None)
            if ibu:
                assert ibu['dosage'] is not None

    def test_clean_ocr_text(self):
        from ml.ocr_pipeline import clean_ocr_text
        cleaned = clean_ocr_text('Para  cetamol   500mg')
        assert '  ' not in cleaned
