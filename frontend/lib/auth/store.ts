'use client';

import { create } from 'zustand';

import type { UserSummary } from '@/lib/types/api';

interface AuthState {
  accessToken: string | null;
  expiresAt: number | null;
  user: UserSummary | null;
  isAuthenticated: boolean;
  setAuth: (token: string, expiresIn: number, user: UserSummary) => void;
  setAccessToken: (token: string, expiresIn: number) => void;
  setUser: (user: UserSummary | null) => void;
  clearAuth: () => void;
}

/**
 * Auth store — in-memory only (KHÔNG dùng localStorage cho access token).
 * Refresh token được lưu HttpOnly cookie từ backend; access token tự rotate
 * trên client qua call `/auth/refresh` khi expired.
 */
export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  expiresAt: null,
  user: null,
  isAuthenticated: false,

  setAuth: (token, expiresIn, user) =>
    set({
      accessToken: token,
      expiresAt: Date.now() + expiresIn * 1000,
      user,
      isAuthenticated: true,
    }),

  setAccessToken: (token, expiresIn) =>
    set((s) => ({
      ...s,
      accessToken: token,
      expiresAt: Date.now() + expiresIn * 1000,
      isAuthenticated: !!s.user,
    })),

  setUser: (user) =>
    set((s) => ({
      ...s,
      user,
      isAuthenticated: !!user && !!s.accessToken,
    })),

  clearAuth: () =>
    set({
      accessToken: null,
      expiresAt: null,
      user: null,
      isAuthenticated: false,
    }),
}));
