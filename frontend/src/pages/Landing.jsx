/**
 * Landing page — hero, features, CTA
 */
import { Link } from 'react-router-dom';
import { Activity, Brain, FileText, Search, Shield, Zap, ChevronRight } from 'lucide-react';

const FEATURES = [
  {
    icon: Brain,
    title: 'Biomedical NER',
    desc: 'Extracts symptoms, duration, severity, and body areas from natural language using biomedical NLP.',
    color: 'text-primary-400',
    bg: 'bg-primary-500/10',
  },
  {
    icon: Search,
    title: 'RAG Evidence Retrieval',
    desc: 'Queries a curated medical knowledge base using semantic search (FAISS + sentence embeddings).',
    color: 'text-accent-400',
    bg: 'bg-accent-500/10',
  },
  {
    icon: Zap,
    title: 'LangGraph Workflow',
    desc: 'A 4-agent AI pipeline: Symptom Analysis → Evidence → Safety → Final Response.',
    color: 'text-violet-400',
    bg: 'bg-violet-500/10',
  },
  {
    icon: FileText,
    title: 'Prescription OCR',
    desc: 'Upload a prescription image to extract medicine names, dosages, and frequencies via EasyOCR.',
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
  },
  {
    icon: Shield,
    title: 'Safety Validation',
    desc: 'Detects urgent warning signs and ensures all responses include appropriate safety language.',
    color: 'text-danger-400',
    bg: 'bg-danger-500/10',
  },
  {
    icon: Activity,
    title: 'Evidence-Grounded',
    desc: 'Every response cites the retrieved medical sources. No hallucinated claims.',
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/10',
  },
];

export default function Landing() {
  return (
    <div className="landing-page min-h-screen">
      {/* Hero */}
      <section className="landing-hero relative overflow-hidden py-24 px-4">
        {/* Decorative blobs */}
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-surface-card border border-surface-border rounded-full px-4 py-2 text-sm text-slate-400 mb-8">
            <span className="w-2 h-2 bg-accent-400 rounded-full animate-pulse-slow" />
            AI-Powered Health Information — Educational Use Only
          </div>

          <h1 className="text-5xl sm:text-6xl font-extrabold text-slate-100 leading-tight mb-6">
            Understand Your{' '}
            <span className="bg-clip-text text-transparent bg-accent-gradient">
              Symptoms
            </span>{' '}
            & Prescriptions
          </h1>

          <p className="text-xl text-slate-400 mb-10 max-w-2xl mx-auto leading-relaxed">
            HealthIntel extracts useful information from symptom descriptions and prescription images,
            providing evidence-grounded health-information summaries — not medical diagnoses.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/register" className="btn-primary text-base flex items-center gap-2">
              Get Started Free <ChevronRight className="w-5 h-5" />
            </Link>
            <Link to="/about" className="btn-secondary text-base">
              How It Works
            </Link>
          </div>

          <p className="mt-6 text-xs text-slate-600">
            This is an educational tool. Always consult a qualified healthcare professional.
          </p>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-4 max-w-7xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="text-3xl font-bold text-slate-100 mb-3">
            Full AI/ML Engineering Stack
          </h2>
          <p className="text-slate-400 max-w-xl mx-auto">
            Built with real biomedical NLP, vector search, LangGraph agents, and prescription OCR —
            not just a UI on top of ChatGPT.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map(({ icon: Icon, title, desc, color, bg }) => (
            <div key={title} className="card-hover group">
              <div className={`w-12 h-12 ${bg} rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                <Icon className={`w-6 h-6 ${color}`} />
              </div>
              <h3 className="text-lg font-semibold text-slate-100 mb-2">{title}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Disclaimer */}
      <section className="pb-16 px-4 max-w-3xl mx-auto">
        <div className="disclaimer-box text-center">
          <p className="font-semibold text-amber-300 mb-1">⚠️ Medical Disclaimer</p>
          <p>
            HealthIntel is an educational health-information tool only. It does not provide medical advice,
            diagnoses, or prescriptions. The information displayed is for general educational purposes.
            Always consult a qualified and licensed healthcare professional for medical assessment and treatment.
          </p>
        </div>
      </section>
    </div>
  );
}
