/**
 * API service layer — all Axios calls to the Django backend.
 */
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = localStorage.getItem('refresh_token');
      if (refresh) {
        try {
          const { data } = await axios.post(`${API_BASE}/api/auth/refresh/`, { refresh });
          localStorage.setItem('access_token', data.access);
          original.headers.Authorization = `Bearer ${data.access}`;
          return api(original);
        } catch {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

// ==========================================
// Auth
// ==========================================
export const authAPI = {
  register: (data) => api.post('/api/auth/register/', data),
  login: (data) => api.post('/api/auth/login/', data),
  profile: () => api.get('/api/auth/profile/'),
  updateProfile: (data) => api.patch('/api/auth/profile/', data),
};

// ==========================================
// Symptoms
// ==========================================
export const symptomsAPI = {
  analyze: (symptoms) => api.post('/api/symptoms/analyze/', { symptoms }),
  workflow: (symptoms) => api.post('/api/symptoms/workflow/', { symptoms }),
  getDetail: (id) => api.get(`/api/symptoms/${id}/`),
};

// ==========================================
// RAG
// ==========================================
export const ragAPI = {
  query: (query, top_k = 5) => api.post('/api/rag/query/', { query, top_k }),
};

// ==========================================
// Prescription
// ==========================================
export const prescriptionAPI = {
  analyze: (imageFile) => {
    const formData = new FormData();
    formData.append('image', imageFile);
    return api.post('/api/prescription/analyze/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  explain: (id) => api.post(`/api/prescription/${id}/explain/`),
};

export const calendarAPI = {
  status: () => api.get('/api/calendar/status/'),
  authorize: () => api.get('/api/calendar/oauth/authorize/'),
  disconnect: () => api.post('/api/calendar/oauth/disconnect/'),
  schedule: (data) => api.post('/api/calendar/schedule/', data),
};

// ==========================================
// Appointments
// ==========================================
export const appointmentsAPI = {
  list: () => api.get('/api/appointments/'),
  create: (data) => api.post('/api/appointments/', data),
  cancel: (id) => api.delete(`/api/appointments/${id}/`),
  detail: (id) => api.get(`/api/appointments/${id}/`),
};

// ==========================================
// History
// ==========================================
export const historyAPI = {
  get: () => api.get('/api/history/'),
};

// ==========================================
// Health check
// ==========================================
export const healthAPI = {
  check: () => api.get('/api/health/'),
};

export default api;
