import { useCallback, useEffect, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  AlertCircle,
  BookOpen,
  Calendar,
  CheckCircle,
  ChevronDown,
  ExternalLink,
  FileText,
  Loader,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
} from 'lucide-react';
import { calendarAPI, prescriptionAPI } from '../services/api';
import toast from 'react-hot-toast';

const WORKFLOW_STAGES = [
  'Image Processing',
  'OCR Extraction',
  'Medicine Identification',
  'Instruction Extraction',
  'Evidence Retrieval',
  'Safety Validation',
  'AI Explanation',
];

const confidenceLabel = (value = 0) => {
  if (value >= 0.9) return 'High confidence';
  if (value >= 0.7) return 'Medium confidence';
  return 'Review required';
};

const confidenceStyle = (value = 0) => (
  value >= 0.9
    ? 'text-accent-400 bg-accent-500/10'
    : value >= 0.7
      ? 'text-amber-300 bg-amber-500/10'
      : 'text-danger-300 bg-danger-500/10'
);

const display = (value, fallback = 'Not extracted') => value || fallback;
const CALENDAR_STATE_KEY = 'healthintel-prescription-calendar-state';

function reminderCount(frequency = '') {
  const value = frequency.toLowerCase();
  if (value.includes('four') || value.includes('4')) return 4;
  if (value.includes('three') || value.includes('3')) return 3;
  if (value.includes('twice') || value.includes('two') || value.includes('2')) return 2;
  if (value.includes('once') || value.includes('daily') || value.includes('1')) return 1;
  return 1;
}

function stageStatus(result, label) {
  return result?.workflow?.find((stage) => stage.label === label)?.status || 'pending';
}

function Stage({ result, label }) {
  const status = stageStatus(result, label);
  const color = status === 'completed'
    ? 'text-accent-400'
    : status === 'failed'
      ? 'text-danger-400'
      : status === 'unavailable'
        ? 'text-amber-300'
        : 'text-slate-500';

  return (
    <div className="flex items-center gap-2 rounded-lg bg-surface p-3 text-sm">
      <CheckCircle className={`h-4 w-4 ${color}`} />
      <span className="text-slate-200">{label}</span>
      <span className="ml-auto text-xs capitalize text-slate-400">{status}</span>
    </div>
  );
}

function ConfidenceBadge({ value }) {
  const score = Number(value || 0);
  return (
    <span className={`inline-flex rounded-full px-2 py-1 text-xs ${confidenceStyle(score)}`}>
      {Math.round(score * 100)}% · {confidenceLabel(score)}
    </span>
  );
}

function ExtractedField({ value, confidence, fallback = 'Unable to confidently extract' }) {
  return (
    <div>
      <div>{display(value, fallback)}</div>
      {confidence != null && <div className="mt-1"><ConfidenceBadge value={confidence} /></div>}
    </div>
  );
}

