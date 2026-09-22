import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Brain, Loader, AlertCircle, Send, FileText } from 'lucide-react';
import { symptomsAPI } from '../services/api';
import AgentWorkflow from '../components/AgentWorkflow';
import SourceCard from '../components/SourceCard';
import toast from 'react-hot-toast';

const CATEGORIES = {
  respiratory: { label: 'Respiratory', color: 'badge-primary', emoji: '\uD83E\uDEB4' },
  digestive: { label: 'Digestive', color: 'badge-accent', emoji: '\uD83E\uDEB3' },
  neurological: { label: 'Neurological', color: 'badge-warning', emoji: '\uD83E\uDDE0' },
  dermatological: { label: 'Dermatological', color: 'badge-primary', emoji: '\uD83E\uDE79' },
  musculoskeletal: { label: 'Musculoskeletal', color: 'badge-accent', emoji: '\uD83E\uDDB4' },
  general: { label: 'General', color: 'badge-warning', emoji: '\uD83C\uDFE5' },
};

/**
 * Extract agent steps from the API response.
 * The backend stores steps in workflow_status.steps (primary) or workflow_run.agent_steps.steps.
 */
function extractAgentSteps(data) {
  const fromWorkflowStatus = data?.workflow_status?.steps;
  if (Array.isArray(fromWorkflowStatus) && fromWorkflowStatus.length > 0) return fromWorkflowStatus;

  const rawSteps = data?.workflow_run?.agent_steps;
  if (Array.isArray(rawSteps) && rawSteps.length > 0) return rawSteps;
  if (rawSteps && Array.isArray(rawSteps.steps) && rawSteps.steps.length > 0) return rawSteps.steps;

  return [];
}

