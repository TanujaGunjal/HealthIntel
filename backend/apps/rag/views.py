"""RAG query view."""
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
import hashlib
import time

logger = logging.getLogger(__name__)


def _synthesize_answer(query, passages):
    """Use the configured project LLM with a strict evidence-only prompt."""
    if not passages:
        return 'No sufficiently relevant evidence was found for this question.'

    evidence = '\n\n'.join(
        f"Source {index}: {passage.get('text', '').strip()}"
        for index, passage in enumerate(passages[:3], start=1)
    )
    prompt = f"""You are an educational medical knowledge assistant.
Answer the user's question using ONLY the source passages below.
Do not diagnose, prescribe, recommend medication doses, or add facts not present in the passages.
If the passages do not fully answer the question, say that the available evidence is limited.
Use 2-4 concise sentences and do not mention source numbers in the answer.

User question: {query}

Source passages:
{evidence}
"""
    try:
        from ml.agent_workflow import _get_llm
        llm = _get_llm()
        if llm is not None:
            response = llm.invoke(prompt)
            content = getattr(response, 'content', response)
            if isinstance(content, list):
                content = ' '.join(
                    item.get('text', '') if isinstance(item, dict) else str(item)
                    for item in content
                )
            if isinstance(content, str) and content.strip():
                return content.strip()
    except (ImportError, RuntimeError, ValueError, OSError) as exc:
        logger.warning('Evidence answer synthesis unavailable: %s', exc)
    except Exception as exc:
        # Provider-specific API errors must not make retrieval fail.
        logger.warning('Evidence answer synthesis provider error: %s', exc)

    # Deterministic fallback remains source-grounded and does not add claims.
    return (
        'The available evidence is limited. The most relevant source states: '
        f"{passages[0].get('text', '').strip()}"
    )


class RAGQueryView(APIView):
    """
    POST /api/rag/query/
    Query the medical knowledge base. Results are cached in Redis (1 hour TTL).
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        query = request.data.get('query', '').strip()
        try:
            top_k = min(max(int(request.data.get('top_k', 5)), 3), 10)
        except (TypeError, ValueError):
            top_k = 5

        if not query or len(query) < 3:
            return Response(
                {'error': 'Query must be at least 3 characters.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Cache key
        cache_key = 'rag:' + hashlib.md5(f'{query}:{top_k}'.encode()).hexdigest()
        cached = cache.get(cache_key)
        if cached:
            logger.info('RAG cache hit: %s', cache_key)
            if not cached.get('answer'):
                cached = {
                    **cached,
                    'answer': _synthesize_answer(query, cached.get('passages', [])),
                }
            return Response({**cached, 'cached': True})

        started = time.perf_counter()
        try:
            from ml.rag_engine import get_rag_engine
            engine = get_rag_engine()
            passages = engine.query(query, top_k=top_k)
        except FileNotFoundError:
            return Response(
                {
                    'error': 'Knowledge base not yet built.',
                    'hint': 'Run: python manage.py ingest_documents',
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except (MemoryError, OSError, RuntimeError, ValueError) as e:
            logger.error('RAG query error: %s', e)
            return Response(
                {'error': 'Evidence retrieval is currently unavailable. Please try again later.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as e:
            logger.error('RAG query error: %s', e)
            return Response(
                {'error': 'Evidence retrieval failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_data = {
            'query': query,
            'passages': passages,
            'total_found': len(passages),
            'answer': _synthesize_answer(query, passages),
            'retrieval_time_ms': round((time.perf_counter() - started) * 1000, 1),
            'status': 'AVAILABLE' if passages else 'NO_RELEVANT_EVIDENCE',
            'similarity_label': 'Semantic similarity',
            'cached': False,
        }

        cache.set(cache_key, response_data, timeout=3600)
        return Response(response_data, status=status.HTTP_200_OK)
