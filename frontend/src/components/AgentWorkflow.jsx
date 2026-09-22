/**
 * Agent workflow status tracker component.
 * Shows the 4 LangGraph agent steps with real-time status and detailed outputs.
 *
 * Props:
 *   steps: array of {agent, status, ...} objects from the backend
 *   isRunning: boolean — true while the API call is in progress
 *   runningStepIndex: number — 0-3 current active step index when isRunning is true
 *   result: object — optional full analysis result payload for supplementary details
 */
import { CheckCircle, Circle, Loader, AlertCircle, MinusCircle, ArrowDown } from 'lucide-react';

const STEPS = [
  {
    key: 'SymptomAnalysisAgent',
    label: 'Symptom Analysis',
    desc: 'Extracting symptoms & classifying health category',
  },
  {
    key: 'EvidenceRetrievalAgent',
    label: 'Evidence Retrieval',
    desc: 'Searching medical knowledge-base passages',
  },
  {
    key: 'SafetyAgent',
    label: 'Safety Validation',
    desc: 'Verifying red-flag & urgent warning signs',
  },
  {
    key: 'FinalResponseAgent',
    label: 'Response Generation',
    desc: 'Composing evidence-backed health summary',
  },
];

function StepIcon({ status }) {
  if (status === 'completed') {
    return <CheckCircle className="w-5 h-5 text-accent-400 flex-shrink-0" />;
  }
  if (status === 'running') {
    return <Loader className="w-5 h-5 text-primary-400 flex-shrink-0 animate-spin" />;
  }
  if (status === 'warning') {
    return <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0" />;
  }
  if (status === 'skipped') {
    return <MinusCircle className="w-5 h-5 text-slate-400 flex-shrink-0" />;
  }
  if (status === 'unavailable' || status === 'no_evidence') {
    return <MinusCircle className="w-5 h-5 text-amber-400 flex-shrink-0" />;
  }
  if (status === 'error' || status === 'failed') {
    return <AlertCircle className="w-5 h-5 text-danger-400 flex-shrink-0" />;
  }
  return <Circle className="w-5 h-5 text-slate-600 flex-shrink-0" />;
}