export default function SymptomAnalyzer() {
  const [symptoms, setSymptoms] = useState('');
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState('workflow');
  const [result, setResult] = useState(null);
  const [agentSteps, setAgentSteps] = useState([]);
  const [runningStepIndex, setRunningStepIndex] = useState(0);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!symptoms.trim() || symptoms.length < 5) {
      toast.error('Please describe your symptoms in more detail.');
      return;
    }
    setLoading(true);
    setResult(null);
    setAgentSteps([]);
    setError('');
    setRunningStepIndex(0);

    // Live progression simulation while the backend pipeline is executing
    const timer = setInterval(() => {
      setRunningStepIndex((prev) => (prev < 3 ? prev + 1 : prev));
    }, 750);

    try {
      if (mode === 'workflow') {
        const { data } = await symptomsAPI.workflow(symptoms);
        const steps = extractAgentSteps(data);
        setResult(data);
        setAgentSteps(steps);
        toast.success('Analysis complete!');
      } else {
        const { data } = await symptomsAPI.analyze(symptoms);
        const steps = extractAgentSteps(data);
        setResult(data);
        setAgentSteps(steps);
        toast.success('Symptoms analyzed!');
      }
    } catch (err) {
      const msg =
        err.response?.data?.error ||
        err.response?.data?.symptoms?.[0] ||
        'Analysis failed. Please try again.';
      setError(msg);
      toast.error(msg);
    } finally {
      clearInterval(timer);
      setLoading(false);
    }
  };

  const cat = result ? (CATEGORIES[result.category] || CATEGORIES.general) : null;
  const isUrgent = result?.workflow_status?.is_urgent || false;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 animate-fade-in">
      <div className="mb-8">
        <h1 className="section-title flex items-center gap-2">
          <Brain className="w-7 h-7 text-primary-400" /> Symptom Analyzer
        </h1>
        <p className="section-subtitle">
          Describe your symptoms in natural language. Our AI pipeline extracts biomedical entities,
          classifies the health category, and retrieves evidence-backed information.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Input panel */}
        <div className="lg:col-span-2 space-y-4">
          {/* Mode toggle */}
          <div className="flex gap-2 bg-surface-card border border-surface-border rounded-xl p-1 w-fit">
            {[
              { key: 'workflow', label: '\uD83E\uDD16 Full AI Workflow' },
              { key: 'analyze', label: '\u26A1 Quick Analyze' },
            ].map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setMode(key)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  mode === key
                    ? 'bg-primary-600 text-white shadow-glow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="card space-y-4">
            <label className="label text-base font-semibold">Describe your symptoms</label>
            <textarea
              className="input resize-none h-36"
              placeholder="e.g. I have had a fever, severe headache, and sore throat for the past two days. I also feel very tired and have a runny nose..."
              value={symptoms}
              onChange={(e) => setSymptoms(e.target.value)}
              disabled={loading}
            />
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400">{symptoms.length} / 2000 characters</span>
              <button
                type="submit"
                className="btn-primary flex items-center gap-2"
                disabled={loading || symptoms.length < 5}
              >
                {loading ? (
                  <><Loader className="w-4 h-4 animate-spin" /> Analyzing...</>
                ) : (
                  <><Send className="w-4 h-4" /> Analyze Symptoms</>
                )}
              </button>
            </div>
          </form>

          {error && (
            <div className="flex items-center gap-2 bg-danger-500/10 border border-danger-500/30 rounded-xl p-4 text-danger-300 text-sm">
              <AlertCircle className="w-5 h-5 flex-shrink-0" /> {error}
            </div>
          )}

          {/* Results */}
          {result && (
            <div className="space-y-4 animate-slide-up">
              {/* Entity extraction */}
              <div className="card">
                <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-4">
                  Extracted Information
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <div className="text-xs text-slate-400 mb-2 uppercase tracking-wider">Symptoms Detected</div>
                    <div className="flex flex-wrap gap-2">
                      {(result.symptoms || result.extracted_symptoms?.map((s) => s.name) || []).map((s, i) => (
                        <span key={i} className="badge badge-primary">{s}</span>
                      ))}
                      {!(result.symptoms?.length || result.extracted_symptoms?.length) && (
                        <span className="text-slate-400 italic text-sm">No specific symptoms extracted</span>
                      )}
                    </div>
                  </div>
                  <div className="space-y-2">
                    {(result.duration || result.duration_text) && (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-slate-400">Duration:</span>
                        <span className="text-slate-200">{result.duration || result.duration_text}</span>
                      </div>
                    )}
                    {(result.severity || result.severity_text) && (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-slate-400">Severity:</span>
                        <span className="text-slate-200">{result.severity || result.severity_text}</span>
                      </div>
                    )}
                    {result.body_area && (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-slate-400">Body Area:</span>
                        <span className="text-slate-200">{result.body_area}</span>
                      </div>
                    )}
                    {result.nlp_source && (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="text-slate-400">NLP Engine:</span>
                        <span className="badge badge-accent">{result.nlp_source}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Classification */}
              <div className="card">
                <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-4">
                  Health Category Classification
                </h3>
                <div className="flex items-center gap-4">
                  <div className="text-4xl">{cat?.emoji}</div>
                  <div>
                    <div className="flex items-center gap-3 mb-1">
                      <span className={`badge ${cat?.color} text-sm`}>{cat?.label}</span>
                      <span className="text-slate-300 text-sm">
                        {Math.round((result.confidence || result.category_confidence || 0) * 100)}% confidence
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">
                      Model: {result.classifier_model || 'tfidf_logreg'} — for informational purposes only
                    </p>
                  </div>
                </div>

                {result.all_probabilities && (
                  <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {Object.entries(result.all_probabilities)
                      .sort(([, a], [, b]) => b - a)
                      .map(([c, prob]) => (
                        <div key={c} className="bg-surface rounded-lg p-2">
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-slate-400 capitalize">{c}</span>
                            <span className="text-slate-300">{Math.round(prob * 100)}%</span>
                          </div>
                          <div className="h-1.5 bg-surface-border rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary-500 rounded-full transition-all"
                              style={{ width: `${prob * 100}%` }}
                            />
                          </div>
                        </div>
                      ))}
                  </div>
                )}
              </div>

              {/* LLM / Rule-based health information */}
              {result.llm_response && (
                <div className="card">
                  <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">
                    Evidence-backed Health Information
                  </h3>
                  <div className="prose-medical whitespace-pre-wrap text-sm text-slate-300 leading-relaxed">
                    {result.llm_response}
                  </div>
                </div>
              )}

              {/* Safety notes */}
              {result.safety_notes && (
                <div className={isUrgent ? 'urgent-box' : 'disclaimer-box'}>
                  {result.safety_notes}
                </div>
              )}

              {/* Agent step execution summary */}
              {agentSteps.length > 0 && (
                <div className="card">
                  <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
                    Workflow Execution Summary
                  </h3>
                  <div className="space-y-2">
                    {agentSteps.map((step, i) => (
                      <div key={i} className="flex items-start gap-3 text-sm p-2 bg-surface rounded-lg">
                        <span className="text-accent-400 font-mono text-xs mt-0.5 w-5 text-center">{i + 1}</span>
                        <div className="flex-1">
                          <span className="text-slate-200 font-medium">{step.agent}</span>
                          {step.output_preview && (
                            <p className="text-slate-400 text-xs mt-0.5 line-clamp-2">{step.output_preview}</p>
                          )}
                          {step.passages_found !== undefined && (
                            <p className="text-slate-400 text-xs mt-0.5">
                              Retrieved {step.passages_found} evidence passage{step.passages_found !== 1 ? 's' : ''}
                            </p>
                          )}
                          {step.is_urgent !== undefined && (
                            <p className={`text-xs mt-0.5 ${step.is_urgent ? 'text-amber-400' : 'text-accent-400'}`}>
                              {step.is_urgent ? '\u26A0\uFE0F Urgent warning signs detected' : '\u2713 No urgent warning signs'}
                            </p>
                          )}
                          {step.response_length !== undefined && (
                            <p className="text-slate-400 text-xs mt-0.5">
                              Generated {step.response_length}-character response
                            </p>
                          )}
                        </div>
                        <span className={`text-xs shrink-0 px-2 py-0.5 rounded-full font-medium ${
                          step.status === 'error' || step.status === 'failed'
                            ? 'bg-danger-500/20 text-danger-400 border border-danger-500/30'
                            : step.status === 'unavailable'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                            : 'bg-accent-500/20 text-accent-400 border border-accent-500/30'
                        }`}>
                          {step.status === 'unavailable'
                            ? 'Unavailable'
                            : step.status === 'error' || step.status === 'failed'
                            ? 'Error'
                            : 'Completed'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Evidence sources */}
              {result.sources?.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
                    Evidence Sources ({result.sources.length})
                  </h3>
                  <div className="space-y-3">
                    {result.sources.map((s, i) => (
                      <SourceCard key={i} source={s} index={i} />
                    ))}
                  </div>
                </div>
              )}

              {/* View full report */}
              {result.id && (
                <Link
                  to={`/report/${result.id}`}
                  className="btn-secondary w-full flex items-center justify-center gap-2 text-sm"
                >
                  <FileText className="w-4 h-4" /> View Full Report
                </Link>
              )}
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          <AgentWorkflow
            steps={agentSteps}
            isRunning={loading}
            runningStepIndex={runningStepIndex}
            result={result}
          />
          <div className="disclaimer-box text-xs">
            <strong>Important:</strong> This tool provides educational health information only.
            It does not diagnose medical conditions. Please consult a healthcare professional.
          </div>
        </div>
      </div>
    </div>
  );
}
