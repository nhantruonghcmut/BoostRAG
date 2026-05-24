'use client';

import Link from 'next/link';
import { useTranslations } from 'next-intl';

import { Button } from '@/components/ui/button';

export default function NotFound() {
  const t = useTranslations('common');
  return (
    <div className="container flex min-h-screen flex-col items-center justify-center gap-4 text-center">
      <h1 className="text-6xl font-bold">404</h1>
      <p className="text-muted-foreground">Page not found.</p>
      <Button asChild>
        <Link href="/">{t('back')}</Link>
      </Button>
    </div>
  );
}
