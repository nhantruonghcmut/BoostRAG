import { apiClient } from './client';
import type {
  LoginRequest,
  LoginResponse,
  MessageResponse,
  RefreshResponse,
  RegisterRequest,
  RegisterResponse,
  UserRead,
} from '@/lib/types/api';

export const authApi = {
  register: (data: RegisterRequest) => apiClient.post<RegisterResponse>('/auth/register', data),

  login: (data: LoginRequest) =>
    apiClient.post<LoginResponse>('/auth/login', data, {
      // @ts-expect-error custom flag consumed by interceptor
      _skipAuthRefresh: true,
    }),

  refresh: () => apiClient.post<RefreshResponse>('/auth/refresh'),

  logout: () => apiClient.post<MessageResponse>('/auth/logout'),

  me: () => apiClient.get<UserRead>('/auth/me'),
};
