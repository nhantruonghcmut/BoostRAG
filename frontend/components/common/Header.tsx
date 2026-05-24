'use client';

import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { Sparkles } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { LanguageSwitcher } from '@/components/common/LanguageSwitcher';
import { useAuthStore } from '@/lib/auth/store';

export function Header() {
  const t = useTranslations();
  const isAuthed = useAuthStore((s) => s.isAuthenticated);

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/85 backdrop-blur">
      <div className="container flex h-16 items-center justify-between">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <Sparkles className="h-5 w-5 text-primary" aria-hidden />
          <span>{t('common.appName')}</span>
        </Link>
        <nav className="flex items-center gap-3">
          <LanguageSwitcher />
          {isAuthed ? (
            <Button asChild size="sm">
              <Link href="/chat">{t('common.dashboard')}</Link>
            </Button>
          ) : (
            <>
              <Button asChild variant="ghost" size="sm">
                <Link href="/login">{t('common.login')}</Link>
              </Button>
              <Button asChild size="sm">
                <Link href="/register">{t('common.register')}</Link>
              </Button>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
