'use client';

import { useTransition } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { Globe } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { LOCALE_COOKIE, isLocale, locales, type Locale } from '@/lib/i18n/config';

interface LanguageSwitcherProps {
  className?: string;
}

export function LanguageSwitcher({ className }: LanguageSwitcherProps) {
  const t = useTranslations('common');
  const currentLocale = useLocale();
  const [isPending, startTransition] = useTransition();

  const setLocale = (next: Locale) => {
    if (next === currentLocale) return;
    document.cookie = `${LOCALE_COOKIE}=${next}; path=/; max-age=${60 * 60 * 24 * 365}; SameSite=Lax`;
    startTransition(() => {
      window.location.reload();
    });
  };

  return (
    <div className={className} role="group" aria-label={t('language')}>
      <div className="inline-flex items-center gap-1 rounded-md border border-input bg-background p-1 text-xs">
        <Globe className="ml-1 h-3.5 w-3.5 text-muted-foreground" aria-hidden />
        {locales.map((locale) => {
          if (!isLocale(locale)) return null;
          const active = locale === currentLocale;
          return (
            <Button
              key={locale}
              variant={active ? 'default' : 'ghost'}
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={() => setLocale(locale)}
              disabled={isPending}
              aria-pressed={active}
            >
              {locale.toUpperCase()}
            </Button>
          );
        })}
      </div>
    </div>
  );
}
