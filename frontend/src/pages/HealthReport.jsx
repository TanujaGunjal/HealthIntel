import { useParams, Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { ArrowLeft, Brain, BookOpen, Shield, FileText, Printer, Activity, Clock3, AlertTriangle, Sparkles } from 'lucide-react';
import { symptomsAPI } from '../services/api';
import AgentWorkflow from '../components/AgentWorkflow';
import SourceCard from '../components/SourceCard';

export default function HealthReport() {
  const { id } = useParams();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    symptomsAPI.getDetail(id)
      .then(({ data }) => setReport(data))
      .catch(() => setError('Report not found or you do not have permission to view it.'))
      .finally(() => setLoading(false));
  }, [id]);


  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-10 h-10 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  if (!report) return (
    <div className="max-w-3xl mx-auto px-4 py-16 text-center">
      <p className="text-slate-400 mb-4">{error || 'Report not found.'}</p>
      <Link to="/symptoms" className="btn-primary">New Analysis</Link>
    </div>
  );

  const steps = report.workflow_run?.agent_steps?.steps || report.workflow_status?.steps || [];
  const isUrgent = report.workflow_status?.is_urgent || false;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 animate-fade-in">
      <div className="flex items-center gap-3 mb-8">
        <Link to="/history" className="text-slate-400 hover:text-slate-200 transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-100">Health Information Report</h1>
            <span className="badge badge-accent hidden sm:inline-flex">Educational</span>
          </div>
          <p className="text-slate-400 text-sm flex items-center gap-2">
            <Clock3 className="w-3.5 h-3.5" /> Analysis #{report.id} · {new Date(report.created_at).toLocaleString()}
          </p>
        </div>
        <button
          onClick={() => window.print()}
          className="btn-secondary py-2 px-4 text-sm flex items-center gap-2 print:hidden"
        >
          <Printer className="w-4 h-4" /> Print Report
        </button>
      </div>

      {isUrgent && (
        <div className="urgent-box mb-6 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span>This report contains symptoms that may require urgent medical attention. Please seek immediate care.</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          {/* Symptom Summary & Classification */}
          <div className="card">
            <div className="flex items-start justify-between gap-4 mb-4">
              <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <Brain className="w-4 h-4 text-primary-400" /> Symptom Summary
              </h2>
              <Activity className="w-5 h-5 text-primary-400" />
            </div>
            <div className="rounded-xl bg-surface p-4 border border-surface-border mb-4">
              <p className="text-sm text-slate-300 leading-6 italic">"{report.raw_input}"</p>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <span className="badge badge-accent capitalize">{report.category}</span>
              <span className="text-slate-400">Classification confidence:</span>
              <span className="font-semibold text-slate-200">{Math.round((report.category_confidence || 0) * 100)}%</span>
              <div className="h-2 min-w-32 flex-1 rounded-full bg-surface">
                <div
                  className="h-2 rounded-full bg-accent-500 transition-all"
                  style={{ width: `${Math.min(100, (report.category_confidence || 0) * 100)}%` }}
                />
              </div>
            </div>
          </div>

          {/* Extracted Information */}
          <div className="card">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
              <FileText className="w-4 h-4 text-primary-400" /> Extracted Information
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-xs text-slate-400 block mb-2 uppercase tracking-wider">Symptoms Detected</span>
                <div className="flex flex-wrap gap-2">
                  {report.extracted_symptoms?.map((s, i) => (
                    <span key={i} className="badge badge-primary">{s.name || s}</span>
                  ))}
                  {(!report.extracted_symptoms || report.extracted_symptoms.length === 0) && (
                    <span className="text-slate-400 italic text-xs">No specific symptoms extracted</span>
                  )}
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">Duration:</span>
                  <span className="text-slate-200 font-medium">
                    {report.duration_text || report.duration || 'Not specified'}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">Severity:</span>
                  <span className="text-slate-200 font-medium">
                    {report.severity_text || report.severity || 'Not specified'}
                  </span>
                </div>
                {report.body_area && (
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400">Body Area:</span>
                    <span className="text-slate-200 font-medium">{report.body_area}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Evidence-backed Health Information */}
          <div className="card">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-accent-400" /> Evidence-backed Health Information
            </h2>
            {report.llm_response ? (
              <div className="prose-medical text-sm whitespace-pre-wrap leading-relaxed text-slate-300">
                {report.llm_response}
              </div>
            ) : (
              <p className="text-slate-400 italic text-sm">No evidence-backed response available for this record.</p>
            )}
          </div>

          {/* Safety Validation */}
          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <Shield className="w-4 h-4 text-amber-400" /> Safety Validation
              </h2>
              <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                isUrgent
                  ? 'bg-danger-500/20 text-danger-300 border border-danger-500/30'
                  : report.safety_notes
                  ? 'bg-accent-500/20 text-accent-300 border border-accent-500/30'
                  : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
              }`}>
                {isUrgent ? 'Urgent Warning Signs' : report.safety_notes ? 'Verified' : 'Unavailable'}
              </span>
            </div>
            <div className={isUrgent ? 'urgent-box' : 'disclaimer-box'}>
              {report.safety_notes || 'Safety validation notes unavailable for this analysis.'}
            </div>
          </div>

          {/* Evidence Sources */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-violet-400" /> Evidence Sources ({report.sources?.length || 0})
              </h2>
            </div>
            {report.sources?.length > 0 ? (
              <div className="space-y-3">
                {report.sources.map((s, i) => (
                  <SourceCard key={i} source={s} index={i} />
                ))}
              </div>
            ) : (
              <div className="card text-center py-6 text-slate-400 text-sm italic">
                No medical evidence sources retrieved for this analysis.
              </div>
            )}
          </div>

          {/* Medical disclaimer */}
          <div className="disclaimer-box text-sm">
            <strong>Medical Disclaimer:</strong> This report is for educational and informational purposes only. It does not constitute
            medical advice or clinical diagnosis. Always consult a licensed healthcare professional for medical concerns.
          </div>
        </div>

        {/* Workflow sidebar */}
        <div className="lg:sticky lg:top-6 lg:self-start">
          <AgentWorkflow steps={steps} isRunning={false} result={report} />
        </div>
      </div>
    </div>
  );
}
