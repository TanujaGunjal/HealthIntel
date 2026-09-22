"""
Management command: ingest_documents
=====================================
Reads all .txt files from backend/data/medical_documents/,
chunks them, embeds with sentence-transformers, and stores in FAISS.

Usage:
    python manage.py ingest_documents
    python manage.py ingest_documents --docs-path /custom/path
"""
import os
import logging
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Ingest medical documents into FAISS vector store.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--docs-path',
            type=str,
            default=None,
            help='Path to medical documents directory (default: backend/data/medical_documents)',
        )
        parser.add_argument(
            '--chunk-size',
            type=int,
            default=400,
            help='Character chunk size (default: 400)',
        )

    def handle(self, *args, **options):
        docs_path = options['docs_path'] or str(settings.MEDICAL_DOCS_PATH)
        docs_dir = Path(docs_path)

        if not docs_dir.exists():
            self.stderr.write(self.style.ERROR(f'Documents directory not found: {docs_dir}'))
            return

        # Find all text files
        txt_files = list(docs_dir.glob('**/*.txt'))
        if not txt_files:
            self.stderr.write(self.style.WARNING('No .txt files found in documents directory'))
            return

        self.stdout.write(f'Found {len(txt_files)} document(s). Processing...')

        documents = []
        for fpath in txt_files:
            try:
                text = fpath.read_text(encoding='utf-8')
                if len(text.strip()) < 50:
                    self.stdout.write(self.style.WARNING(f'  Skipping (too short): {fpath.name}'))
                    continue
                documents.append({
                    'text': text,
                    'title': fpath.stem.replace('_', ' ').title(),
                    'source_file': fpath.name,
                })
                self.stdout.write(f'  [OK] Loaded: {fpath.name} ({len(text)} chars)')
            except Exception as e:
                self.stderr.write(f'  [ERROR] Error reading {fpath.name}: {e}')

        if not documents:
            self.stderr.write(self.style.ERROR('No documents loaded.'))
            return

        self.stdout.write(f'\nBuilding FAISS index from {len(documents)} documents...')

        try:
            from ml.rag_engine import RAGEngine
            index_path = str(Path(settings.BASE_DIR) / settings.FAISS_INDEX_PATH)
            engine = RAGEngine(index_path)
            engine.build_index(documents)
            self.stdout.write(self.style.SUCCESS(
                f'\n[OK] FAISS index built successfully at: {index_path}'
            ))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Failed to build index: {e}'))
            raise
