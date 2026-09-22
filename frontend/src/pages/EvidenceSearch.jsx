import { useState } from 'react';
import { Search, Loader, BookOpen, AlertCircle, Zap, X, Send, Bot, User } from 'lucide-react';
import { ragAPI } from '../services/api';
import SourceCard from '../components/SourceCard';
import toast from 'react-hot-toast';

const EXAMPLE_QUERIES = [
  'What causes stomach pain and nausea?',
  'What information is available about fever and sore throat?',
  'How does asthma affect breathing?',
  'What are common symptoms of migraine?',
];

function buildGroundedAnswer(passages, query) {
  if (!passages?.length) {
    return `I could not find sufficiently relevant information for “${query}” in the medical knowledge base.`;
  }
  return `The retrieved evidence is available below for review of “${query}”.`;
}

export default function EvidenceSearch() {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  const [lastResults, setLastResults] = useState(null);
  const [error, setError] = useState('');

  const handleSearch = async (submittedQuery = query) => {
    const trimmedQuery = submittedQuery.trim();
    if (!trimmedQuery || trimmedQuery.length < 3) {
      toast.error('Please enter at least 3 characters.');
      return;
    }

    setQuery(trimmedQuery);
    setLoading(true);
    setError('');
    try {
      const { data } = await ragAPI.query(trimmedQuery, topK);
      const passages = data.passages || [];
      setLastResults(data);
      setMessages(current => [
        ...current,
        { role: 'user', text: trimmedQuery },
        {
          role: 'assistant',
          text: data.answer || buildGroundedAnswer(passages, trimmedQuery),
          sources: passages.slice(0, 3),
          retrieval: data,
        },
      ]);
      if (data.cached) toast('Results from cache', { icon: '⚡' });
    } catch (err) {
      const msg = err.response?.data?.error || 'Search failed. Please try again.';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setLastResults(null);
    setQuery('');
    setError('');
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-6 lg:px-8 animate-fade-in">
      <div className="mb-8">
        <h1 className="section-title flex items-center gap-2">
          <Search className="h-7 w-7 text-violet-400" /> Evidence Search
        </h1>
        <p className="section-subtitle">
          Ask a question about the curated medical knowledge base. Answers are grounded in retrieved evidence.
        </p>
      </div>

      <div className="card mb-6">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-slate-200">Medical knowledge assistant</p>
            <p className="text-xs text-slate-500">FAISS + MiniLM semantic retrieval</p>
          </div>
          {messages.length > 0 && (
            <button type="button" onClick={clearChat} className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200">
              <X className="h-3.5 w-3.5" /> Clear chat
            </button>
          )}
        </div>

        <div className="mb-5 max-h-[28rem] space-y-4 overflow-y-auto pr-1">
          {messages.length === 0 && (
            <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/30 p-8 text-center text-sm text-slate-400">
              <Bot className="mx-auto mb-3 h-9 w-9 text-primary-400 opacity-70" />
              Ask a health-information question to retrieve relevant sources.
            </div>
          )}
          {messages.map((message, index) => (
            <div key={`${message.role}-${index}`} className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : ''}`}>
              {message.role === 'assistant' && <Bot className="mt-2 h-5 w-5 flex-shrink-0 text-primary-400" />}
              <div className={`max-w-[90%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                message.role === 'user'
                  ? 'rounded-br-sm bg-primary-600/30 text-primary-50'
                  : 'rounded-bl-sm border border-slate-700 bg-slate-800/70 text-slate-200'
              }`}>
                {message.role === 'user' && <User className="mr-2 inline h-4 w-4 text-primary-300" />}
                {message.text}
                {message.role === 'assistant' && message.sources?.length > 0 && (
                  <div className="mt-4 border-t border-slate-700 pt-3">
                    <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Sources</p>
                    <div className="space-y-2">
                      {message.sources.map((source, sourceIndex) => (
                        <div key={`${source.source_file || source.title}-${sourceIndex}`} className="rounded-lg bg-slate-900/50 p-2.5 text-xs">
                          <div className="flex items-center justify-between gap-2 text-slate-300">
                            <span className="flex min-w-0 items-center gap-1 truncate">
                              <BookOpen className="h-3.5 w-3.5 flex-shrink-0 text-primary-400" />
                              {source.title || source.source_file || 'Medical Reference'}
                            </span>
                            <span className="flex-shrink-0 text-primary-300">
                              Retrieval similarity: {Math.round((source.similarity_score || 0) * 100)}%
                            </span>
                          </div>
                          <p className="mt-1 text-slate-400">{source.text || source.snippet}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex items-center gap-3 text-sm text-slate-400">
              <Bot className="h-5 w-5 text-primary-400" />
              <div className="rounded-2xl rounded-bl-sm border border-slate-700 bg-slate-800/70 px-4 py-3">
                <Loader className="mr-2 inline h-4 w-4 animate-spin" /> Retrieving evidence…
              </div>
            </div>
          )}
        </div>

        <div className="flex gap-2">
          <div className="relative flex-1">
            <input
              type="text"
              className="input pr-10"
              placeholder="Ask a medical knowledge question…"
              value={query}
              onChange={event => setQuery(event.target.value)}
              onKeyDown={event => event.key === 'Enter' && handleSearch()}
              disabled={loading}
            />
            {query && !loading && (
              <button type="button" onClick={() => setQuery('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-200" aria-label="Clear question">
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
          <select className="input w-20" value={topK} onChange={event => setTopK(Number(event.target.value))} aria-label="Number of sources">
            {[3, 5, 10].map(value => <option key={value} value={value}>Top {value}</option>)}
          </select>
          <button onClick={() => handleSearch()} className="btn-primary flex items-center gap-2 whitespace-nowrap" disabled={loading}>
            {loading ? <Loader className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            Ask
          </button>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {EXAMPLE_QUERIES.map(example => (
            <button key={example} onClick={() => handleSearch(example)} disabled={loading} className="rounded-full border border-primary-500/20 px-3 py-1 text-xs text-primary-400 transition-all hover:border-primary-500/40 hover:text-primary-300">
              {example}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="mb-4 flex items-center gap-2 rounded-xl border border-danger-500/30 bg-danger-500/10 p-4 text-sm text-danger-300">
          <AlertCircle className="h-5 w-5 flex-shrink-0" /> {error}
        </div>
      )}

      {lastResults && (
        <div className="mb-6 flex items-center justify-between text-xs text-slate-500">
          <span>{lastResults.total_found || 0} retrieved source{lastResults.total_found === 1 ? '' : 's'}</span>
          <span className="flex items-center gap-3">
            {lastResults.retrieval_time_ms != null && <span>{lastResults.retrieval_time_ms} ms</span>}
            {lastResults.cached && <span className="flex items-center gap-1 text-primary-400"><Zap className="h-3 w-3" /> Cached</span>}
          </span>
        </div>
      )}

      <div className="disclaimer-box mt-6 text-xs">
        Educational health information only. This does not provide medical diagnosis or treatment.
      </div>
    </div>
  );
}
