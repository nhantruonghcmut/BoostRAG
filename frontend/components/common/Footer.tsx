'use client';

import { useTranslations } from 'next-intl';

export function Footer() {
  const t = useTranslations('marketing.footer');
  return (
    <footer className="border-t bg-muted/40">
      <div className="container flex flex-col gap-2 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <p>{t('tagline')}</p>
        <p>{t('rights')}</p>
      </div>
    </footer>
  );
}
