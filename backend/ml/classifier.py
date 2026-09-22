"""
Symptom Category Classifier
============================
Primary: TF-IDF + Logistic Regression (CPU-only, fast)
Optional: DistilBERT fine-tuned (gated by ENABLE_TRANSFORMER_CLASSIFIER env var)

Categories:
  - respiratory
  - digestive
  - neurological
  - dermatological
  - musculoskeletal
  - general
"""
import os
import logging
import pickle
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / 'models_store' / 'tfidf_classifier.pkl'

# ---- Training data ----
# Curated symptom descriptions with category labels
# Enough variety to give the TF-IDF model discriminative signal.
TRAINING_DATA = [
    # respiratory
    ("cough shortness of breath wheezing chest tightness", "respiratory"),
    ("runny nose congestion sneezing sore throat", "respiratory"),
    ("fever cough sore throat difficulty breathing", "respiratory"),
    ("persistent cough phlegm mucus breathlessness", "respiratory"),
    ("asthma attack inhaler chest pressure", "respiratory"),
    ("pneumonia cough fever chest pain", "respiratory"),
    ("bronchitis cough wheeze mucus", "respiratory"),
    ("flu fever body ache runny nose cough", "respiratory"),
    ("cold stuffy nose sneezing mild fever", "respiratory"),
    ("throat pain hoarseness loss of voice", "respiratory"),
    ("sinusitis nasal congestion headache pressure", "respiratory"),
    ("tuberculosis cough blood fever night sweats", "respiratory"),
    ("shortness of breath on exertion chest pain", "respiratory"),
    ("seasonal allergy pollen runny nose sneezing eyes watery", "respiratory"),
    ("covid cough fever loss of smell fatigue", "respiratory"),

    # digestive
    ("nausea vomiting stomach pain diarrhea", "digestive"),
    ("bloating gas abdominal cramps constipation", "digestive"),
    ("heartburn acid reflux burning chest", "digestive"),
    ("food poisoning vomiting diarrhea stomach cramps", "digestive"),
    ("irritable bowel alternating diarrhea constipation", "digestive"),
    ("gallstones right upper abdominal pain after eating", "digestive"),
    ("stomach ulcer burning pain empty stomach", "digestive"),
    ("celiac disease bloating diarrhea after gluten", "digestive"),
    ("liver pain right side jaundice yellow skin", "digestive"),
    ("bloody diarrhea rectal bleeding abdominal pain", "digestive"),
    ("dyspepsia indigestion fullness after eating", "digestive"),
    ("appendicitis right lower abdomen pain fever", "digestive"),
    ("loss of appetite nausea weight loss fatigue", "digestive"),
    ("mouth ulcer difficulty swallowing throat pain", "digestive"),
    ("hiccups burping belching after meals", "digestive"),

    # neurological
    ("severe headache migraine nausea light sensitivity", "neurological"),
    ("dizziness vertigo balance problems nausea", "neurological"),
    ("numbness tingling hands feet", "neurological"),
    ("seizure convulsion loss of consciousness", "neurological"),
    ("memory loss confusion cognitive decline", "neurological"),
    ("tremor shaking hands Parkinson", "neurological"),
    ("stroke facial drooping arm weakness slurred speech", "neurological"),
    ("vision blurred double vision headache", "neurological"),
    ("neck stiffness fever headache light sensitivity meningitis", "neurological"),
    ("insomnia sleep disturbance difficulty sleeping", "neurological"),
    ("anxiety panic attack racing heart", "neurological"),
    ("depression mood low energy loss of interest", "neurological"),
    ("cluster headache one side eye pain", "neurological"),
    ("fainting syncope loss of consciousness brief", "neurological"),
    ("tinnitus ringing ears dizziness", "neurological"),

    # dermatological
    ("skin rash itching redness", "dermatological"),
    ("hives urticaria allergic reaction swelling", "dermatological"),
    ("eczema dry skin patches itchy", "dermatological"),
    ("psoriasis scaly skin plaques", "dermatological"),
    ("acne pimples oily skin", "dermatological"),
    ("blisters fluid filled skin vesicles", "dermatological"),
    ("wound infection redness warmth pus", "dermatological"),
    ("sunburn red hot painful skin", "dermatological"),
    ("jaundice yellow skin eyes dark urine", "dermatological"),
    ("hair loss baldness scalp itching", "dermatological"),
    ("nail fungus thick yellow nails", "dermatological"),
    ("athlete foot itching peeling feet", "dermatological"),
    ("contact dermatitis rash after touching plant chemical", "dermatological"),
    ("melanoma dark irregular mole skin change", "dermatological"),
    ("skin peeling flaking dry patches winter", "dermatological"),

    # musculoskeletal
    ("joint pain swelling stiffness arthritis", "musculoskeletal"),
    ("back pain lower lumbar stiffness", "musculoskeletal"),
    ("muscle ache body ache soreness fatigue", "musculoskeletal"),
    ("knee pain swelling difficulty walking", "musculoskeletal"),
    ("shoulder pain limited movement rotator cuff", "musculoskeletal"),
    ("neck pain stiffness after sleeping", "musculoskeletal"),
    ("fracture bone pain swelling after injury", "musculoskeletal"),
    ("sprain ankle twisted swelling bruising", "musculoskeletal"),
    ("gout big toe pain swelling sudden", "musculoskeletal"),
    ("fibromyalgia widespread muscle pain fatigue tender points", "musculoskeletal"),
    ("carpal tunnel wrist pain tingling hand weakness", "musculoskeletal"),
    ("hip pain groin difficulty walking elderly", "musculoskeletal"),
    ("sciatica shooting leg pain lower back", "musculoskeletal"),
    ("tendinitis heel pain Achilles", "musculoskeletal"),
    ("osteoporosis bone pain fracture spine compression", "musculoskeletal"),

    # general
    ("fever chills fatigue weakness general malaise", "general"),
    ("weight loss unexplained appetite loss fatigue", "general"),
    ("night sweats fever weight loss fatigue", "general"),
    ("swollen lymph nodes neck armpit groin", "general"),
    ("dehydration thirst dry mouth dark urine", "general"),
    ("anemia pale skin fatigue weakness breathlessness", "general"),
    ("diabetes frequent urination thirst blurred vision", "general"),
    ("thyroid fatigue weight gain cold intolerance", "general"),
    ("high blood pressure headache dizziness", "general"),
    ("chest pain palpitation racing heart", "general"),
    ("edema swollen legs ankles pitting", "general"),
    ("fever of unknown origin weeks fatigue", "general"),
    ("allergic reaction itching hives breathing difficulty", "general"),
    ("sepsis high fever confusion low blood pressure", "general"),
    ("vitamin deficiency fatigue weakness mouth sores", "general"),
]