export default function AgentWorkflow({
  steps = [],
  isRunning = false,
  runningStepIndex = 0,
  result = null,
}) {
  // Map steps by agent key
  const stepMap = {};
  steps.forEach((s) => {
    const key = s.agent || s.key || s.name;
    if (key) stepMap[key] = s;
  });

  const completedCount = steps.filter((s) => s.status === 'completed').length;
  const warningCount = steps.filter((s) => s.status === 'warning').length;
  const skippedCount = steps.filter((s) => s.status === 'skipped').length;
  const unavailableCount = steps.filter((s) => s.status === 'unavailable' || s.status === 'no_evidence').length;

  return (
    <div className="card space-y-3">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
          AI Agent Workflow
        </h3>
        {steps.length > 0 && !isRunning && (
          <div className="flex items-center gap-1.5 text-xs flex-wrap">
            <span className="text-accent-400 font-medium">{completedCount}/{STEPS.length} Completed</span>
            {warningCount > 0 && (
              <span className="text-amber-400 font-medium">({warningCount} Warning)</span>
            )}
            {skippedCount > 0 && (
              <span className="text-slate-400 font-medium">({skippedCount} Skipped)</span>
            )}
            {unavailableCount > 0 && (
              <span className="text-amber-400/80 font-medium">({unavailableCount} Unavailable)</span>
            )}
          </div>
        )}
        {isRunning && (
          <span className="text-xs text-primary-400 animate-pulse font-medium flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-primary-400 animate-ping" />
            Executing pipeline...
          </span>
        )}
      </div>

      {STEPS.map((step, i) => {
        const backendStep = stepMap[step.key];

        // Determine step status
        let status = 'pending';
        if (isRunning) {
          if (i < runningStepIndex) {
            status = 'completed';
          } else if (i === runningStepIndex) {
            status = 'running';
          } else {
            status = 'pending';
          }
        } else if (backendStep) {
          status = backendStep.status || 'completed';
        }

        // Compute detailed output for each step
        let detailNode = null;

        if (status === 'completed' && !isRunning) {
          if (step.key === 'SymptomAnalysisAgent') {
            const rawSyms =
              backendStep?.symptoms ||
              result?.symptoms ||
              result?.extracted_symptoms?.map((s) => s.name || s) ||
              [];
            const cat = backendStep?.category || result?.category;
            const dur = backendStep?.duration || result?.duration || result?.duration_text;
            const sev = backendStep?.severity || result?.severity || result?.severity_text;

            detailNode = (
              <div className="mt-1.5 pt-1.5 border-t border-accent-500/20 text-xs space-y-1">
                {rawSyms.length > 0 ? (
                  <div className="flex flex-wrap gap-1 items-center">
                    <span className="text-slate-400">Extracted:</span>
                    {rawSyms.slice(0, 4).map((s, idx) => (
                      <span key={idx} className="px-1.5 py-0.5 rounded bg-accent-500/20 text-accent-300 font-mono text-[11px]">
                        {s}
                      </span>
                    ))}
                    {rawSyms.length > 4 && (
                      <span className="text-slate-400">+{rawSyms.length - 4} more</span>
                    )}
                  </div>
                ) : (
                  <p className="text-slate-300">Symptoms processed & analyzed</p>
                )}
                <div className="flex flex-wrap items-center gap-2 text-slate-300">
                  {cat && (
                    <span>Category: <strong className="text-accent-300 capitalize">{cat}</strong></span>
                  )}
                  {dur && <span>• Duration: <strong>{dur}</strong></span>}
                  {sev && <span>• Severity: <strong>{sev}</strong></span>}
                </div>
              </div>
            );
          } else if (step.key === 'EvidenceRetrievalAgent') {
            const count =
              backendStep?.passages_found ??
              (result?.sources?.length !== undefined ? result.sources.length : null);
            const topSources = backendStep?.top_sources || result?.sources?.slice(0, 2) || [];

            detailNode = (
              <div className="mt-1.5 pt-1.5 border-t border-accent-500/20 text-xs space-y-1">
                <p className="text-slate-300">
                  {count !== null && count > 0 ? (
                    <>Retrieved <strong className="text-accent-300">{count}</strong> medical evidence passage{count !== 1 ? 's' : ''}</>
                  ) : (
                    'Medical knowledge base searched'
                  )}
                </p>
                {topSources.length > 0 && (
                  <div className="space-y-0.5">
                    {topSources.map((s, idx) => (
                      <div key={idx} className="text-slate-400 truncate flex items-center justify-between gap-1">
                        <span className="truncate">• {s.title || s.source_file || 'Reference'}</span>
                        {s.similarity_score !== undefined && s.similarity_score !== null && (
                          <span className="text-accent-300 text-[10px] shrink-0">
                            {Math.round(s.similarity_score * 100)}% match
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          } else if (step.key === 'SafetyAgent') {
            const isUrgent =
              backendStep?.is_urgent ??
              result?.workflow_status?.is_urgent ??
              false;
            const safetyText =
              backendStep?.safety_result ||
              (isUrgent
                ? 'Urgent warning signs detected'
                : 'Safety verified: No urgent red flags detected');

            detailNode = (
              <div className="mt-1.5 pt-1.5 border-t border-accent-500/20 text-xs">
                <p className={`font-medium ${isUrgent ? 'text-amber-400' : 'text-accent-300'}`}>
                  {isUrgent ? '⚠️ ' : '✓ '}{safetyText}
                </p>
              </div>
            );
          } else if (step.key === 'FinalResponseAgent') {
            const len =
              backendStep?.response_length ??
              (result?.llm_response ? result.llm_response.length : null);

            detailNode = (
              <div className="mt-1.5 pt-1.5 border-t border-accent-500/20 text-xs">
                <p className="text-slate-300">
                  {len ? (
                    <>Generated <strong className="text-accent-300">{len}</strong>-character evidence-backed response</>
                  ) : (
                    'Educational summary compiled'
                  )}
                </p>
              </div>
            );
          }
        } else if ((status === 'unavailable' || status === 'no_evidence') && !isRunning) {
          const reason =
            backendStep?.message ||
            (step.key === 'EvidenceRetrievalAgent'
              ? 'No matching passages found or index offline'
              : step.key === 'SafetyAgent'
              ? 'Safety checks unavailable'
              : step.key === 'FinalResponseAgent'
              ? 'Response generation unavailable'
              : 'Step unavailable');

          detailNode = (
            <div className="mt-1.5 pt-1.5 border-t border-amber-500/20 text-xs">
              <p className="text-amber-400/90 italic">{reason}</p>
            </div>
          );
        } else if (status === 'skipped' && !isRunning) {
          detailNode = (
            <div className="mt-1.5 pt-1.5 border-t border-slate-700/40 text-xs">
              <p className="text-slate-400 italic">
                {backendStep?.message || 'Skipped by router'}
              </p>
            </div>
          );
        } else if (status === 'warning' && !isRunning) {
          detailNode = (
            <div className="mt-1.5 pt-1.5 border-t border-amber-500/20 text-xs">
              <p className="text-amber-300 font-medium">
                ⚠️ {backendStep?.safety_notes || backendStep?.output_preview || 'Warning condition identified'}
              </p>
            </div>
          );
        } else if (status === 'running') {
          detailNode = (
            <div className="mt-1.5 text-xs text-primary-300 font-mono animate-pulse">
              Processing step...
            </div>
          );
        }

        return (
          <div key={step.key}>
            <div
              className={`agent-step flex items-start gap-3 p-3 rounded-xl border transition-all duration-300 ${
                status === 'completed'
                  ? 'border-accent-500/40 bg-accent-500/10'
                  : status === 'running'
                  ? 'border-primary-500/60 bg-primary-500/15 shadow-[0_0_15px_rgba(59,130,246,0.15)] ring-1 ring-primary-500/40'
                  : status === 'warning'
                  ? 'border-amber-500/40 bg-amber-500/10'
                  : status === 'skipped'
                  ? 'border-slate-700/60 bg-slate-800/20 opacity-70'
                  : status === 'unavailable' || status === 'no_evidence'
                  ? 'border-amber-500/30 bg-amber-500/5'
                  : status === 'error'
                  ? 'border-danger-500/30 bg-danger-500/10'
                  : 'border-surface-border/60 bg-surface/40 opacity-70'
              }`}
            >
              <StepIcon status={status} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <p
                    className={`text-sm font-semibold truncate ${
                      status === 'completed'
                        ? 'text-accent-300'
                        : status === 'running'
                        ? 'text-primary-300'
                        : status === 'warning'
                        ? 'text-amber-300'
                        : status === 'skipped'
                        ? 'text-slate-400'
                        : status === 'unavailable' || status === 'no_evidence'
                        ? 'text-amber-300'
                        : status === 'error'
                        ? 'text-danger-400'
                        : 'text-slate-300'
                    }`}
                  >
                    {step.label}
                  </p>
                  {status === 'completed' && (
                    <span className="badge-accent text-xs shrink-0 font-medium">Completed</span>
                  )}
                  {status === 'running' && (
                    <span className="badge-primary text-xs shrink-0 font-medium">Running</span>
                  )}
                  {status === 'warning' && (
                    <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-amber-500/20 text-amber-300 border border-amber-500/30 shrink-0">
                      Warning
                    </span>
                  )}
                  {status === 'skipped' && (
                    <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-slate-700/40 text-slate-400 border border-slate-600/40 shrink-0">
                      Skipped
                    </span>
                  )}
                  {(status === 'unavailable' || status === 'no_evidence') && (
                    <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-amber-500/20 text-amber-300 border border-amber-500/30 shrink-0">
                      Unavailable
                    </span>
                  )}
                  {status === 'error' && (
                    <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-danger-500/20 text-danger-300 border border-danger-500/30 shrink-0">
                      Error
                    </span>
                  )}
                  {status === 'pending' && (
                    <span className="text-[11px] text-slate-500 shrink-0">Pending</span>
                  )}
                </div>
                <p className="text-xs text-slate-400 mt-0.5">{step.desc}</p>
                {detailNode}
              </div>
            </div>

            {i < STEPS.length - 1 && (
              <ArrowDown
                className={`mx-auto my-1 h-3.5 w-3.5 transition-all duration-300 ${
                  isRunning && i === runningStepIndex - 1
                    ? 'text-primary-400 animate-bounce'
                    : isRunning && i < runningStepIndex
                    ? 'text-primary-400'
                    : !isRunning && (status === 'completed' || status === 'unavailable')
                    ? 'text-accent-500/70'
                    : 'text-slate-700'
                }`}
              />
            )}
          </div>
        );
      })}

      {/* No data + not running */}
      {steps.length === 0 && !isRunning && (
        <p className="text-xs text-slate-400 text-center pt-2">
          Submit symptoms to execute the AI agent pipeline
        </p>
      )}
    </div>
  );
}
