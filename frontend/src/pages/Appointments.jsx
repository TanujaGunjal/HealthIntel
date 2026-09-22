import { useState, useEffect } from 'react';
import {
  AlertCircle,
  ArrowRight,
  Building2,
  Calendar,
  CalendarDays,
  CheckCircle,
  Clock3,
  Loader,
  MapPin,
  Plus,
  Search,
  ShieldCheck,
  Star,
  X,
} from 'lucide-react';
import { appointmentsAPI } from '../services/api';
import toast from 'react-hot-toast';

const PROVIDER_TYPES = [
  'General Practitioner',
  'Family Doctor',
  'Internist',
  'Cardiologist',
  'Dermatologist',
  'Neurologist',
  'Orthopedist',
  'Pediatrician',
  'Psychiatrist',
  'Pulmonologist',
  'Gastroenterologist',
  'ENT Specialist',
  'Ophthalmologist',
  'Other Specialist',
];

const PROVIDER_DIRECTORY = [
  {
    id: 'dr-sarah-chen',
    name: 'Dr. Sarah Chen',
    specialty: 'Primary Care',
    clinic: 'Northside Family Clinic',
    address: '1080 Wellness Ave, Brooklyn, NY',
    rating: 4.9,
    distance: '1.2 mi',
    nextAvailability: 'Today • 2:30 PM',
    tags: ['Accepting new patients', 'Virtual care'],
  },
  {
    id: 'dr-michael-ortega',
    name: 'Dr. Michael Ortega',
    specialty: 'Cardiology',
    clinic: 'Harbor Heart Center',
    address: '245 Bayfront Blvd, Brooklyn, NY',
    rating: 4.8,
    distance: '2.8 mi',
    nextAvailability: 'Tomorrow • 9:00 AM',
    tags: ['Same-day consults', 'Heart screening'],
  },
  {
    id: 'dr-emma-nelson',
    name: 'Dr. Emma Nelson',
    specialty: 'Dermatology',
    clinic: 'Bright Skin Studio',
    address: '420 Linden Street, Brooklyn, NY',
    rating: 4.9,
    distance: '3.6 mi',
    nextAvailability: 'Thu • 1:15 PM',
    tags: ['Skin evaluations', 'Telehealth'],
  },
  {
    id: 'dr-omar-rashid',
    name: 'Dr. Omar Rashid',
    specialty: 'Internal Medicine',
    clinic: 'Beacon Health Group',
    address: '910 Atlantic Ave, Brooklyn, NY',
    rating: 4.7,
    distance: '4.1 mi',
    nextAvailability: 'Today • 5:45 PM',
    tags: ['Wellness visits', 'Lab referrals'],
  },
  {
    id: 'dr-priya-ashok',
    name: 'Dr. Priya Ashok',
    specialty: 'Pediatrics',
    clinic: 'Little Sprouts Medical',
    address: '77 Garden Row, Queens, NY',
    rating: 5.0,
    distance: '5.4 mi',
    nextAvailability: 'Fri • 10:00 AM',
    tags: ['New patient visits', 'Family care'],
  },
  {
    id: 'dr-lee-watson',
    name: 'Dr. Lee Watson',
    specialty: 'Neurology',
    clinic: 'Summit Neuro Clinic',
    address: '14 Park Terrace, Manhattan, NY',
    rating: 4.8,
    distance: '7.2 mi',
    nextAvailability: 'Mon • 3:30 PM',
    tags: ['Headache care', 'Testing referrals'],
  },
];

const STATUS_STYLES = {
  upcoming: 'bg-emerald-100 text-emerald-700 border border-emerald-200',
  completed: 'bg-slate-200 text-slate-700 border border-slate-300',
  cancelled: 'bg-red-100 text-red-700 border border-red-200',
};

