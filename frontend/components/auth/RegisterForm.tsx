'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useTranslations } from 'next-intl';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { z } from 'zod';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useRegister } from '@/lib/auth/useAuth';
import { ApiError } from '@/lib/types/api';

type Messages = ReturnType<typeof useTranslations<string>>;

function buildSchema(t: Messages) {
  return z.object({
    full_name: z
      .string({ required_error: t('validation.fullName.required') })
      .min(1, t('validation.fullName.required'))
      .max(150, t('validation.fullName.maxLength')),
    email: z
      .string({ required_error: t('validation.email.required') })
      .min(1, t('validation.email.required'))
      .email(t('validation.email.invalid')),
    password: z
      .string({ required_error: t('validation.password.required') })
      .min(10, t('validation.password.minLength'))
      .regex(/[A-Za-z]/, t('validation.password.needLetter'))
      .regex(/\d/, t('validation.password.needDigit')),
  });
}

export function RegisterForm() {
  const t = useTranslations();
  const router = useRouter();
  const schema = buildSchema(t);
  type FormValues = z.infer<typeof schema>;

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { full_name: '', email: '', password: '' },
  });

  const reg = useRegister();

  const onSubmit = handleSubmit(async (values) => {
    try {
      await reg.mutateAsync(values);
      toast.success(t('auth.register.success'));
      router.push('/login');
    } catch (error) {
      const message = mapErrorToMessage(error, t);
      toast.error(message);
    }
  });

  return (
    <form onSubmit={onSubmit} className="space-y-5" noValidate>
      <div className="space-y-2">
        <Label htmlFor="full_name">{t('common.fullName')}</Label>
        <Input
          id="full_name"
          autoComplete="name"
          aria-invalid={!!errors.full_name}
          {...register('full_name')}
        />
        {errors.full_name && <p className="text-sm text-destructive">{errors.full_name.message}</p>}
      </div>

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
          autoComplete="new-password"
          aria-invalid={!!errors.password}
          {...register('password')}
        />
        <p className="text-xs text-muted-foreground">{t('auth.register.passwordHint')}</p>
        {errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}
      </div>

      <Button type="submit" disabled={reg.isPending} className="w-full">
        {reg.isPending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
        {t('auth.register.submit')}
      </Button>

      <p className="text-center text-sm text-muted-foreground">
        {t('auth.register.haveAccount')}{' '}
        <Link href="/login" className="font-medium text-primary hover:underline">
          {t('auth.register.loginLink')}
        </Link>
      </p>
    </form>
  );
}

function mapErrorToMessage(error: unknown, t: Messages): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case 'RESOURCE_CONFLICT':
        return t('auth.errors.emailExists');
      case 'VALIDATION_ERROR':
        return t('auth.errors.passwordTooWeak');
      case 'NETWORK_ERROR':
        return t('auth.errors.network');
      default:
        return error.message || t('auth.errors.generic');
    }
  }
  return t('auth.errors.generic');
}
