'use client';

import axios, {
  AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios';

import { useAuthStore } from '@/lib/auth/store';
import { ApiError, type ApiErrorResponse, type RefreshResponse } from '@/lib/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface InternalConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
  _skipAuthRefresh?: boolean;
}

const instance: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});

instance.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`);
  }
  return config;
});

let refreshInflight: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  if (refreshInflight) return refreshInflight;
  refreshInflight = (async () => {
    try {
      const resp = await axios.post<RefreshResponse>(
        `${API_BASE_URL}/auth/refresh`,
        {},
        { withCredentials: true },
      );
      const { access_token, expires_in } = resp.data;
      useAuthStore.getState().setAccessToken(access_token, expires_in);
      return access_token;
    } finally {
      refreshInflight = null;
    }
  })();
  return refreshInflight;
}

instance.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorResponse>) => {
    const original = error.config as InternalConfig | undefined;
    const status = error.response?.status;

    if (
      status === 401 &&
      original &&
      !original._retry &&
      !original._skipAuthRefresh &&
      original.url &&
      !original.url.endsWith('/auth/login') &&
      !original.url.endsWith('/auth/refresh')
    ) {
      original._retry = true;
      try {
        const newToken = await refreshAccessToken();
        original.headers.set('Authorization', `Bearer ${newToken}`);
        return instance.request(original);
      } catch {
        useAuthStore.getState().clearAuth();
      }
    }

    const payload = error.response?.data;
    if (payload?.error) {
      throw new ApiError(payload.error, status ?? 0);
    }
    throw new ApiError(
      {
        code: 'NETWORK_ERROR',
        message: error.message || 'Network error',
      },
      status ?? 0,
    );
  },
);

export const apiClient = {
  async get<T>(path: string, config?: AxiosRequestConfig): Promise<T> {
    const r: AxiosResponse<T> = await instance.get(path, config);
    return r.data;
  },
  async post<T>(path: string, body?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const r: AxiosResponse<T> = await instance.post(path, body, config);
    return r.data;
  },
  async patch<T>(path: string, body?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const r: AxiosResponse<T> = await instance.patch(path, body, config);
    return r.data;
  },
  async delete<T = void>(path: string, config?: AxiosRequestConfig): Promise<T> {
    const r: AxiosResponse<T> = await instance.delete(path, config);
    return r.data;
  },
  raw: instance,
};

export type { AxiosRequestConfig };
