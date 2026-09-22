import {
  Activity,
  ArrowRight,
  Brain,
  CheckCircle2,
  FileText,
  Search,
  Shield,
  Sparkles,
  Stethoscope,
  Zap,
} from 'lucide-react';

const pipeline = [
  {
    step: '01',
    icon: Brain,
    accent: 'from-primary-500/20 to-primary-500/5 text-primary-300',
    title: 'Understand the input',
    name: 'Biomedical NER',
    desc: 'Extracts symptoms, duration, severity, and body area from free-text descriptions using scispaCy, with a spaCy and regex fallback.',
  },
  {
    step: '02',
    icon: Zap,
    accent: 'from-violet-500/20 to-violet-500/5 text-violet-300',
    title: 'Classify patterns',
    name: 'Symptom Classifier',
    desc: 'A TF-IDF and Logistic Regression model maps symptoms to six health categories and returns probability scores.',
  },
  {
    step: '03',
    icon: Search,
    accent: 'from-accent-500/20 to-accent-500/5 text-accent-300',
    title: 'Retrieve evidence',
    name: 'RAG Knowledge Retrieval',
    desc: 'Embeds medical documents, searches a FAISS index for relevant passages, and caches results in Redis for faster follow-ups.',
  },
  {
    step: '04',
    icon: Activity,
    accent: 'from-cyan-500/20 to-cyan-500/5 text-cyan-300',
    title: 'Apply safety checks',
    name: 'LangGraph Workflow',
    desc: 'Coordinates symptom analysis, evidence retrieval, safety review, and the final response through a four-node StateGraph.',
  },
  {
    step: '05',
    icon: FileText,
    accent: 'from-amber-500/20 to-amber-500/5 text-amber-300',
    title: 'Read prescriptions',
    name: 'Prescription OCR',
    desc: 'Uses EasyOCR with a Tesseract fallback to identify medicines, dosage, and frequency while flagging low-confidence fields.',
  },
];

const capabilities = [
  ['Accuracy', 'Evidence-grounded summaries instead of unsupported guesses.'],
  ['Clarity', 'Plain-language explanations for complex health information.'],
  ['Safety', 'Clear limits, warnings, and professional-care guidance.'],
  ['Accessibility', 'Text and prescription-image inputs in one workflow.'],
];

const stack = [
  ['Frontend', 'React · Vite · Tailwind'],
  ['Backend', 'Django · DRF · PostgreSQL'],
  ['ML / NLP', 'spaCy · scikit-learn · Transformers'],
  ['AI', 'Gemini / OpenAI · LangGraph'],
  ['Retrieval', 'FAISS · sentence-transformers · Redis'],
  ['Operations', 'EasyOCR · Tesseract · Celery · Docker'],
];

