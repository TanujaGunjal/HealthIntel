import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Brain, FileText, Search, Activity, ArrowRight, Clock,
  Calendar, UserCheck, AlertCircle, ChevronRight, CheckCircle2
} from 'lucide-react';
import { historyAPI, appointmentsAPI } from '../services/api';

const MAIN_TOOLS = [
  {
    to: '/symptoms',
    icon: Brain,
    title: 'Symptom Analyzer',
    desc: 'Describe symptoms in natural language. Get biomedical NER extraction, category classification, and an evidence-backed health report via LangGraph AI workflow.',
    cta: 'Analyze Symptoms',
    color: 'text-primary-400',
    bg: 'bg-primary-500/10',
    border: 'hover:border-primary-500/50',
  },
  {
    to: '/prescription',
    icon: FileText,
    title: 'Prescription Reader',
    desc: 'Upload a prescription image. EasyOCR (with Tesseract fallback) extracts medicine names, dosages, and frequencies with confidence scores.',
    cta: 'Read Prescription',
    color: 'text-accent-400',
    bg: 'bg-accent-500/10',
    border: 'hover:border-accent-500/50',
  },
  {
    to: '/evidence',
    icon: Search,
    title: 'Evidence Search',
    desc: 'Query curated medical knowledge directly using semantic search. FAISS retrieves top-ranked passages with similarity scores and citations.',
    cta: 'Search Evidence',
    color: 'text-violet-400',
    bg: 'bg-violet-500/10',
    border: 'hover:border-violet-500/50',
  },
];

