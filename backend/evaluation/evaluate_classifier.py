"""
Evaluation: Symptom Classifier
================================
Evaluates TF-IDF + Logistic Regression classifier using cross-validation.
Reports accuracy, precision, recall, and F1-score per class.

Run from backend/:
    python evaluation/evaluate_classifier.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

import numpy as np
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder

from ml.classifier import TRAINING_DATA, CATEGORIES


def evaluate():
    texts = [t for t, _ in TRAINING_DATA]
    labels = [l for _, l in TRAINING_DATA]

    le = LabelEncoder()
    le.fit(labels)
    y = le.transform(labels)

    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=5000,
                                   sublinear_tf=True, stop_words='english')),
        ('clf', LogisticRegression(C=1.0, max_iter=1000, solver='lbfgs',
                                    multi_class='multinomial')),
    ])

    # 5-fold stratified cross-validation
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scoring = ['accuracy', 'f1_macro', 'precision_macro', 'recall_macro']
    cv_results = cross_validate(pipeline, texts, y, cv=cv, scoring=scoring)

    print('\n' + '='*60)
    print('SYMPTOM CLASSIFIER EVALUATION (5-Fold Cross-Validation)')
    print('='*60)
    print(f"Dataset size:       {len(texts)} samples")
    print(f"Number of classes:  {len(CATEGORIES)}")
    print(f"Classes:            {', '.join(CATEGORIES)}\n")

    metrics = {
        'Accuracy':           cv_results['test_accuracy'],
        'F1 (macro avg)':     cv_results['test_f1_macro'],
        'Precision (macro)':  cv_results['test_precision_macro'],
        'Recall (macro)':     cv_results['test_recall_macro'],
    }

    print(f"{'Metric':<25} {'Mean':>8} {'Std':>8}")
    print('-'*45)
    for name, vals in metrics.items():
        print(f"{name:<25} {np.mean(vals):>8.4f} {np.std(vals):>8.4f}")

    # Full training set report
    print('\n--- Full Training Set Report ---')
    pipeline.fit(texts, y)
    y_pred = pipeline.predict(texts)
    print(classification_report(y, y_pred, target_names=le.classes_))

    return {k: (float(np.mean(v)), float(np.std(v))) for k, v in metrics.items()}


if __name__ == '__main__':
    results = evaluate()
    print('\nEvaluation complete. See evaluation/results.md for the report table.')
