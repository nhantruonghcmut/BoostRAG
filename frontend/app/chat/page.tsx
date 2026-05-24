'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { ArrowLeft, MessageSquareText } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { useCurrentUser } from '@/lib/auth/useAuth';
import { useAuthStore } from '@/lib/auth/store';

export default function ChatPlaceholderPage() {
  const t = useTranslations();
  const router = useRouter();
  const accessToken = useAuthStore((s) => s.accessToken);

  useEffect(() => {
    if (!accessToken) router.replace('/login');
  }, [accessToken, router]);

  const { data: user, isLoading } = useCurrentUser();

  return (
    <div className="container flex min-h-screen flex-col items-center justify-center gap-6 py-16 text-center">
      <MessageSquareText className="h-16 w-16 text-primary/50" aria-hidden />
      <h1 className="text-3xl font-semibold">{t('common.chat')}</h1>
      <p className="max-w-md text-muted-foreground">{t('common.comingSoon')}</p>
      {!isLoading && user && (
        <p className="text-sm text-muted-foreground">
          Logged in as <span className="font-medium">{user.email}</span> · {user.role}
        </p>
      )}
      <Button asChild variant="outline">
        <Link href="/">
          <ArrowLeft className="h-4 w-4" aria-hidden />
          {t('common.back')}
        </Link>
      </Button>
    </div>
  );
}