function BookingForm({ onBooked, onClose, initialValues = {} }) {
  const [form, setForm] = useState({
    provider_name: '',
    provider_type: '',
    provider_address: '',
    appointment_date: '',
    appointment_time: '',
    notes: '',
    ...initialValues,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setForm((prev) => ({
      ...prev,
      provider_name: initialValues.provider_name || prev.provider_name || '',
      provider_type: initialValues.provider_type || prev.provider_type || '',
      provider_address: initialValues.provider_address || prev.provider_address || '',
    }));
  }, [initialValues]);

  const today = new Date().toISOString().split('T')[0];

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.provider_name.trim()) {
      setError('Provider name is required.');
      return;
    }
    if (!form.appointment_date) {
      setError('Please select a date.');
      return;
    }
    if (!form.appointment_time) {
      setError('Please select a time.');
      return;
    }

    setLoading(true);
    try {
      const { data } = await appointmentsAPI.create(form);
      toast.success('Appointment booked!');
      onBooked(data);
      onClose();
    } catch (err) {
      const msg = err.response?.data
        ? Object.values(err.response.data).flat().join(' ')
        : 'Booking failed. Please try again.';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-sm">
      <div className="w-full max-w-lg mx-4 rounded-[28px] border border-slate-200 bg-white p-6 shadow-2xl">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-lg font-bold text-slate-900">
            <Plus className="h-5 w-5 text-emerald-600" /> Book Appointment
          </h2>
          <button
            onClick={onClose}
            className="rounded-full p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900"
            aria-label="Close booking form"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="provider_name">
              Provider / Clinic Name <span className="text-red-500">*</span>
            </label>
            <input
              id="provider_name"
              name="provider_name"
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 placeholder:text-slate-400 focus:border-emerald-400 focus:outline-none"
              placeholder="e.g. City Health Clinic, Dr. Sarah Ahmed"
              value={form.provider_name}
              onChange={handleChange}
              disabled={loading}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="provider_type">
                Provider Type
              </label>
              <select
                id="provider_type"
                name="provider_type"
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 focus:border-emerald-400 focus:outline-none"
                value={form.provider_type}
                onChange={handleChange}
                disabled={loading}
              >
                <option value="">Select type…</option>
                {PROVIDER_TYPES.map((type) => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="provider_address">
                Address / Location
              </label>
              <input
                id="provider_address"
                name="provider_address"
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 placeholder:text-slate-400 focus:border-emerald-400 focus:outline-none"
                placeholder="e.g. 12 Main Street"
                value={form.provider_address}
                onChange={handleChange}
                disabled={loading}
              />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="appointment_date">
                Date <span className="text-red-500">*</span>
              </label>
              <input
                id="appointment_date"
                name="appointment_date"
                type="date"
                min={today}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 focus:border-emerald-400 focus:outline-none"
                value={form.appointment_date}
                onChange={handleChange}
                disabled={loading}
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="appointment_time">
                Time <span className="text-red-500">*</span>
              </label>
              <input
                id="appointment_time"
                name="appointment_time"
                type="time"
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 focus:border-emerald-400 focus:outline-none"
                value={form.appointment_time}
                onChange={handleChange}
                disabled={loading}
              />
            </div>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700" htmlFor="notes">
              Notes
            </label>
            <textarea
              id="notes"
              name="notes"
              className="h-20 w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 placeholder:text-slate-400 focus:border-emerald-400 focus:outline-none"
              placeholder="Reason for visit, special instructions, etc."
              value={form.notes}
              onChange={handleChange}
              disabled={loading}
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-600">
              <AlertCircle className="h-4 w-4 flex-shrink-0" /> {error}
            </div>
          )}

          <button
            type="submit"
            id="book-appointment-btn"
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-6 py-3 font-semibold text-white transition-all hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader className="h-4 w-4 animate-spin" /> Booking…
              </>
            ) : (
              <>
                <Calendar className="h-4 w-4" /> Confirm Booking
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function Appointments() {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [searchQuery, setSearchQuery] = useState('Brooklyn, NY');
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [cancelling, setCancelling] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    appointmentsAPI
      .list()
      .then(({ data }) => setAppointments(data))
      .catch(() => setError('Failed to load appointments.'))
      .finally(() => setLoading(false));
  }, []);

  const filteredProviders = PROVIDER_DIRECTORY.filter((provider) => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    return [provider.name, provider.specialty, provider.clinic, provider.address]
      .join(' ')
      .toLowerCase()
      .includes(query);
  });

  const handleBooked = (newAppt) => {
    setAppointments((prev) => [newAppt, ...prev]);
  };

  const handleCancel = async (id) => {
    if (!window.confirm('Cancel this appointment?')) return;
    setCancelling(id);
    try {
      await appointmentsAPI.cancel(id);
      setAppointments((prev) =>
        prev.map((a) => (a.id === id ? { ...a, status: 'cancelled' } : a)),
      );
      toast.success('Appointment cancelled.');
    } catch {
      toast.error('Could not cancel appointment.');
    } finally {
      setCancelling(null);
    }
  };

  const handleOpenBooking = (provider) => {
    setSelectedProvider({
      provider_name: provider.name,
      provider_type: provider.specialty,
      provider_address: provider.address,
    });
    setShowForm(true);
  };

  const upcoming = appointments.filter((a) => a.status === 'upcoming');
  const past = appointments.filter((a) => a.status !== 'upcoming');

  return (
    <div className="min-h-screen bg-white text-slate-900">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {showForm && (
          <BookingForm
            onBooked={handleBooked}
            onClose={() => {
              setShowForm(false);
              setSelectedProvider(null);
            }}
            initialValues={selectedProvider || {}}
          />
        )}

        <section className="rounded-[32px] border border-slate-200 bg-gradient-to-r from-[#edf9f4] via-[#f6fbff] to-[#ffffff] p-6 shadow-[0_20px_50px_rgba(15,23,42,0.08)] sm:p-8">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-emerald-700">
                Care & Appointments
              </p>
              <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
                Find the right care, close to home.
              </h1>
            </div>
            <button
              type="button"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-emerald-600/20 transition hover:bg-emerald-500"
              onClick={() => setShowForm(true)}
            >
              Find Appointments
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>

          <div className="mt-6 grid gap-3 rounded-2xl border border-slate-200 bg-white/80 p-3 shadow-sm backdrop-blur sm:grid-cols-2 xl:grid-cols-[1.4fr_1.1fr_1fr_auto]">
            <label className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-600">
              <Search className="h-4 w-4 text-slate-500" />
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search city or specialist"
                className="w-full bg-transparent text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none"
              />
            </label>

            <label className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-600">
              <CalendarDays className="h-4 w-4 text-slate-500" />
              <select className="w-full bg-transparent text-sm text-slate-800 focus:outline-none">
                <option>Any specialty</option>
                <option>Primary Care</option>
                <option>Cardiology</option>
                <option>Dermatology</option>
                <option>Pediatrics</option>
              </select>
            </label>

            <label className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-600">
              <Calendar className="h-4 w-4 text-slate-500" />
              <input
                type="date"
                className="w-full bg-transparent text-sm text-slate-800 focus:outline-none"
              />
            </label>

            <button
              type="button"
              className="rounded-xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
            >
              Search
            </button>
          </div>
        </section>

        <section className="mt-8 overflow-hidden rounded-[30px] border border-slate-200 bg-white shadow-[0_18px_40px_rgba(15,23,42,0.06)]">
          <div className="grid lg:grid-cols-[1.6fr_0.8fr]">
            <div className="relative min-h-[300px] overflow-hidden bg-[linear-gradient(135deg,#edf8f7_0%,#dff2f5_30%,#ecf3ff_100%)] p-6">
              <div className="absolute inset-0 opacity-75" style={{ backgroundImage: 'linear-gradient(rgba(148,163,184,0.18) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,0.18) 1px, transparent 1px)', backgroundSize: '36px 36px' }} />
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(62,214,176,0.18),transparent_30%),radial-gradient(circle_at_80%_70%,rgba(83,146,255,0.15),transparent_32%)]" />

              <div className="relative flex h-full flex-col justify-between">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.25em] text-emerald-700">
                      Nearby providers
                    </p>
                    <h2 className="mt-2 text-2xl font-bold text-slate-900">Brooklyn care map</h2>
                  </div>
                  <div className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                    19 providers open
                  </div>
                </div>

                <div className="relative mt-6 h-52">
                  <div className="absolute left-[12%] top-[16%] h-20 w-20 rounded-full bg-emerald-200/60 blur-2xl" />
                  <div className="absolute bottom-[16%] right-[18%] h-20 w-20 rounded-full bg-blue-200/60 blur-2xl" />

                  <div className="absolute left-[18%] top-[30%] rounded-full border-2 border-white bg-emerald-500 p-2 shadow-lg shadow-emerald-500/40">
                    <MapPin className="h-4 w-4 text-white" />
                  </div>
                  <div className="absolute right-[22%] top-[38%] rounded-full border-2 border-white bg-sky-500 p-2 shadow-lg shadow-sky-500/40">
                    <MapPin className="h-4 w-4 text-white" />
                  </div>
                  <div className="absolute left-[45%] top-[52%] rounded-full border-2 border-white bg-violet-500 p-2 shadow-lg shadow-violet-500/40">
                    <MapPin className="h-4 w-4 text-white" />
                  </div>
                  <div className="absolute left-[62%] top-[28%] rounded-full border-2 border-white bg-amber-500 p-2 shadow-lg shadow-amber-500/40">
                    <MapPin className="h-4 w-4 text-white" />
                  </div>
                  <div className="absolute bottom-[18%] left-[52%] rounded-full border-2 border-white bg-rose-500 p-2 shadow-lg shadow-rose-500/40">
                    <MapPin className="h-4 w-4 text-white" />
                  </div>
                </div>
              </div>
            </div>

            <aside className="bg-slate-50 p-6">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-slate-900">Quick access</h3>
                  <ShieldCheck className="h-5 w-5 text-emerald-600" />
                </div>

                <div className="mt-5 space-y-4">
                  <div className="rounded-2xl bg-emerald-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-700">Today</p>
                    <p className="mt-2 text-2xl font-bold text-slate-900">5 open</p>
                    <p className="text-sm text-slate-600">within 15 minutes</p>
                  </div>

                  <div className="rounded-2xl bg-sky-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-sky-700">Care type</p>
                    <p className="mt-2 text-2xl font-bold text-slate-900">Primary</p>
                    <p className="text-sm text-slate-600">best match for you</p>
                  </div>
                </div>
              </div>
            </aside>
          </div>
        </section>

        <section className="mt-8">
          <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-2xl font-bold text-slate-900">Nearby Providers</h2>
              <p className="mt-1 text-sm text-slate-600">
                {filteredProviders.length} providers near {searchQuery || 'your area'}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowForm(true)}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:text-slate-900"
            >
              <Plus className="h-4 w-4" /> New appointment
            </button>
          </div>

          {filteredProviders.length === 0 ? (
            <div className="rounded-[28px] border border-dashed border-slate-300 bg-white p-10 text-center text-slate-600">
              No providers match your search. Try a different city or specialty.
            </div>
          ) : (
            <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
              {filteredProviders.map((provider) => (
                <article
                  key={provider.id}
                  className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-[0_10px_30px_rgba(15,23,42,0.04)] transition hover:-translate-y-1 hover:shadow-[0_18px_40px_rgba(15,23,42,0.09)]"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="rounded-2xl bg-emerald-100 p-2.5 text-emerald-700">
                        <Building2 className="h-5 w-5" />
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-slate-900">{provider.name}</h3>
                        <p className="text-sm text-slate-500">{provider.specialty}</p>
                      </div>
                    </div>
                    <div className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-700">
                      <Star className="h-3.5 w-3.5 fill-current" />
                      {provider.rating}
                    </div>
                  </div>

                  <div className="mt-5 flex flex-wrap gap-2">
                    {provider.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-medium text-slate-600"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>

                  <div className="mt-5 space-y-2 text-sm text-slate-600">
                    <div className="flex items-start gap-2">
                      <MapPin className="mt-0.5 h-4 w-4 text-slate-400" />
                      <span>{provider.address}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock3 className="h-4 w-4 text-slate-400" />
                      <span>{provider.nextAvailability}</span>
                    </div>
                  </div>

                  <div className="mt-6 flex items-center justify-between border-t border-slate-200 pt-4">
                    <div>
                      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-400">Distance</p>
                      <p className="mt-1 text-base font-semibold text-slate-900">{provider.distance}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-100"
                      >
                        View Profile
                      </button>
                      <button
                        type="button"
                        onClick={() => handleOpenBooking(provider)}
                        className="rounded-xl bg-emerald-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-emerald-500"
                      >
                        Book
                      </button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="mt-10">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-slate-900">Your appointments</h2>
              <p className="mt-1 text-sm text-slate-600">Manage upcoming and recent visits.</p>
            </div>
          </div>

          {error && (
            <div className="mb-5 flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-600">
              <AlertCircle className="h-5 w-5 flex-shrink-0" /> {error}
            </div>
          )}

          {loading ? (
            <div className="rounded-[28px] border border-slate-200 bg-white p-10 text-center shadow-sm">
              <Loader className="mx-auto h-8 w-8 animate-spin text-emerald-600" />
            </div>
          ) : appointments.length === 0 ? (
            <div className="rounded-[28px] border border-slate-200 bg-white p-10 text-center shadow-sm">
              <Calendar className="mx-auto h-12 w-12 text-slate-300" />
              <p className="mt-4 text-lg font-semibold text-slate-700">No appointments yet</p>
              <p className="mt-2 text-sm text-slate-500">Book your first appointment with a healthcare provider.</p>
              <button
                type="button"
                onClick={() => setShowForm(true)}
                className="mt-6 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-500"
              >
                Book Now
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              {upcoming.length > 0 && (
                <div>
                  <h3 className="mb-3 flex items-center gap-2 text-base font-semibold text-slate-700">
                    <Clock3 className="h-4 w-4 text-emerald-600" /> Upcoming ({upcoming.length})
                  </h3>
                  <div className="space-y-3">
                    {upcoming.map((appt) => (
                      <AppointmentCard
                        key={appt.id}
                        appt={appt}
                        onCancel={handleCancel}
                        cancelling={cancelling === appt.id}
                      />
                    ))}
                  </div>
                </div>
              )}

              {past.length > 0 && (
                <div>
                  <h3 className="mb-3 flex items-center gap-2 text-base font-semibold text-slate-700">
                    <CheckCircle className="h-4 w-4 text-slate-500" /> Past Appointments ({past.length})
                  </h3>
                  <div className="space-y-3">
                    {past.map((appt) => (
                      <AppointmentCard
                        key={appt.id}
                        appt={appt}
                        onCancel={null}
                        cancelling={false}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function AppointmentCard({ appt, onCancel, cancelling }) {
  return (
    <div className="flex flex-col gap-3 rounded-[24px] border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-start sm:justify-between">
      <div className="flex items-start gap-4">
        <div className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${STATUS_STYLES[appt.status]}`}>
          {appt.status}
        </div>

        <div className="min-w-0">
          <p className="text-lg font-semibold text-slate-900">{appt.provider_name}</p>
          {appt.provider_type && <p className="text-sm text-slate-500">{appt.provider_type}</p>}

          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              {new Date(`${appt.appointment_date}T00:00:00`).toLocaleDateString(undefined, {
                weekday: 'short',
                year: 'numeric',
                month: 'short',
                day: 'numeric',
              })}
            </span>
            <span className="flex items-center gap-1">
              <Clock3 className="h-3.5 w-3.5" />
              {appt.appointment_time?.slice(0, 5)}
            </span>
            {appt.provider_address && (
              <span className="flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5" />
                {appt.provider_address}
              </span>
            )}
          </div>

          {appt.notes && <p className="mt-2 text-xs italic text-slate-500">{appt.notes}</p>}
        </div>
      </div>

      {onCancel && appt.status === 'upcoming' && (
        <button
          type="button"
          onClick={() => onCancel(appt.id)}
          disabled={cancelling}
          className="inline-flex items-center justify-center gap-1 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs font-semibold text-red-600 transition hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {cancelling ? <Loader className="h-3.5 w-3.5 animate-spin" /> : <X className="h-3.5 w-3.5" />}
          Cancel
        </button>
      )}
    </div>
  );
}
