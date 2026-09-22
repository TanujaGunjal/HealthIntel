import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Clock, Brain, FileText, ChevronRight, AlertCircle, Loader } from 'lucide-react';
import { historyAPI } from '../services/api';

const CATEGORY_COLORS = {
  respiratory: 'badge-primary',
  digestive: 'badge-accent',
  neurological: 'badge-warning',
  dermatological: 'badge-primary',
  musculoskeletal: 'badge-accent',
  general: 'badge-warning',
};

const CATEGORY_EMOJIS = {
  respiratory: '🫁', digestive: '🫃', neurological: '🧠',
  dermatological: '🩹', musculoskeletal: '🦴', general: '🏥',
};

export default function History() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    historyAPI.get()
      .then(({ data }) => setData(data))
      .catch(() => setError('Failed to load history. Please try again.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-surface">
      <Loader className="w-8 h-8 text-primary-400 animate-spin" />
    </div>
  );

  const analyses = data?.symptom_analyses || [];
  const prescriptions = data?.prescriptions || [];
  const hasHistory = analyses.length > 0 || prescriptions.length > 0;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 animate-fade-in">
      <div className="mb-8">
        <h1 className="section-title flex items-center gap-2">
          <Clock className="w-7 h-7 text-primary-400" /> Health History
        </h1>
        <p className="section-subtitle">
          Your past symptom analyses and prescription scans are stored here for reference.
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-danger-500/10 border border-danger-500/30 rounded-xl p-4 text-danger-300 text-sm mb-6">
          <AlertCircle className="w-5 h-5 flex-shrink-0" /> {error}
        </div>
      )}

      {!hasHistory && !error && (
        <div className="card text-center py-16 text-slate-500">
          <Clock className="w-12 h-12 mx-auto mb-3 opacity-20" />
          <p className="text-lg font-medium mb-2">No history yet</p>
          <p className="text-sm mb-6">Your analyses and prescription scans will appear here once you start using HealthIntel.</p>
          <div className="flex gap-3 justify-center">
            <Link to="/symptoms" className="btn-primary py-2 px-4 text-sm">Analyze Symptoms</Link>
            <Link to="/prescription" className="btn-secondary py-2 px-4 text-sm">Read Prescription</Link>
          </div>
        </div>
      )}

      {analyses.length > 0 && (
        <div className="mb-8">
          <h2 className="text-lg font-bold text-slate-100 mb-4 flex items-center gap-2">
            <Brain className="w-5 h-5 text-primary-400" />
            Symptom Analyses ({analyses.length})
          </h2>
          <div className="space-y-3">
            {analyses.map((item) => {
              const emoji = CATEGORY_EMOJIS[item.category] || '🏥';
              const colorClass = CATEGORY_COLORS[item.category] || 'badge-warning';
              return (
                <Link
                  key={item.id}
                  to={`/report/${item.id}`}
                  className="card flex items-center gap-4 hover:border-primary-500/40 transition-all group"
                >
                  <div className="text-3xl">{emoji}</div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-300 truncate">{item.raw_input}</p>
                    <div className="flex items-center gap-3 mt-1">
                      <span className={`badge ${colorClass} capitalize`}>{item.category}</span>
                      <span className="text-xs text-slate-400">
                        {Math.round((item.category_confidence || 0) * 100)}% confidence
                      </span>
                      <span className="text-xs text-slate-400">
                        {new Date(item.created_at).toLocaleString()}
                      </span>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-400 group-hover:text-primary-400 transition-colors flex-shrink-0" />
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {prescriptions.length > 0 && (
        <div>
          <h2 className="text-lg font-bold text-slate-100 mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-accent-400" />
            Prescription Scans ({prescriptions.length})
          </h2>
          <div className="space-y-3">
            {prescriptions.map((item) => (
              <div key={item.id} className="card flex items-center gap-4">
                <div className="w-10 h-10 bg-accent-500/20 rounded-xl flex items-center justify-center flex-shrink-0">
                  <FileText className="w-5 h-5 text-accent-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-300">
                    Prescription Scan
                    {item.medicine_count > 0 && (
                      <span className="ml-2 text-accent-400">— {item.medicine_count} medicine{item.medicine_count !== 1 ? 's' : ''} extracted</span>
                    )}
                  </p>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-slate-400">Engine: {item.ocr_engine || 'N/A'}</span>
                    {item.ocr_confidence && (
                      <span className="text-xs text-slate-400">
                        Confidence: {Math.round(item.ocr_confidence * 100)}%
                      </span>
                    )}
                    <span className="text-xs text-slate-400">{new Date(item.created_at).toLocaleString()}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
