'use client';

import { useTranslations } from 'next-intl';
import {
  ShieldCheck,
  Layers,
  Network,
  Wrench,
  Microscope,
  Globe2,
  type LucideIcon,
} from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface Feature {
  key: 'adminPortal' | 'multiLLM' | 'acl' | 'functionCalling' | 'debug' | 'i18n';
  icon: LucideIcon;
}

const FEATURES: Feature[] = [
  { key: 'adminPortal', icon: ShieldCheck },
  { key: 'multiLLM', icon: Layers },
  { key: 'acl', icon: Network },
  { key: 'functionCalling', icon: Wrench },
  { key: 'debug', icon: Microscope },
  { key: 'i18n', icon: Globe2 },
];

export function FeatureGrid() {
  const t = useTranslations('marketing.features');
  return (
    <section className="container py-20">
      <div className="mx-auto mb-12 max-w-2xl text-center">
        <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">{t('title')}</h2>
        <p className="mt-4 text-muted-foreground">{t('subtitle')}</p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map(({ key, icon: Icon }) => (
          <Card key={key} className="transition-shadow hover:shadow-md">
            <CardHeader>
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary">
                <Icon className="h-5 w-5" aria-hidden />
              </div>
              <CardTitle className="text-lg">{t(`${key}.title`)}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">{t(`${key}.desc`)}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}
