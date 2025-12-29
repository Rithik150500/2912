import { create } from 'zustand';
import { authApi } from '../services/api';

interface User {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  role: 'client' | 'advocate';
  is_active: boolean;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    email: string;
    password: string;
    full_name: string;
    phone?: string;
    role: 'client' | 'advocate';
  }) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem('accessToken'),
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authApi.login(email, password);
      const { access_token, refresh_token } = response.data;

      localStorage.setItem('accessToken', access_token);
      localStorage.setItem('refreshToken', refresh_token);

      // Load user data
      const userResponse = await authApi.getMe();
      set({
        user: userResponse.data,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error: unknown) {
      const message = (error as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail || 'Login failed';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  register: async (data) => {
    set({ isLoading: true, error: null });
    try {
      await authApi.register(data);
      // Auto login after registration
      const loginResponse = await authApi.login(data.email, data.password);
      const { access_token, refresh_token } = loginResponse.data;

      localStorage.setItem('accessToken', access_token);
      localStorage.setItem('refreshToken', refresh_token);

      const userResponse = await authApi.getMe();
      set({
        user: userResponse.data,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error: unknown) {
      const message = (error as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail || 'Registration failed';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  logout: () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    set({ user: null, isAuthenticated: false });
  },

  loadUser: async () => {
    if (!localStorage.getItem('accessToken')) {
      set({ isAuthenticated: false, user: null });
      return;
    }

    set({ isLoading: true });
    try {
      const response = await authApi.getMe();
      set({
        user: response.data,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  clearError: () => set({ error: null }),
}));
