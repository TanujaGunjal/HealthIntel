import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import SymptomAnalyzer from './pages/SymptomAnalyzer';
import PrescriptionReader from './pages/PrescriptionReader';
import HealthReport from './pages/HealthReport';
import EvidenceSearch from './pages/EvidenceSearch';
import About from './pages/About';
import ProfileSetup from './pages/ProfileSetup';
import History from './pages/History';
import Appointments from './pages/Appointments';

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-surface">
      <div className="w-10 h-10 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );
  return user ? children : <Navigate to="/login" replace />;
}

function AppRoutes() {
  return (
    <div className="min-h-screen bg-surface text-slate-100">
      <Navbar />
      <div className="clinical-theme min-h-screen bg-white text-slate-900">
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/about" element={<About />} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><ProfileSetup /></ProtectedRoute>} />
        <Route path="/symptoms" element={<ProtectedRoute><SymptomAnalyzer /></ProtectedRoute>} />
        <Route path="/prescription" element={<ProtectedRoute><PrescriptionReader /></ProtectedRoute>} />
        <Route path="/report/:id" element={<ProtectedRoute><HealthReport /></ProtectedRoute>} />
        <Route path="/evidence" element={<ProtectedRoute><EvidenceSearch /></ProtectedRoute>} />
        <Route path="/history" element={<ProtectedRoute><History /></ProtectedRoute>} />
        <Route path="/appointments" element={<ProtectedRoute><Appointments /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </div>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#1e293b',
            color: '#f1f5f9',
            border: '1px solid #334155',
            borderRadius: '12px',
          },
        }}
      />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
