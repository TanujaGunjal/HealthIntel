/**
 * Source card — displays a retrieved RAG evidence passage.
 */
import { useState } from 'react';
import { BookOpen, ExternalLink, ChevronDown, ChevronUp, Lightbulb } from 'lucide-react';

export default function SourceCard({ source, index }) {
  const [expanded, setExpanded] = useState(false);
  const score = source.similarity_score;
  const pct = score ? Math.round(score * 100) : null;

  return (
    <div className="card border-l-2 border-l-primary-500 animate-slide-up">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-primary-400 flex-shrink-0 mt-0.5" />
          <h4 className="text-sm font-semibold text-slate-200">{source.title || 'Medical Reference'}</h4>
        </div>
        {pct !== null && (
          <span className={`badge flex-shrink-0 ${pct >= 70 ? 'badge-accent' : 'badge-primary'}`}>
            Retrieval similarity: {pct}%
          </span>
        )}
      </div>

      <p className="text-sm text-slate-200 leading-relaxed">
        {source.text || source.snippet}
      </p>

      <div className="mt-3 rounded-lg border border-slate-700/60 bg-slate-900/30 p-3">
        <p className="flex items-center gap-1 text-xs font-medium text-slate-400">
          <Lightbulb className="h-3.5 w-3.5 text-amber-300" /> Why this matched
        </p>
        <p className="mt-1 text-xs text-slate-500">{source.why_matched || 'Semantically similar to the query'}</p>
      </div>

      {source.full_text && source.full_text !== source.text && (
        <button
          type="button"
          onClick={() => setExpanded(value => !value)}
          className="mt-3 flex items-center gap-1 text-xs text-primary-300 hover:text-primary-200"
        >
          {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          {expanded ? 'Hide full passage' : 'View full passage'}
        </button>
      )}
      {expanded && <p className="mt-2 text-xs leading-relaxed text-slate-400">{source.full_text}</p>}

      {source.source_file && (
        <p className="text-xs text-slate-400 mt-2 flex items-center gap-1">
          <ExternalLink className="w-3 h-3 text-slate-400" />
          {source.source_file}
        </p>
      )}
    </div>
  );
}
