"""
Evaluation: RAG Retrieval
==========================
Evaluates FAISS retrieval using Precision@K and Recall@K
against a small set of manually defined relevant queries.

Run from backend/:
    python evaluation/evaluate_rag.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()


# Manual relevance judgments: query → set of expected source keywords
EVAL_QUERIES = [
    {
        'query': 'symptoms of common cold',
        'relevant_keywords': ['rhinovirus', 'runny nose', 'congestion', 'sneezing', 'sore throat'],
        'expected_source': 'respiratory_health',
    },
    {
        'query': 'fever and body ache flu',
        'relevant_keywords': ['influenza', 'fever', 'body aches', 'fatigue', 'headache'],
        'expected_source': 'respiratory_health',
    },
    {
        'query': 'acid reflux heartburn treatment',
        'relevant_keywords': ['GERD', 'reflux', 'oesophagus', 'heartburn', 'stomach acid'],
        'expected_source': 'digestive_health',
    },
    {
        'query': 'migraine headache symptoms',
        'relevant_keywords': ['migraine', 'throbbing', 'nausea', 'light sensitivity', 'one side'],
        'expected_source': 'neurological_health',
    },
    {
        'query': 'joint pain arthritis stiffness',
        'relevant_keywords': ['arthritis', 'joint', 'stiffness', 'swelling', 'inflammation'],
        'expected_source': 'musculoskeletal_health',
    },
    {
        'query': 'skin rash itching eczema',
        'relevant_keywords': ['eczema', 'itching', 'dry skin', 'rash', 'patches'],
        'expected_source': 'general_and_dermatological_health',
    },
    {
        'query': 'diabetes symptoms blood sugar',
        'relevant_keywords': ['diabetes', 'blood glucose', 'thirst', 'urination', 'fatigue'],
        'expected_source': 'general_and_dermatological_health',
    },
    {
        'query': 'asthma breathing difficulty wheezing',
        'relevant_keywords': ['asthma', 'wheezing', 'breathe', 'bronchial', 'inhaler'],
        'expected_source': 'respiratory_health',
    },
]


def precision_at_k(retrieved_texts, relevant_keywords, k):
    """Fraction of top-K retrieved chunks containing at least one relevant keyword."""
    top_k = retrieved_texts[:k]
    hits = sum(
        1 for text in top_k
        if any(kw.lower() in text.lower() for kw in relevant_keywords)
    )
    return hits / k if k > 0 else 0.0


def recall_at_k(retrieved_texts, relevant_keywords, k):
    """Fraction of relevant keywords found in top-K retrieved chunks."""
    top_k_text = ' '.join(retrieved_texts[:k]).lower()
    found = sum(1 for kw in relevant_keywords if kw.lower() in top_k_text)
    return found / len(relevant_keywords) if relevant_keywords else 0.0


def evaluate():
    try:
        from ml.rag_engine import get_rag_engine
        engine = get_rag_engine()
    except FileNotFoundError:
        print('ERROR: FAISS index not found. Run: python manage.py ingest_documents')
        return

    Ks = [1, 3, 5]
    all_p = {k: [] for k in Ks}
    all_r = {k: [] for k in Ks}

    print('\n' + '='*65)
    print('RAG RETRIEVAL EVALUATION')
    print('='*65)
    print(f"{'Query':<40} " + " ".join(f"P@{k}  R@{k}" for k in Ks))
    print('-'*65)

    for item in EVAL_QUERIES:
        results = engine.query(item['query'], top_k=max(Ks))
        texts = [r['text'] for r in results]

        row = f"{item['query'][:38]:<40}"
        for k in Ks:
            p = precision_at_k(texts, item['relevant_keywords'], k)
            r = recall_at_k(texts, item['relevant_keywords'], k)
            all_p[k].append(p)
            all_r[k].append(r)
            row += f" {p:.2f}  {r:.2f}"
        print(row)

    print('\n--- Average Scores ---')
    print(f"{'Metric':<15} " + " ".join(f"K={k:>2}" for k in Ks))
    print('-'*35)
    for label, scores in [('Precision@K', all_p), ('Recall@K', all_r)]:
        row = f"{label:<15}"
        for k in Ks:
            avg = sum(scores[k]) / len(scores[k])
            row += f"  {avg:.3f}"
        print(row)

    print('\nNote: relevance is keyword-based (heuristic). Results reflect retrieval quality.')


if __name__ == '__main__':
    evaluate()