export default function PrescriptionReader() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [showOcr, setShowOcr] = useState(false);
  const [explaining, setExplaining] = useState(false);
  const [explanation, setExplanation] = useState('');
  const [calendarConnected, setCalendarConnected] = useState(false);
  const [scheduledMedicineIds, setScheduledMedicineIds] = useState(new Set());
  const [selectedTimes, setSelectedTimes] = useState({});
  const [schedulingInProgress, setSchedulingInProgress] = useState({});
  const [calendarLoading, setCalendarLoading] = useState(false);

  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview);
  }, [preview]);

  useEffect(() => {
    try {
      const savedState = JSON.parse(sessionStorage.getItem(CALENDAR_STATE_KEY) || 'null');
      if (savedState?.result) setResult(savedState.result);
      if (savedState?.selectedTimes && typeof savedState.selectedTimes === 'object') {
        setSelectedTimes(savedState.selectedTimes);
      }
    } catch {
      sessionStorage.removeItem(CALENDAR_STATE_KEY);
    }
  }, []);

  useEffect(() => {
    if (result) {
      sessionStorage.setItem(CALENDAR_STATE_KEY, JSON.stringify({ result, selectedTimes }));
    }
  }, [result, selectedTimes]);

  useEffect(() => {
    let mounted = true;
    const checkCalendarStatus = async () => {
      try {
        const { data } = await calendarAPI.status();
        if (!mounted) return;
        setCalendarConnected(Boolean(data.connected));
        if (Array.isArray(data.scheduled_medicine_ids)) {
          setScheduledMedicineIds(new Set(data.scheduled_medicine_ids));
        }
      } catch (err) {
        if (!mounted) return;
        setCalendarConnected(false);
      }
    };
    checkCalendarStatus();

    // Handle return from redirect OAuth
    const params = new URLSearchParams(window.location.search);
    if (params.get('calendar_connected') === 'true') {
      setCalendarConnected(true);
      toast.success('Google Calendar Connected');
      window.history.replaceState({}, '', window.location.pathname);
      checkCalendarStatus();
    } else if (params.get('calendar_error')) {
      toast.error(params.get('calendar_error'));
      window.history.replaceState({}, '', window.location.pathname);
    }

    // Handle message from popup OAuth
    const handleMessage = (event) => {
      if (event.data?.type === 'GOOGLE_CALENDAR_CONNECTED') {
        setCalendarConnected(true);
        setCalendarLoading(false);
        toast.success('Google Calendar Connected');
        checkCalendarStatus();
      } else if (event.data?.type === 'GOOGLE_CALENDAR_ERROR') {
        setCalendarLoading(false);
        toast.error(event.data.error || 'Google Calendar connection failed');
      }
    };
    window.addEventListener('message', handleMessage);

    return () => {
      mounted = false;
      window.removeEventListener('message', handleMessage);
    };
  }, []);

  const onDrop = useCallback((accepted, rejected) => {
    if (rejected.length) {
      toast.error('File rejected. Use an image up to 10 MB.');
      return;
    }
    const selected = accepted[0];
    if (!selected) return;
    setFile(selected);
    setPreview(URL.createObjectURL(selected));
    setResult(null);
    setExplanation('');
    setSelectedTimes({});
    sessionStorage.removeItem(CALENDAR_STATE_KEY);
    setError('');
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'] },
    maxSize: 10 * 1024 * 1024,
    multiple: false,
  });

  const analyze = async () => {
    if (!file) return;
    setLoading(true);
    setError('');
    setExplanation('');
    try {
      const { data } = await prescriptionAPI.analyze(file);
      setResult(data);
      sessionStorage.setItem(CALENDAR_STATE_KEY, JSON.stringify({ result: data, selectedTimes: {} }));
      if (data.explanation) {
        setExplanation(data.explanation);
      }
      if (data.status === 'OCR_FAILED' || data.status === 'EXTRACTION_FAILED') {
        setError(data.message || 'The prescription could not be structured. Please verify the original image.');
      } else {
        toast.success('Prescription analysis complete.');
      }
    } catch (err) {
      const message = err.response?.data?.error || 'OCR analysis failed. Please try a clearer image.';
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const explain = async () => {
    if (!result?.id) return;
    setExplaining(true);
    setError('');
    try {
      const { data } = await prescriptionAPI.explain(result.id);
      if (data.explanation) setExplanation(data.explanation);
      else setError(data.message || 'AI explanation is unavailable.');
    } catch (err) {
      setError(err.response?.data?.message || err.response?.data?.error || 'AI explanation is unavailable.');
    } finally {
      setExplaining(false);
    }
  };

  const clear = () => {
    if (preview) URL.revokeObjectURL(preview);
    setFile(null);
    setPreview(null);
    setResult(null);
    setExplanation('');
    setSelectedTimes({});
    sessionStorage.removeItem(CALENDAR_STATE_KEY);
    setError('');
  };

  const handleConnectCalendar = async () => {
    setCalendarLoading(true);
    try {
      const { data } = await calendarAPI.authorize();
      if (data.authorization_url) {
        const popup = window.open(data.authorization_url, 'google_oauth', 'width=600,height=700');
        if (!popup || popup.closed || typeof popup.closed === 'undefined') {
          // Popup was blocked — save state then do a full redirect
          window.location.assign(data.authorization_url);
        } else {
          // Monitor the popup: if it closes without sending a postMessage, let the user know
          const pollTimer = setInterval(() => {
            if (popup.closed) {
              clearInterval(pollTimer);
              // Give any in-flight postMessage 500 ms to land before showing cancellation
              setTimeout(() => {
                setCalendarLoading(false);
              }, 500);
            }
          }, 400);
        }
      }
    } catch (err) {
      toast.error(err.response?.data?.error || 'Unable to connect Google Calendar.');
      setCalendarLoading(false);
    }
    // Loading state is cleared either by postMessage handler or popup-close poll
  };

  const handleDisconnectCalendar = async () => {
    setCalendarLoading(true);
    try {
      await calendarAPI.disconnect();
      setCalendarConnected(false);
      toast.success('Google Calendar disconnected. Existing events kept.');
    } catch (err) {
      toast.error(err.response?.data?.error || 'Unable to disconnect Google Calendar.');
    } finally {
      setCalendarLoading(false);
    }
  };

  const handleScheduleMedicine = async (medicine) => {
    if (!medicine.id) {
      toast.error('Medicine record ID not found. Please analyze a prescription first.');
      return;
    }
    const time = selectedTimes[medicine.id];
    if (!time) {
      toast.error('Please select a reminder time.');
      return;
    }
    if (!calendarConnected) {
      toast.error('Please connect Google Calendar first.');
      handleConnectCalendar();
      return;
    }
    if (!medicine.duration) {
      toast.error(`${medicine.name}: prescription duration is required to create a calendar reminder. Please verify the original prescription.`);
      return;
    }
    if (schedulingInProgress[medicine.id] || scheduledMedicineIds.has(medicine.id)) {
      return;
    }

    setSchedulingInProgress((prev) => ({ ...prev, [medicine.id]: true }));
    try {
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
      const today = new Date();
      const yyyy = today.getFullYear();
      const mm = String(today.getMonth() + 1).padStart(2, '0');
      const dd = String(today.getDate()).padStart(2, '0');
      const startTime = `${yyyy}-${mm}-${dd}T${time}:00`;

      await calendarAPI.schedule({
        medicine_id: medicine.id,
        start_time: startTime,
        timezone,
        frequency: medicine.frequency || 'daily',
      });

      setScheduledMedicineIds((prev) => new Set([...prev, medicine.id]));
      toast.success(`✓ Added ${medicine.name} to Google Calendar`);
    } catch (err) {
      const status = err.response?.status;
      const message = err.response?.data?.error;
      if (status === 401) {
        // Token expired — backend deleted the credential; reflect that in the UI
        setCalendarConnected(false);
        toast.error('Google Calendar authorization expired. Please reconnect.');
      } else {
        toast.error(message || `Unable to schedule reminder for ${medicine.name}.`);
      }
    } finally {
      setSchedulingInProgress((prev) => ({ ...prev, [medicine.id]: false }));
    }
  };

  const medicines = result?.medicines || [];
  const schedule = result?.schedule || [];
  const warnings = result?.validation?.warnings || [];
  const evidence = Array.isArray(result?.evidence)
    ? result.evidence
    : (result?.evidence?.items || result?.sources || []);
  const safetyResults = result?.safety?.results || [];
  // Backend returns cleaned_ocr_text (primary) or ocr_text (alias)
  const ocrText = result?.cleaned_ocr_text || result?.ocr_text || result?.ocr?.text || '';
  const pipelineStatus = result?.pipeline_status || result?.status ||
    (result?.ocr_engine && result.ocr_engine !== 'none' ? 'SUCCESS' : 'OCR_FAILED');



  return (
    <div className="prescription-page min-h-screen bg-white text-slate-900">
      <div className="mx-auto max-w-7xl animate-fade-in px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="section-title flex items-center gap-2">
          <FileText className="h-7 w-7 text-accent-400" />
          Prescription Understanding
        </h1>
        <p className="section-subtitle">
          Extract and review prescription instructions with transparent confidence, safety, and evidence states.
        </p>
      </div>

      <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-1">
          {!file ? (
            <div
              {...getRootProps()}
              className={`card flex min-h-64 cursor-pointer flex-col items-center justify-center border-2 border-dashed ${
                isDragActive ? 'border-primary-500 bg-primary-500/5' : 'border-surface-border hover:border-primary-500/50'
              }`}
            >
              <input {...getInputProps()} />
              <Upload className="mb-4 h-12 w-12 text-slate-500" />
              <p className="font-medium text-slate-200">Drop a prescription image</p>
              <p className="mt-1 text-sm text-slate-400">or click to select · max 10 MB</p>
            </div>
          ) : (
            <div className="card space-y-4">
              <div className="flex justify-between gap-2">
                <span className="truncate text-sm text-slate-300">{file.name}</span>
                <button onClick={clear} className="text-slate-400 hover:text-danger-400" aria-label="Remove image">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <img src={preview} alt="Prescription preview" className="max-h-72 w-full rounded-xl bg-surface object-contain" />
              <button onClick={analyze} disabled={loading} className="btn-accent flex w-full justify-center gap-2">
                {loading ? <><Loader className="h-4 w-4 animate-spin" /> Processing…</> : <><FileText className="h-4 w-4" /> Analyze prescription</>}
              </button>
            </div>
          )}
          {error && (
            <div className="flex gap-2 rounded-xl border border-danger-500/30 bg-danger-500/10 p-4 text-sm text-danger-300">
              <AlertCircle className="h-5 w-5 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        <div className="lg:col-span-2">
          <div className="card">
            <h2 className="mb-4 font-semibold text-slate-100">Prescription Analysis Workflow</h2>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {WORKFLOW_STAGES.map((label) => <Stage key={label} result={result} label={label} />)}
            </div>
            {loading && <p className="mt-4 text-sm text-primary-300">Processing… stages update after backend work completes.</p>}
            {!loading && !result && <p className="mt-4 text-sm text-slate-400">Upload an image to begin.</p>}
          </div>
        </div>
      </div>

      {result && (
        <div className="space-y-6">
          <section className="card overflow-x-auto">
            <div className="mb-4 flex items-center justify-between gap-4">
              <div>
                <h2 className="font-semibold text-slate-100">Prescription Summary</h2>
                <p className="text-sm text-slate-400">
                  {medicines.length} medicine{medicines.length === 1 ? '' : 's'} detected · extraction confidence is not medical correctness.
                </p>
              </div>
              <span className={`rounded-full px-3 py-1 text-xs ${pipelineStatus === 'SUCCESS' ? 'bg-accent-500/10 text-accent-400' : pipelineStatus === 'OCR_FAILED' ? 'bg-danger-500/10 text-danger-400' : 'bg-amber-500/10 text-amber-300'}`}>
                {pipelineStatus}
              </span>
            </div>
            <table className="w-full min-w-[820px] text-sm">
              <thead className="border-b border-surface-border text-left text-slate-400 font-medium">
                <tr><th className="pb-3">Medicine</th><th>Dosage</th><th>Frequency</th><th>Duration</th><th>Timing</th><th>Extraction confidence</th></tr>
              </thead>
              <tbody>
                {medicines.map((medicine, index) => (
                  <tr key={`${medicine.name}-${index}`} className="border-b border-surface-border/60">
                    <td className="py-3 font-medium text-slate-200">
                      {display(medicine.name)}
                      {medicine.needs_verification && <span className="block text-xs text-amber-300">Needs verification</span>}
                    </td>
                    <td className="text-slate-300"><ExtractedField value={medicine.dosage} confidence={medicine.field_confidence?.dosage} /></td>
                    <td className="text-slate-300"><ExtractedField value={medicine.frequency} confidence={medicine.field_confidence?.frequency} /></td>
                    <td className="text-slate-300"><ExtractedField value={medicine.duration} confidence={medicine.field_confidence?.duration} /></td>
                    <td className="text-slate-300"><ExtractedField value={medicine.timing} confidence={medicine.field_confidence?.timing} fallback="Timing not specified" /></td>
                    <td><ConfidenceBadge value={medicine.extraction_confidence ?? medicine.confidence} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!medicines.length && <p className="py-5 text-center text-slate-400 italic">OCR text was read, but no medicine could be confidently normalized.</p>}
          </section>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <section className="card">
              <h2 className="mb-4 font-semibold text-slate-100">Medication Schedule</h2>
              {schedule.length ? schedule.map((item, index) => (
                <div key={`${item.medicine}-${index}`} className="mb-2 rounded-lg bg-surface p-3">
                  <p className="text-xs uppercase tracking-wide text-accent-400">{item.period || item.timing || 'Timing not specified'}</p>
                  <p className="font-medium text-slate-200">{item.medicine} {item.dosage || ''}</p>
                  <p className="text-sm text-slate-400">{item.instruction || 'Instruction not specified'}</p>
                </div>
              )) : <p className="text-sm text-slate-400 italic">Timing not specified in the extracted prescription.</p>}
            </section>

            <section className="card">
              <h2 className="mb-4 font-semibold text-slate-100">Prescription Validation</h2>
              {warnings.length ? warnings.map((warning, index) => (
                <p key={index} className="mb-2 flex gap-2 text-sm text-amber-300"><AlertCircle className="h-4 w-4 shrink-0" />{warning}</p>
              )) : <p className="text-sm text-accent-400">✓ Required medicine fields were extracted.</p>}
              {result.validation?.status && <p className="mt-3 text-xs capitalize text-slate-400">Validation status: {result.validation.status}</p>}
            </section>
          </div>

          {/* Google Calendar Section */}
          <section className="card" id="google-calendar-section">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-surface-border pb-4">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-primary-500/10 p-2 text-primary-400">
                  <Calendar className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="font-semibold text-slate-100">Google Calendar Reminders</h2>
                  <p className="text-xs text-slate-400">
                    Schedule medication reminders directly into your Google Calendar.
                  </p>
                </div>
              </div>

              <div>
                {!calendarConnected ? (
                  <button
                    onClick={handleConnectCalendar}
                    disabled={calendarLoading}
                    className="btn-accent flex items-center gap-2 text-xs py-2 px-3"
                  >
                    {calendarLoading ? (
                      <><Loader className="h-3.5 w-3.5 animate-spin" /> Connecting…</>
                    ) : (
                      <><Calendar className="h-3.5 w-3.5" /> Add to Google Calendar</>
                    )}
                  </button>
                ) : (
                  <div className="flex items-center gap-3">
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-accent-500/10 px-3 py-1 text-xs font-medium text-accent-400">
                      <CheckCircle className="h-3.5 w-3.5" />
                      Google Calendar Connected
                    </span>
                    <button
                      onClick={handleDisconnectCalendar}
                      disabled={calendarLoading}
                      className="text-xs text-slate-400 underline hover:text-danger-400 transition-colors"
                      title="Disconnect Google Calendar (existing events kept)"
                    >
                      Disconnect
                    </button>
                  </div>
                )}
              </div>
            </div>

            <div className="mt-4 space-y-3">
              {medicines.length === 0 ? (
                <p className="text-sm italic text-slate-400">No extracted medications to schedule.</p>
              ) : (
                medicines.map((medicine, index) => {
                  const requiresVerification = Boolean(
                    medicine.needs_verification || !medicine.frequency
                  );
                  const isScheduled = Boolean(medicine.id && scheduledMedicineIds.has(medicine.id));
                  const isScheduling = Boolean(medicine.id && schedulingInProgress[medicine.id]);
                  const selectedTime = selectedTimes[medicine.id] || '';

                  const freqOrTiming = medicine.timing && (!medicine.frequency || medicine.frequency.toLowerCase().includes('daily') || medicine.frequency.toLowerCase().includes('once'))
                    ? medicine.timing
                    : (medicine.frequency || 'Frequency not specified');
                  const instructionLine = medicine.duration ? `${freqOrTiming} · ${medicine.duration}` : freqOrTiming;

                  return (
                    <div
                      key={medicine.id || `${medicine.name}-${index}`}
                      className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-xl border border-surface-border bg-surface p-4"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-100">
                            {medicine.name} {medicine.dosage || ''}
                          </span>
                          {requiresVerification && (
                            <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-xs font-medium text-amber-300">
                              Requires verification
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-slate-400">
                          {instructionLine}
                        </p>
                      </div>

                      <div className="flex items-center gap-3">
                        {requiresVerification ? (
                          <div className="rounded-lg bg-surface-elevated px-3 py-1.5 text-xs text-amber-300">
                            Requires verification
                          </div>
                        ) : isScheduled ? (
                          <div className="flex items-center gap-3">
                            <span className="flex items-center gap-1.5 text-sm font-medium text-accent-400">
                              <CheckCircle className="h-4 w-4" />
                              ✓ Added to Google Calendar
                            </span>
                            <a
                              href="https://calendar.google.com/"
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-1 text-xs text-primary-400 underline hover:text-primary-300"
                            >
                              Open Google Calendar
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            <input
                              type="time"
                              aria-label={`Select reminder time for ${medicine.name}`}
                              value={selectedTime}
                              disabled={isScheduling}
                              onChange={(e) => {
                                const val = e.target.value;
                                setSelectedTimes((prev) => ({ ...prev, [medicine.id]: val }));
                              }}
                              className="rounded-lg border border-surface-border bg-surface-elevated px-3 py-1.5 text-sm text-slate-200 focus:border-primary-500 focus:outline-none"
                            />
                            <button
                              onClick={() => {
                                if (!calendarConnected) {
                                  toast.error('Please connect Google Calendar first.');
                                  handleConnectCalendar();
                                } else {
                                  handleScheduleMedicine(medicine);
                                }
                              }}
                              disabled={!selectedTime || isScheduling}
                              className="btn-accent py-1.5 px-3 text-xs flex items-center gap-1.5 disabled:opacity-50"
                            >
                              {isScheduling ? (
                                <><Loader className="h-3.5 w-3.5 animate-spin" /> Scheduling…</>
                              ) : (
                                'Schedule'
                              )}
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </section>
          <section className="card">
            <h2 className="mb-3 flex gap-2 font-semibold text-slate-100"><ShieldCheck className="h-5 w-5 text-accent-400" /> Medication Safety</h2>
            <p className="text-sm text-amber-300">{result.safety?.status === 'SAFETY_CHECK_UNAVAILABLE' ? 'Safety validation unavailable' : (result.safety?.message || 'Safety validation unavailable')}</p>
            {safetyResults.map((item, index) => (
              <div key={index} className="mt-3 rounded-lg border border-surface-border bg-surface p-3 text-sm">
                <p className="text-amber-300">{item.title || item.status || 'Potential interaction detected'}</p>
                <p className="mt-1 text-slate-400">{item.explanation || item.message || 'Review this result with a qualified healthcare professional.'}</p>
              </div>
            ))}
            <p className="mt-4 text-xs text-slate-500">Verify medication information with a qualified healthcare professional. This is an informational safety check, not a diagnosis or prescribing system.</p>
          </section>

          <section className="card">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div><h2 className="flex gap-2 font-semibold text-slate-100"><Sparkles className="h-5 w-5 text-primary-300" /> Explain This Prescription</h2><p className="mt-1 text-sm text-slate-500">Educational explanation only; the prescribed dosage and medicines are never changed.</p></div>
              <button onClick={explain} disabled={explaining || !result.id} className="btn-accent flex items-center gap-2">
                {explaining ? <><Loader className="h-4 w-4 animate-spin" /> Explaining…</> : <><Sparkles className="h-4 w-4" /> Explain Prescription</>}
              </button>
            </div>
            {explanation && (
              <div className="mt-4 rounded-lg bg-surface p-4 text-sm leading-6 text-slate-300">
                {typeof explanation === 'string' ? explanation : (
                  <>
                    <p>{explanation.summary}</p>
                    {explanation.medicines?.map((item) => (
                      <div key={item.name} className="mt-3 rounded-lg border border-surface-border bg-surface-elevated/40 p-3">
                        <p className="font-medium text-accent-400">{item.name}</p>
                        <p className="mt-2 whitespace-pre-line text-slate-300">{item.explanation}</p>
                      </div>
                    ))}
                    {explanation.limitations?.map((item) => <p key={item} className="mt-2 text-amber-300">{item}</p>)}
                    {explanation.disclaimer && <p className="mt-3 text-xs text-slate-500">{explanation.disclaimer}</p>}
                  </>
                )}
              </div>
            )}
          </section>

          <section className="card">
            <h2 className="mb-3 flex gap-2 font-semibold text-slate-100"><BookOpen className="h-5 w-5 text-accent-400" /> Evidence Sources</h2>
            {evidence.length ? evidence.map((source, index) => (
              <div key={index} className="mb-2 rounded-lg bg-surface p-3 text-sm">
                <p className="font-medium text-slate-200">{source.title || source.source_file || source.source || 'Reference source'}</p>
                <p className="mt-1 text-slate-400">{source.text || source.snippet || source.excerpt || source.description}</p>
                {source.similarity_score != null && <p className="mt-2 text-xs text-slate-500">Similarity: {Math.round(Number(source.similarity_score) * 100)}%</p>}
              </div>
            )) : <p className="text-sm text-slate-500">{result?.evidence?.status === 'NO_MATCHES' ? 'No relevant evidence found.' : 'Evidence retrieval unavailable.'}</p>}
          </section>

          <section className="card">
            <button onClick={() => setShowOcr((visible) => !visible)} className="flex w-full items-center justify-between text-left font-semibold text-slate-100">
              <span>Raw OCR Text</span><ChevronDown className={`h-5 w-5 transition-transform ${showOcr ? 'rotate-180' : ''}`} />
            </button>
            {showOcr && <pre className="mt-4 max-h-72 overflow-auto whitespace-pre-wrap rounded-lg bg-surface p-4 text-sm text-slate-400">{ocrText || 'No OCR text available.'}</pre>}
          </section>
        </div>
      )}


      <p className="mt-8 text-center text-xs text-slate-500">Educational information only. Always verify prescriptions and medication questions with a qualified healthcare professional.</p>
      </div>
    </div>
  );
}
