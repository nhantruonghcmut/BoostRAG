'use client';

import Link from 'next/link';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useTranslations } from 'next-intl';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { z } from 'zod';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useLogin } from '@/lib/auth/useAuth';
import { ApiError } from '@/lib/types/api';

type Messages = ReturnType<typeof useTranslations<string>>;

function buildSchema(t: Messages) {
  return z.object({
    email: z
      .string({ required_error: t('validation.email.required') })
      .min(1, t('validation.email.required'))
      .email(t('validation.email.invalid')),
    password: z
      .string({ required_error: t('validation.password.required') })
      .min(1, t('validation.password.required')),
  });
}

export function LoginForm() {
  const t = useTranslations();
  const schema = buildSchema(t);
  type FormValues = z.infer<typeof schema>;

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: '', password: '' },
  });

  const login = useLogin();

  const onSubmit = handleSubmit(async (values) => {
    try {
      await login.mutateAsync(values);
      toast.success(t('auth.login.success'));
    } catch (error) {
      const message = mapErrorToMessage(error, t);
      toast.error(message);
    }
  });

  return (
    <form onSubmit={onSubmit} className="space-y-5" noValidate>
      <div className="space-y-2">
        <Label htmlFor="email">{t('common.email')}</Label>
        <Input
          id="email"
          type="email"
          autoComplete="email"
          placeholder="user@example.com"
          aria-invalid={!!errors.email}
          {...register('email')}
        />
        {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
      </div>

      <div className="space-y-2">
        <Label htmlFor="password">{t('common.password')}</Label>
        <Input
          id="password"
          type="password"
          autoComplete="current-password"
          aria-invalid={!!errors.password}
          {...register('password')}
        />
        {errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}
      </div>

      <Button type="submit" disabled={login.isPending} className="w-full">
        {login.isPending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
        {t('auth.login.submit')}
      </Button>

      <p className="text-center text-sm text-muted-foreground">
        {t('auth.login.noAccount')}{' '}
        <Link href="/register" className="font-medium text-primary hover:underline">
          {t('auth.login.registerLink')}
        </Link>
      </p>
    </form>
  );
}

function mapErrorToMessage(error: unknown, t: Messages): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case 'AUTH_INVALID_CREDENTIALS':
        return t('auth.errors.invalidCredentials');
      case 'AUTH_PENDING_APPROVAL':
        return t('auth.errors.pendingApproval');
      case 'AUTH_ACCOUNT_LOCKED':
        return t('auth.errors.accountLocked');
      case 'AUTH_ACCOUNT_DISABLED':
        return t('auth.errors.accountDisabled');
      case 'NETWORK_ERROR':
        return t('auth.errors.network');
      default:
        return error.message || t('auth.errors.generic');
    }
  }
  return t('auth.errors.generic');
}
