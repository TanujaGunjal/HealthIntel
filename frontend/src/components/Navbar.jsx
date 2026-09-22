import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Activity, LogOut, Menu, X, User } from 'lucide-react';
import { useState } from 'react';

export default function Navbar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = () => { logout(); navigate('/'); };

  const navLinks = user
    ? [
        { to: '/dashboard', label: 'Dashboard' },
        { to: '/symptoms', label: 'Symptoms' },
        { to: '/prescription', label: 'Prescription' },
        { to: '/evidence', label: 'Evidence' },
        { to: '/appointments', label: 'Care & Appointments' },
        { to: '/history', label: 'History' },
        { to: '/about', label: 'About' },
      ]
    : [{ to: '/about', label: 'About' }];

  return (
    <nav className="sticky top-0 z-50 border-b border-surface-border bg-surface/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-9 h-9 rounded-xl bg-accent-gradient flex items-center justify-center shadow-glow group-hover:scale-105 transition-transform">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg text-slate-100">
              Health<span className="text-primary-400">Intel</span>
            </span>
          </Link>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-5">
            {navLinks.map(({ to, label }) => (
              <Link
                key={to}
                to={to}
                className={`nav-link ${location.pathname === to ? 'active' : ''}`}
              >
                {label}
              </Link>
            ))}
          </div>

          {/* Auth buttons */}
          <div className="hidden md:flex items-center gap-3">
            {user ? (
              <div className="flex items-center gap-3">
                <Link
                  to="/profile"
                  className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200 transition-colors"
                  title="Edit Profile"
                >
                  <User className="w-4 h-4" />
                  {user.full_name || user.email}
                </Link>
                <button onClick={handleLogout} className="btn-secondary py-2 px-4 text-sm flex items-center gap-2">
                  <LogOut className="w-4 h-4" /> Logout
                </button>
              </div>
            ) : (
              <>
                <Link to="/login" className="btn-secondary py-2 px-4 text-sm">Log In</Link>
                <Link to="/register" className="btn-primary py-2 px-4 text-sm">Get Started</Link>
              </>
            )}
          </div>

          {/* Mobile menu toggle */}
          <button className="md:hidden text-slate-400 hover:text-slate-100" onClick={() => setMobileOpen(!mobileOpen)}>
            {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div className="md:hidden border-t border-surface-border bg-surface-card px-4 py-4 space-y-3 animate-fade-in">
          {navLinks.map(({ to, label }) => (
            <Link key={to} to={to} className="block nav-link py-1" onClick={() => setMobileOpen(false)}>
              {label}
            </Link>
          ))}
          {user ? (
            <>
              <Link to="/profile" className="block text-sm text-slate-300 py-1" onClick={() => setMobileOpen(false)}>
                Profile
              </Link>
              <button onClick={() => { handleLogout(); setMobileOpen(false); }} className="block text-danger-400 text-sm font-medium py-1">
                Log Out
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="block text-sm text-slate-300 py-1" onClick={() => setMobileOpen(false)}>Log In</Link>
              <Link to="/register" className="block text-sm text-primary-400 py-1 font-semibold" onClick={() => setMobileOpen(false)}>Get Started</Link>
            </>
          )}
        </div>
      )}
    </nav>
  );
}
