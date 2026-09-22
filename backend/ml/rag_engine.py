"""
Medical RAG Engine
==================
Builds and queries a FAISS vector index over medical documents.

Pipeline:
  Documents → text extraction → cleaning → chunking
           → sentence-transformers embeddings → FAISS index
           → similarity search → top-K passages
"""
import os
import json
import logging
import pickle
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
CHUNK_SIZE = 400       # characters (approx 100-120 tokens)
CHUNK_OVERLAP = 80     # character overlap between chunks
TOP_K = 4
MIN_RESULT_SCORE = 0.25
MIN_SCORE_NO_CONCEPT = 0.40   # Higher bar for passages with no literal concept match


def _clean_text(text: str) -> str:
    return re.sub(r'\s+', ' ', str(text or '')).strip()


def _clean_source_text(text: str, title: str = '') -> str:
    """Remove document-header artifacts without changing source wording."""
    cleaned = _clean_text(text)
    for prefix in (title, 'Source: General Health Reference (Educational Use)'):
        if prefix:
            cleaned = re.sub(rf'^(?:{re.escape(prefix)}\s*:?\s*)+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^[A-Z ]*INFORMATION\s+Source:\s*.*?\)\s*', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'(?:\s*Source:\s*){2,}', ' ', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _sentence_excerpt(text: str) -> str:
    """Trim a chunk cleanly to complete sentences/bullets without fragment noise."""
    if not text:
        return ''
    cleaned = text.strip()
    first_token = cleaned.split()[0] if cleaned.split() else ''
    if first_token and (not first_token[0].isupper() and not first_token.startswith(('-', '•', '*', '('))):
        m = re.search(r'(?:[.!?]\s+|\n\s*[-•*]\s+|\n\n+)([A-Z0-9\-•*])', cleaned)
        if m:
            cleaned = cleaned[m.start(1):].lstrip()
    lines = [line.strip() for line in cleaned.split('\n') if line.strip()]
    if lines:
        last_line = lines[-1]
        if not re.search(r'[.!?:]$', last_line):
            if re.search(r'\b(?:and|or|such as|the|a|an|of|in|to|with|by|at|for)\s*$', last_line, re.IGNORECASE):
                lines = lines[:-1]
    if lines:
        cleaned = ' '.join(lines)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def _query_concepts(query: str) -> list[str]:
    stop_words = {
        'what', 'which', 'does', 'this', 'that', 'with', 'from', 'about',
        'information', 'available', 'causes', 'symptoms', 'general', 'and',
        'the', 'for', 'are', 'is', 'how', 'of', 'to', 'in', 'at', 'home',
        'should', 'can', 'common', 'affect', 'relief', 'eat', 'drink', 'pain',
        # Conversational / pronoun / filler
        'have', 'has', 'had', 'having', 'feel', 'feels', 'felt', 'feeling',
        'been', 'was', 'were', 'will', 'would', 'could', 'also', 'just',
        'like', 'any', 'some', 'got', 'get', 'getting', 'take', 'taking', 'taken',
        'help', 'please', 'tell', 'know', 'see', 'experience', 'experiencing',
        # Severity / modifiers
        'severe', 'mild', 'moderate', 'slight', 'intense', 'bad', 'terrible', 'awful',
        'little', 'lot', 'very', 'extreme', 'unbearable',
        # Negation
        'not', 'no', 'dont', 'doesnt', 'didnt', 'without', 'denies', 'denied',
        'negative', 'neither', 'nor', 'but',
    }
    return list(dict.fromkeys(
        token for token in re.findall(r'[a-z0-9]+', query.lower())
        if len(token) > 2 and token not in stop_words
    ))


def _concept_stems(concepts: list[str]) -> set[str]:
    return {
        concept[:-3] if concept.endswith('ies') else
        concept[:-2] if concept.endswith(('ed', 'es')) else
        concept[:-1] if concept.endswith('s') else concept
        for concept in concepts
    }


def _has_relevant_concepts(query_concepts: list[str], text: str) -> bool:
    passage_stems = _concept_stems(_query_concepts(text))
    return bool(_concept_stems(query_concepts) & passage_stems)


def _is_near_duplicate(left: str, right: str) -> bool:
    ratio = SequenceMatcher(None, left.lower(), right.lower()).ratio()
    if ratio >= 0.75:
        return True
    t1 = set(left.lower().split())
    t2 = set(right.lower().split())
    if t1 and t2:
        jaccard = len(t1 & t2) / len(t1 | t2)
        if jaccard >= 0.65:
            return True
    return False


class RAGEngine:
    """FAISS-backed retrieval engine for medical documents."""

    def __init__(self, index_path: str):
        self.index_path = Path(index_path)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_file = self.index_path.with_suffix('.faiss')
        self.meta_file = self.index_path.with_suffix('.pkl')

        self._embedder = None
        self._index = None
        self._chunks_meta: list[dict] = []

    def _get_embedder(self):
        """Lazy-load sentence-transformers model."""
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
                logger.info('Embedder loaded: %s', EMBEDDING_MODEL_NAME)
            except ImportError:
                raise RuntimeError('sentence-transformers not installed')
        return self._embedder

    def _embed(self, texts: list[str]) -> np.ndarray:
        """Embed a list of texts; returns (N, D) float32 array."""
        embedder = self._get_embedder()
        embeddings = embedder.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return embeddings.astype(np.float32)

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------
    @staticmethod
    def chunk_text(text: str, source_meta: dict) -> list[dict]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        text = text.strip()
        while start < len(text):
            end = start + CHUNK_SIZE
            chunk_text = text[start:end].strip()
            if len(chunk_text) > 20:
                chunks.append({
                    'text': chunk_text,
                    'start': start,
                    'end': end,
                    **source_meta,
                })
            start += CHUNK_SIZE - CHUNK_OVERLAP
        return chunks

    def build_index(self, documents: list[dict]):
        """
        Build FAISS index from a list of documents.

        Each document: {'text': str, 'title': str, 'source_file': str, ...}
        """
        try:
            import faiss
        except ImportError:
            raise RuntimeError('faiss-cpu not installed')

        all_chunks = []
        for doc in documents:
            meta = {k: v for k, v in doc.items() if k != 'text'}
            chunks = self.chunk_text(doc['text'], meta)
            all_chunks.extend(chunks)

        if not all_chunks:
            logger.warning('No chunks to index')
            return

        logger.info('Indexing %d chunks from %d documents', len(all_chunks), len(documents))

        texts = [c['text'] for c in all_chunks]
        embeddings = self._embed(texts)

        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)  # Inner product (cosine with normalized vecs)
        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)
        index.add(embeddings)

        # Save
        faiss.write_index(index, str(self.index_file))
        with open(self.meta_file, 'wb') as f:
            pickle.dump(all_chunks, f)

        self._index = index
        self._chunks_meta = all_chunks
        logger.info('FAISS index saved: %s (%d vectors, dim=%d)', self.index_file, len(all_chunks), dim)

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------
    def load_index(self):
        """Load FAISS index and metadata from disk."""
        if not self.index_file.exists():
            raise FileNotFoundError(
                f'FAISS index not found at {self.index_file}. '
                'Run: python manage.py ingest_documents'
            )
        try:
            import faiss
        except ImportError:
            raise RuntimeError('faiss-cpu not installed')

        self._index = faiss.read_index(str(self.index_file))
        with open(self.meta_file, 'rb') as f:
            self._chunks_meta = pickle.load(f)
        logger.info('FAISS index loaded: %d vectors', self._index.ntotal)

    def _ensure_loaded(self):
        if self._index is None:
            self.load_index()

    def query(self, query_text: str, top_k: int = TOP_K) -> list[dict]:
        """
        Retrieve top-K most relevant passages for a query.

        High-quality retrieval features:
        - Uses clean positive query text for embedding if negation is detected
          (prevents negated entities like "no chest pain" from retrieving chest pain documents).
        - Separates positive and negated concepts; eliminates passages matching only negated entities.
        - Re-ranks candidates by combined score (FAISS cosine similarity + concept overlap density).
        - Multi-layer deduplication (SequenceMatcher + token Jaccard similarity).
        - Diversity constraint: max 2 passages per source file.
        - Enforces similarity score >= 0.25 (and >= 0.40 for passages without explicit concept hits).

        Returns list of dicts with keys:
          text, full_text, title, source_file, similarity_score,
          matched_concepts, why_matched, chunk_index
        """
        self._ensure_loaded()

        import faiss

        # Detect clinical negation in query to isolate positive intent
        neg_spans = []
        pos_text = query_text
        try:
            from ml.ner_pipeline import detect_negation_spans
            neg_spans, pos_text = detect_negation_spans(query_text)
        except Exception as exc:
            logger.debug('Negation detection fallback: %s', exc)

        has_negation = bool(neg_spans) and len(pos_text.strip()) >= 3
        embed_query = pos_text.strip() if has_negation else query_text

        # Positive concepts
        pos_concepts = _query_concepts(embed_query)
        n_concepts = max(len(pos_concepts), 1)

        # Negated concepts (must not be treated as positive targets)
        neg_concepts = []
        if has_negation:
            for start, end in neg_spans:
                neg_concepts.extend(_query_concepts(query_text[start:end]))
            neg_concepts = [c for c in dict.fromkeys(neg_concepts) if c not in pos_concepts]

        query_emb = self._embed([embed_query])
        faiss.normalize_L2(query_emb)

        # Fetch generous candidate pool (8× top_k) for re-ranking
        candidate_k = min(max(top_k * 8, 30), self._index.ntotal)
        scores, indices = self._index.search(query_emb, candidate_k)

        # ── Phase 1: collect & score all viable candidates ──────────────────
        candidates = []
        seen_excerpts: list[str] = []

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            raw_score = float(score)
            if raw_score < MIN_RESULT_SCORE:
                continue

            chunk = self._chunks_meta[idx]
            title = chunk.get('title', 'Unknown')
            full_text = _clean_source_text(chunk.get('text', ''), title)
            excerpt = _sentence_excerpt(full_text)
            if not excerpt:
                continue

            excerpt_lower = excerpt.lower()
            matched_pos = [
                c for c in pos_concepts
                if re.search(rf'\b{re.escape(c)}\b', excerpt_lower)
            ]
            matched_neg = [
                c for c in neg_concepts
                if re.search(rf'\b{re.escape(c)}\b', excerpt_lower)
            ]

            # If user explicitly denied symptoms, exclude passages matching only negated concepts
            if neg_concepts and matched_neg and not matched_pos:
                continue

            # Passages matching 0 positive concepts must clear a higher similarity threshold
            if pos_concepts and not matched_pos and raw_score < MIN_SCORE_NO_CONCEPT:
                continue

            # Skip near-duplicates
            if any(_is_near_duplicate(excerpt, seen) for seen in seen_excerpts):
                continue
            seen_excerpts.append(excerpt)

            concept_density = len(matched_pos) / n_concepts
            combined = 0.60 * raw_score + 0.40 * concept_density
            if matched_neg:
                combined -= 0.15 * (len(matched_neg) / max(len(neg_concepts), 1))

            candidates.append({
                'text': excerpt,
                'full_text': full_text,
                'title': title,
                'source_file': chunk.get('source_file', ''),
                'similarity_score': round(raw_score, 4),
                'matched_concepts': matched_pos,
                'why_matched': (
                    f"Matches query concepts: {', '.join(matched_pos)}"
                    if matched_pos else 'Semantically similar to the query'
                ),
                'chunk_index': int(idx),
                '_combined': combined,
            })

        # ── Phase 2: re-rank by combined score ──────────────────────────────
        candidates.sort(key=lambda c: c['_combined'], reverse=True)

        # ── Phase 3: select top_k with per-source cap of 2 ──────────────────
        results = []
        source_counts: dict[str, int] = {}
        for cand in candidates:
            source_key = cand['source_file'] or cand['title']
            if source_counts.get(source_key, 0) >= 2:
                continue
            # Clean up internal key before returning
            cand.pop('_combined', None)
            results.append(cand)
            source_counts[source_key] = source_counts.get(source_key, 0) + 1
            if len(results) >= top_k:
                break

        return results


# Module-level singleton
_rag_engine: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    """Return cached RAG engine (load once per process)."""
    global _rag_engine
    if _rag_engine is None:
        from django.conf import settings
        index_path = str(Path(settings.BASE_DIR) / settings.FAISS_INDEX_PATH)
        _rag_engine = RAGEngine(index_path)
    return _rag_engine