export default function About() {
  return (
    <main className="about-page relative overflow-hidden">
      <div className="pointer-events-none absolute -top-40 right-[-10rem] h-96 w-96 rounded-full bg-emerald-100/70 blur-3xl" />
      <div className="pointer-events-none absolute top-[28rem] left-[-14rem] h-96 w-96 rounded-full bg-sky-100/70 blur-3xl" />

      <div className="relative mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-14 lg:px-8">
        <section className="grid items-end gap-8 lg:grid-cols-[1.15fr_.85fr]">
          <div>
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
              <Sparkles className="h-3.5 w-3.5" />
              Built for safer understanding
            </div>
            <h1 className="max-w-3xl text-4xl font-extrabold tracking-tight text-slate-950 sm:text-5xl lg:text-6xl">
              Health information that is{' '}
              <span className="bg-gradient-to-r from-emerald-600 via-cyan-600 to-sky-600 bg-clip-text text-transparent">
                easier to understand.
              </span>
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-slate-600 sm:text-lg">
              HealthIntel turns symptom descriptions and prescription images into evidence-grounded,
              educational summaries — helping people ask better questions without pretending to replace a clinician.
            </p>
          </div>

          <div className="card relative overflow-hidden border-emerald-200 bg-gradient-to-br from-emerald-50 via-white to-sky-50">
            <div className="absolute right-0 top-0 h-28 w-28 translate-x-8 -translate-y-8 rounded-full border border-primary-400/20" />
            <div className="relative flex items-start gap-4">
              <div className="rounded-2xl bg-emerald-100 p-3 text-emerald-700">
                <Stethoscope className="h-6 w-6" />
              </div>
              <div>
                <p className="text-sm font-semibold text-emerald-700">Our promise</p>
                <p className="mt-2 text-lg font-semibold leading-7 text-slate-900">
                  Explain clearly. Cite evidence. Escalate when it matters.
                </p>
              </div>
            </div>
            <div className="relative mt-6 grid grid-cols-3 gap-3 border-t border-surface-border pt-4 text-center">
              <div><p className="text-xl font-bold text-slate-900">5</p><p className="mt-1 text-xs text-slate-500">AI stages</p></div>
              <div><p className="text-xl font-bold text-slate-900">6</p><p className="mt-1 text-xs text-slate-500">health areas</p></div>
              <div><p className="text-xl font-bold text-slate-900">24/7</p><p className="mt-1 text-xs text-slate-500">available</p></div>
            </div>
          </div>
        </section>

        <section className="mt-12 grid gap-5 lg:grid-cols-[.8fr_1.2fr]">
          <div className="card border-primary-500/20 bg-primary-500/[0.04]">
            <p className="mb-3 text-xs font-bold uppercase tracking-[0.2em] text-primary-300">The problem</p>
            <h2 className="text-2xl font-bold text-slate-100">Healthcare information is often difficult to act on.</h2>
            <p className="mt-4 text-sm leading-6 text-slate-400">
              Symptoms can be vague, prescriptions can be hard to read, and online searches can quickly become overwhelming.
              HealthIntel creates a calmer first step between a question and a qualified healthcare conversation.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {capabilities.map(([title, desc]) => (
              <div key={title} className="rounded-2xl border border-surface-border bg-surface-card/80 p-5">
                <CheckCircle2 className="h-5 w-5 text-accent-400" />
                <h3 className="mt-4 font-semibold text-slate-100">{title}</h3>
                <p className="mt-2 text-sm leading-5 text-slate-400">{desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-16">
          <div className="mb-7 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary-300">How it works</p>
              <h2 className="mt-2 text-3xl font-bold text-slate-100">From question to grounded answer</h2>
            </div>
            <p className="max-w-md text-sm leading-6 text-slate-500">Each stage adds context and safety before anything is shown to the user.</p>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            {pipeline.map(({ step, icon: Icon, accent, title, name, desc }, index) => (
              <div key={step} className="relative min-w-0">
                <div className="card h-full min-w-0 p-5 hover:border-primary-500/40">
                  <div className={`mb-5 flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br ${accent}`}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <span className="font-mono text-xs font-medium text-slate-500">STEP {step}</span>
                    {index < pipeline.length - 1 && <ArrowRight className="hidden h-4 w-4 text-slate-600 xl:block" />}
                  </div>
                  <p className="text-xs font-medium text-primary-300">{title}</p>
                  <h3 className="mt-1 break-words text-base font-bold text-slate-100">{name}</h3>
                  <p className="mt-3 break-words text-sm leading-6 text-slate-400">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-16 grid gap-6 lg:grid-cols-[1fr_1.1fr]">
          <div className="card">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary-300">Technology</p>
            <h2 className="mt-2 text-2xl font-bold text-slate-100">A real full-stack ML pipeline</h2>
            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              {stack.map(([label, value]) => (
                <div key={label} className="min-w-0 rounded-xl border border-surface-border bg-surface px-4 py-3">
                  <p className="text-xs font-semibold text-slate-500">{label}</p>
                  <p className="mt-1 break-words text-sm font-medium text-slate-200">{value}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="disclaimer-box flex flex-col justify-between">
            <div>
              <h2 className="flex items-center gap-2 text-lg font-bold text-amber-300">
                <Shield className="h-5 w-5" /> Medical disclaimer
              </h2>
              <p className="mt-4 text-sm leading-6">
                HealthIntel is an educational health-information tool, not a medical device. It does not diagnose,
                prescribe, or replace professional medical advice. AI-generated content may contain inaccuracies.
                Always consult a qualified healthcare provider about your condition or treatment.
              </p>
            </div>
            <p className="mt-6 border-t border-amber-500/20 pt-4 text-xs font-semibold uppercase tracking-wide text-amber-200/80">
              In an emergency, contact your local emergency number immediately.
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
