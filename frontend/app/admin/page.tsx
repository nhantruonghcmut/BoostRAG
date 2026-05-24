'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { ArrowLeft, ShieldCheck } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/lib/auth/store';
import { useCurrentUser } from '@/lib/auth/useAuth';

export default function AdminPlaceholderPage() {
  const t = useTranslations();
  const router = useRouter();
  const accessToken = useAuthStore((s) => s.accessToken);
  const { data: user, isLoading } = useCurrentUser();

  useEffect(() => {
    if (!accessToken) {
      router.replace('/login');
    } else if (!isLoading && user && user.role !== 'admin') {
      router.replace('/chat');
    }
  }, [accessToken, isLoading, router, user]);

  return (
    <div className="container flex min-h-screen flex-col items-center justify-center gap-6 py-16 text-center">
      <ShieldCheck className="h-16 w-16 text-primary/50" aria-hidden />
      <h1 className="text-3xl font-semibold">Admin</h1>
      <p className="max-w-md text-muted-foreground">{t('common.comingSoon')}</p>
      <Button asChild variant="outline">
        <Link href="/">
          <ArrowLeft className="h-4 w-4" aria-hidden />
          {t('common.back')}
        </Link>
      </Button>
    </div>
  );
}
