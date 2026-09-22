import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Save, Loader, AlertCircle, CheckCircle } from 'lucide-react';
import { authAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

const SEX_OPTIONS = [
  { value: '', label: 'Select…' },
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other', label: 'Other' },
  { value: 'prefer_not_to_say', label: 'Prefer not to say' },
];

export default function ProfileSetup() {
  const navigate = useNavigate();
  const { user, setUser } = useAuth();
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState('');

  const [form, setForm] = useState({
    full_name: '',
    age: '',
    sex: '',
    height_cm: '',
    weight_kg: '',
    known_allergies: '',
    existing_conditions: '',
  });

  // Pre-fill with existing profile data
  useEffect(() => {
    authAPI.profile()
      .then(({ data }) => {
        setForm({
          full_name: data.full_name || '',
          age: data.age || '',
          sex: data.sex || '',
          height_cm: data.height_cm || '',
          weight_kg: data.weight_kg || '',
          known_allergies: data.known_allergies || '',
          existing_conditions: data.existing_conditions || '',
        });
      })
      .catch(() => {})
      .finally(() => setFetching(false));
  }, []);

  const handleChange = (e) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.full_name.trim()) { setError('Full name is required.'); return; }
    if (!form.age || Number(form.age) < 1 || Number(form.age) > 120) {
      setError('Please enter a valid age (1–120).'); return;
    }
    if (!form.sex) { setError('Please select your sex.'); return; }

    setLoading(true);
    setError('');
    try {
      const payload = {
        full_name: form.full_name.trim(),
        age: parseInt(form.age, 10),
        sex: form.sex,
        height_cm: form.height_cm ? parseFloat(form.height_cm) : null,
        weight_kg: form.weight_kg ? parseFloat(form.weight_kg) : null,
        known_allergies: form.known_allergies.trim(),
        existing_conditions: form.existing_conditions.trim(),
      };
      const { data } = await authAPI.updateProfile(payload);
      if (setUser) setUser(prev => ({ ...prev, ...data }));
      toast.success('Profile saved!');
      navigate('/dashboard');
    } catch (err) {
      const msg = err.response?.data
        ? Object.values(err.response.data).flat().join(' ')
        : 'Failed to save profile. Please try again.';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  if (fetching) return (
    <div className="min-h-screen flex items-center justify-center bg-surface">
      <div className="w-10 h-10 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-12 animate-fade-in">
      <div className="mb-8 text-center">
        <div className="w-16 h-16 bg-primary-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <User className="w-8 h-8 text-primary-400" />
        </div>
        <h1 className="text-3xl font-bold text-slate-100 mb-2">Complete Your Profile</h1>
        <p className="text-slate-400">
          Provide a few basic details to personalise your health-information experience.
        </p>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Full name */}
          <div>
            <label className="label" htmlFor="full_name">Full Name <span className="text-danger-400">*</span></label>
            <input
              id="full_name"
              name="full_name"
              type="text"
              className="input"
              placeholder="e.g. Jane Doe"
              value={form.full_name}
              onChange={handleChange}
              disabled={loading}
            />
          </div>

          {/* Age + Sex */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label" htmlFor="age">Age <span className="text-danger-400">*</span></label>
              <input
                id="age"
                name="age"
                type="number"
                min={1}
                max={120}
                className="input"
                placeholder="e.g. 28"
                value={form.age}
                onChange={handleChange}
                disabled={loading}
              />
            </div>
            <div>
              <label className="label" htmlFor="sex">Sex <span className="text-danger-400">*</span></label>
              <select
                id="sex"
                name="sex"
                className="input"
                value={form.sex}
                onChange={handleChange}
                disabled={loading}
              >
                {SEX_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Height + Weight (optional) */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label" htmlFor="height_cm">Height <span className="text-slate-500 font-normal">(cm, optional)</span></label>
              <input
                id="height_cm"
                name="height_cm"
                type="number"
                min={50}
                max={300}
                step="0.1"
                className="input"
                placeholder="e.g. 165"
                value={form.height_cm}
                onChange={handleChange}
                disabled={loading}
              />
            </div>
            <div>
              <label className="label" htmlFor="weight_kg">Weight <span className="text-slate-500 font-normal">(kg, optional)</span></label>
              <input
                id="weight_kg"
                name="weight_kg"
                type="number"
                min={1}
                max={500}
                step="0.1"
                className="input"
                placeholder="e.g. 60"
                value={form.weight_kg}
                onChange={handleChange}
                disabled={loading}
              />
            </div>
          </div>

          {/* Known allergies */}
          <div>
            <label className="label" htmlFor="known_allergies">
              Known Allergies <span className="text-slate-500 font-normal">(optional)</span>
            </label>
            <input
              id="known_allergies"
              name="known_allergies"
              type="text"
              className="input"
              placeholder="e.g. Penicillin, Peanuts, Latex"
              value={form.known_allergies}
              onChange={handleChange}
              disabled={loading}
            />
            <p className="text-xs text-slate-500 mt-1">Separate multiple entries with commas.</p>
          </div>

          {/* Existing conditions */}
          <div>
            <label className="label" htmlFor="existing_conditions">
              Existing Conditions <span className="text-slate-500 font-normal">(optional)</span>
            </label>
            <input
              id="existing_conditions"
              name="existing_conditions"
              type="text"
              className="input"
              placeholder="e.g. Asthma, Hypertension, Type 2 Diabetes"
              value={form.existing_conditions}
              onChange={handleChange}
              disabled={loading}
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 bg-danger-500/10 border border-danger-500/30 rounded-xl p-3 text-danger-300 text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" /> {error}
            </div>
          )}

          <div className="disclaimer-box text-xs">
            <strong>Privacy:</strong> Your profile information is stored securely and used only to
            personalise your health-information experience within HealthIntel. It is never shared
            with third parties. This is not a medical record.
          </div>

          <button
            type="submit"
            id="save-profile-btn"
            className="btn-primary w-full flex items-center justify-center gap-2"
            disabled={loading}
          >
            {loading ? (
              <><Loader className="w-4 h-4 animate-spin" /> Saving…</>
            ) : (
              <><Save className="w-4 h-4" /> Save Profile &amp; Continue</>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
