import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Activity, Mail, Lock, User, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';

const Field = ({ name, type = 'text', label, icon: Icon, placeholder, form, setForm, errors }) => (
  <div>
    <label className="label">{label}</label>
    <div className="relative">
      <Icon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
      <input
        type={type}
        className={`input pl-10 ${errors[name] ? 'ring-2 ring-danger-500' : ''}`}
        placeholder={placeholder}
        value={form[name]}
        onChange={e => setForm({ ...form, [name]: e.target.value })}
        required
      />
    </div>
    {errors[name] && (
      <p className="text-danger-400 text-xs mt-1">{errors[name][0]}</p>
    )}
  </div>
);

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', username: '', password: '', password2: '' });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrors({});
    if (form.password !== form.password2) {
      setErrors({ password2: ['Passwords do not match.'] });
      return;
    }
    setLoading(true);
    try {
      await register(form);
      toast.success('Account created! Please sign in.');
      navigate('/login');
    } catch (err) {
      setErrors(err.response?.data || { non_field_errors: ['Registration failed. Please try again.'] });
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12 bg-surface">
      <div className="w-full max-w-md animate-fade-in">
        <div className="text-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-accent-gradient flex items-center justify-center mx-auto mb-4 shadow-glow">
            <Activity className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-slate-100">Create account</h1>
          <p className="text-slate-400 mt-1">Join HealthIntel — free educational tool</p>
        </div>

        <div className="card">
          {errors.non_field_errors && (
            <div className="flex items-center gap-2 bg-danger-500/10 border border-danger-500/30 rounded-xl p-3 mb-4 text-danger-300 text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" /> {errors.non_field_errors[0]}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Field name="email" type="email" label="Email address" icon={Mail} placeholder="you@example.com" form={form} setForm={setForm} errors={errors} />
            <Field name="username" label="Username" icon={User} placeholder="yourname" form={form} setForm={setForm} errors={errors} />
            <Field name="password" type="password" label="Password" icon={Lock} placeholder="••••••••" form={form} setForm={setForm} errors={errors} />
            <Field name="password2" type="password" label="Confirm password" icon={Lock} placeholder="••••••••" form={form} setForm={setForm} errors={errors} />

            <button type="submit" className="btn-primary w-full" disabled={loading}>
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Creating account...
                </span>
              ) : 'Create Account'}
            </button>
          </form>

          <p className="text-center text-slate-400 text-sm mt-6">
            Already have an account?{' '}
            <Link to="/login" className="text-primary-400 hover:text-primary-300 font-medium">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
