import axios from 'axios';

const API_URL = '/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = localStorage.getItem('refreshToken');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token, refresh_token } = response.data;
          localStorage.setItem('accessToken', access_token);
          localStorage.setItem('refreshToken', refresh_token);

          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        } catch {
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          window.location.href = '/login';
        }
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  register: (data: {
    email: string;
    password: string;
    full_name: string;
    phone?: string;
    role: 'client' | 'advocate';
  }) => api.post('/auth/register', data),

  login: (email: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    return api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
  },

  getMe: () => api.get('/auth/me'),
  logout: () => api.post('/auth/logout'),
};

// Client API
export const clientApi = {
  // Conversations
  createConversation: () => api.post('/client/conversations', {}),
  getConversations: () => api.get('/client/conversations'),
  getConversation: (id: string) => api.get(`/client/conversations/${id}`),
  sendMessage: (conversationId: string, content: string) =>
    api.post(`/client/conversations/${conversationId}/messages`, { content }),

  // Cases
  getCases: () => api.get('/client/cases'),
  getCase: (id: string) => api.get(`/client/cases/${id}`),
  getRecommendations: (caseId: string) =>
    api.get(`/client/cases/${caseId}/recommendations`),
  selectAdvocate: (caseId: string, advocateId: string) =>
    api.post(`/client/cases/${caseId}/select-advocate`, { advocate_id: advocateId }),

  // Notifications
  getNotifications: (unreadOnly = false) =>
    api.get(`/client/notifications?unread_only=${unreadOnly}`),
  markNotificationRead: (id: string) =>
    api.post(`/client/notifications/${id}/read`),
};

// Advocate API
export const advocateApi = {
  // Profile
  getProfile: () => api.get('/advocate/profile'),
  createProfile: (data: Record<string, unknown>) => api.post('/advocate/profile', data),
  updateProfile: (data: Record<string, unknown>) => api.put('/advocate/profile', data),
  updateAvailability: (isAvailable: boolean) =>
    api.put('/advocate/availability', { is_available: isAvailable }),

  // Case Requests
  getCaseRequests: (status?: string) =>
    api.get(`/advocate/case-requests${status ? `?status_filter=${status}` : ''}`),
  getCaseRequest: (id: string) => api.get(`/advocate/case-requests/${id}`),
  acceptCaseRequest: (id: string) => api.post(`/advocate/case-requests/${id}/accept`),
  rejectCaseRequest: (id: string, reason?: string) =>
    api.post(`/advocate/case-requests/${id}/reject`, {
      action: 'reject',
      rejection_reason: reason,
    }),

  // Accepted Cases
  getCases: () => api.get('/advocate/cases'),
  getCase: (id: string) => api.get(`/advocate/cases/${id}`),
  sendMessage: (caseId: string, content: string) =>
    api.post(`/advocate/cases/${caseId}/messages`, { content }),

  // Notifications
  getNotifications: (unreadOnly = false) =>
    api.get(`/advocate/notifications?unread_only=${unreadOnly}`),
};

export default api;