export default function Dashboard() {
  const { user } = useAuth();
  const [recentAnalyses, setRecentAnalyses] = useState([]);
  const [upcomingAppointments, setUpcomingAppointments] = useState([]);
  const [loadingStats, setLoadingStats] = useState(true);

  useEffect(() => {
    Promise.allSettled([
      historyAPI.get(),
      appointmentsAPI.list()
    ]).then(([histRes, apptRes]) => {
      if (histRes.status === 'fulfilled' && histRes.value.data) {
        setRecentAnalyses((histRes.value.data.symptom_analyses || []).slice(0, 3));
      }
      if (apptRes.status === 'fulfilled' && Array.isArray(apptRes.value.data)) {
        setUpcomingAppointments(apptRes.value.data.filter(a => a.status === 'upcoming').slice(0, 2));
      }
    }).finally(() => {
      setLoadingStats(false);
    });
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 animate-fade-in">
      {/* Header */}
      <div className="mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 mb-1">
            Welcome back, <span className="text-primary-400">{user?.full_name || user?.username || user?.email}</span>
          </h1>
          <p className="text-slate-400 text-sm">Choose an intelligent healthcare tool or view your records below.</p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/appointments"
            className="btn-secondary text-sm py-2 px-3.5 flex items-center gap-2"
          >
            <Calendar className="w-4 h-4 text-primary-400" /> Appointments
          </Link>
          <Link
            to="/history"
            className="btn-secondary text-sm py-2 px-3.5 flex items-center gap-2"
          >
            <Clock className="w-4 h-4 text-accent-400" /> Health History
          </Link>
        </div>
      </div>

      {/* Profile Completion Prompt */}
      {user && !user.profile_complete && (
        <div className="mb-8 p-4 bg-primary-500/10 border border-primary-500/30 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary-500/20 flex items-center justify-center flex-shrink-0">
              <UserCheck className="w-5 h-5 text-primary-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-200">Complete your health profile</h3>
              <p className="text-xs text-slate-400">
                Adding your age, sex, allergies, and existing conditions helps us tailor educational insights.
              </p>
            </div>
          </div>
          <Link
            to="/profile"
            className="btn-primary text-xs py-2 px-4 whitespace-nowrap self-start sm:self-center"
          >
            Complete Profile
          </Link>
        </div>
      )}

      {/* Feature Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-10">
        {MAIN_TOOLS.map(({ to, icon: Icon, title, desc, cta, color, bg, border }) => (
          <div key={to} className={`card ${border} transition-all duration-200 group flex flex-col`}>
            <div className={`w-12 h-12 ${bg} rounded-xl flex items-center justify-center mb-5 group-hover:scale-110 transition-transform`}>
              <Icon className={`w-6 h-6 ${color}`} />
            </div>
            <h2 className="text-lg font-bold text-slate-100 mb-2">{title}</h2>
            <p className="text-slate-400 text-sm leading-relaxed flex-1">{desc}</p>
            <Link
              to={to}
              className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-primary-400 hover:text-primary-300 transition-colors group/link"
            >
              {cta}
              <ArrowRight className="w-4 h-4 group-hover/link:translate-x-1 transition-transform" />
            </Link>
          </div>
        ))}
      </div>

      {/* Quick Summary: Recent Activity & Upcoming Appointments */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
        {/* Recent Analyses */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Clock className="w-4 h-4 text-primary-400" /> Recent Health Inquiries
            </h2>
            <Link to="/history" className="text-xs text-primary-400 hover:underline">View all</Link>
          </div>
          {recentAnalyses.length > 0 ? (
            <div className="space-y-3">
              {recentAnalyses.map(item => (
                <Link
                  key={item.id}
                  to={`/report/${item.id}`}
                  className="block p-3 rounded-xl bg-surface border border-surface-border hover:border-primary-500/30 transition-colors group"
                >
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="badge badge-primary capitalize">{item.category}</span>
                    <span className="text-slate-400">{new Date(item.created_at).toLocaleDateString()}</span>
                  </div>
                  <p className="text-sm text-slate-200 line-clamp-1 group-hover:text-primary-300 transition-colors">
                    {item.raw_input}
                  </p>
                </Link>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400 py-4 text-center">
              No recent inquiries yet. Try the Symptom Analyzer above.
            </p>
          )}
        </div>

        {/* Upcoming Appointments */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Calendar className="w-4 h-4 text-accent-400" /> Upcoming Appointments
            </h2>
            <Link to="/appointments" className="text-xs text-accent-400 hover:underline">Manage</Link>
          </div>
          {upcomingAppointments.length > 0 ? (
            <div className="space-y-3">
              {upcomingAppointments.map(appt => (
                <div
                  key={appt.id}
                  className="p-3 rounded-xl bg-surface border border-surface-border flex items-center justify-between"
                >
                  <div>
                    <h4 className="text-sm font-semibold text-slate-200">{appt.provider_name}</h4>
                    <p className="text-xs text-slate-400">
                      {appt.appointment_date} at {appt.appointment_time} · {appt.provider_type}
                    </p>
                  </div>
                  <span className="badge badge-accent text-xs">Confirmed</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-4">
              <p className="text-xs text-slate-400 mb-2">No upcoming appointments.</p>
              <Link to="/appointments" className="text-xs text-primary-400 hover:underline">
                Book a consultation
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Pipeline summary */}
      <div className="card">
        <h2 className="text-lg font-bold text-slate-100 mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5 text-accent-400" />
          AI Pipeline Architecture
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { step: '1', label: 'Biomedical NER', desc: 'spaCy & regex symptom and entity extraction', icon: '🧬' },
            { step: '2', label: 'TF-IDF Classifier', desc: 'Logistic regression category classification (6 categories)', icon: '📊' },
            { step: '3', label: 'FAISS Vector RAG', desc: 'MiniLM embeddings + cosine semantic retrieval', icon: '🔍' },
            { step: '4', label: 'LangGraph Agents', desc: 'Analysis → Evidence → Safety → Final synthesis', icon: '🤖' },
          ].map(({ step, label, desc, icon }) => (
            <div key={step} className="bg-surface border border-surface-border rounded-xl p-4">
              <div className="text-2xl mb-2">{icon}</div>
              <div className="text-xs text-primary-400 font-medium mb-1">Step {step}</div>
              <div className="text-sm font-semibold text-slate-200 mb-1">{label}</div>
              <div className="text-xs text-slate-400 leading-relaxed">{desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Disclaimer */}
      <div className="disclaimer-box mt-6">
        <strong>Educational Tool:</strong> HealthIntel provides general health information for educational
        purposes only. It is not a substitute for professional medical advice, diagnosis, or treatment.
        Always consult a qualified healthcare provider.
      </div>
    </div>
  );
}