CATEGORIES = ['respiratory', 'digestive', 'neurological', 'dermatological', 'musculoskeletal', 'general']


def train_tfidf_classifier(save: bool = True):
    """
    Train TF-IDF + Logistic Regression classifier on TRAINING_DATA.
    Returns: (pipeline, label_encoder)
    """
    from sklearn.pipeline import Pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import LabelEncoder

    texts = [t for t, _ in TRAINING_DATA]
    labels = [l for _, l in TRAINING_DATA]

    le = LabelEncoder()
    y = le.fit_transform(labels)

    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            sublinear_tf=True,
            stop_words='english',
        )),
        ('clf', LogisticRegression(
            C=1.0,
            max_iter=1000,
            solver='lbfgs',
            multi_class='multinomial',
        )),
    ])

    pipeline.fit(texts, y)
    logger.info('TF-IDF classifier trained on %d samples', len(texts))

    if save:
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(MODEL_PATH, 'wb') as f:
            pickle.dump({'pipeline': pipeline, 'label_encoder': le}, f)
        logger.info('Classifier saved to %s', MODEL_PATH)

    return pipeline, le


def load_tfidf_classifier():
    """Load saved classifier or train a fresh one if not found."""
    if MODEL_PATH.exists():
        with open(MODEL_PATH, 'rb') as f:
            data = pickle.load(f)
        logger.info('Classifier loaded from %s', MODEL_PATH)
        return data['pipeline'], data['label_encoder']
    else:
        logger.info('No saved classifier found — training now')
        return train_tfidf_classifier(save=True)


# Module-level cache
_pipeline = None
_label_encoder = None


def get_classifier():
    """Return cached classifier (load/train once per process)."""
    global _pipeline, _label_encoder
    if _pipeline is None:
        _pipeline, _label_encoder = load_tfidf_classifier()
    return _pipeline, _label_encoder


def classify_symptoms(text: str) -> dict:
    """
    Classify symptom text into a health category.

    Returns:
        {
            'category': str,
            'confidence': float,
            'all_probabilities': {category: prob, ...},
            'model': 'tfidf_logreg'
        }
    """
    pipeline, le = get_classifier()

    if not text or not text.strip():
        classes = list(le.classes_)
        equal_prob = round(1.0 / len(classes), 4) if classes else 0.1667
        return {
            'category': 'general',
            'confidence': 0.5,
            'all_probabilities': {c: equal_prob for c in classes},
            'model': 'tfidf_logreg_default',
        }

    proba = pipeline.predict_proba([text])[0]
    pred_idx = int(np.argmax(proba))
    category = le.inverse_transform([pred_idx])[0]
    confidence = float(proba[pred_idx])

    all_probs = {
        le.inverse_transform([i])[0]: float(p)
        for i, p in enumerate(proba)
    }

    return {
        'category': category,
        'confidence': round(confidence, 4),
        'all_probabilities': all_probs,
        'model': 'tfidf_logreg',
    }
