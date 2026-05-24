'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { ChatPanel } from '@/components/chat/ChatPanel';
import { SessionSidebar } from '@/components/chat/SessionSidebar';
import { useAuthStore } from '@/lib/auth/store';
import { useCurrentUser } from '@/lib/auth/useAuth';

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  const t = useTranslations();
  const router = useRouter();
  const accessToken = useAuthStore((s) => s.accessToken);
  const { data: user, isLoading } = useCurrentUser();

  useEffect(() => {
    if (!accessToken) router.replace('/login');
  }, [accessToken, router]);

  if (!accessToken || (isLoading && !user)) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        {t('common.loading')}
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col">
      <header className="flex h-14 shrink-0 items-center justify-between border-b px-4">
        <span className="font-semibold">{t('common.chat')}</span>
        {user && <span className="text-sm text-muted-foreground">{user.email}</span>}
      </header>
      <div className="flex min-h-0 flex-1">{children}</div>
    </div>
  );
}
