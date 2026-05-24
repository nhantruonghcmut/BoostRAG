'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';

import { authApi } from '@/lib/api/auth';
import { useAuthStore } from '@/lib/auth/store';
import type { LoginRequest, RegisterRequest } from '@/lib/types/api';

const ME_KEY = ['auth', 'me'] as const;

/** Lấy user hiện tại từ /auth/me. Chỉ fire khi có access token. */
export function useCurrentUser() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const setUser = useAuthStore((s) => s.setUser);

  return useQuery({
    queryKey: ME_KEY,
    queryFn: async () => {
      const user = await authApi.me();
      setUser({
        id: user.id,
        email: user.email,
        full_name: user.full_name,
        role: user.role,
      });
      return user;
    },
    enabled: !!accessToken,
    retry: false,
    staleTime: 30_000,
  });
}

export function useLogin() {
  const setAuth = useAuthStore((s) => s.setAuth);
  const router = useRouter();
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (data: LoginRequest) => authApi.login(data),
    onSuccess: (data) => {
      setAuth(data.access_token, data.expires_in, data.user);
      qc.invalidateQueries({ queryKey: ME_KEY });
      router.push('/chat');
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: (data: RegisterRequest) => authApi.register(data),
  });
}

export function useLogout() {
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const router = useRouter();
  const qc = useQueryClient();

  return useMutation({
    mutationFn: () => authApi.logout(),
    onSettled: () => {
      clearAuth();
      qc.clear();
      router.push('/login');
    },
  });
}
