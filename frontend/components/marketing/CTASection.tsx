'use client';

import Link from 'next/link';
import { useTranslations } from 'next-intl';

import { Button } from '@/components/ui/button';

export function CTASection() {
  const t = useTranslations('marketing.cta');
  return (
    <section className="border-t bg-muted/30">
      <div className="container flex flex-col items-center gap-4 py-20 text-center">
        <h2 className="text-balance text-3xl font-bold tracking-tight sm:text-4xl">{t('title')}</h2>
        <p className="max-w-xl text-muted-foreground">{t('subtitle')}</p>
        <Button asChild size="lg" className="mt-2">
          <Link href="/register">{t('button')}</Link>
        </Button>
      </div>
    </section>
  );
}
