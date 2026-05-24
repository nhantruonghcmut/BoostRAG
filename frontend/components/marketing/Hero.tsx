'use client';

import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { ArrowRight, Sparkles } from 'lucide-react';

import { Button } from '@/components/ui/button';

export function Hero() {
  const t = useTranslations('marketing.hero');
  return (
    <section className="relative overflow-hidden border-b">
      <div className="absolute inset-0 -z-10 bg-gradient-to-br from-primary/5 via-background to-background" />
      <div className="container py-24 sm:py-32">
        <div className="mx-auto flex max-w-3xl flex-col items-center text-center">
          <span className="mb-4 inline-flex items-center gap-2 rounded-full border bg-muted/40 px-3 py-1 text-xs text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5 text-primary" aria-hidden />
            BoostRAG · Phase 1 — Auth foundation
          </span>
          <h1 className="text-balance text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
            {t('title')}
          </h1>
          <p className="mt-6 max-w-2xl text-pretty text-lg text-muted-foreground sm:text-xl">
            {t('subtitle')}
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button asChild size="lg">
              <Link href="/register">
                {t('ctaPrimary')}
                <ArrowRight className="ml-1 h-4 w-4" aria-hidden />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/login">{t('ctaSecondary')}</Link>
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
