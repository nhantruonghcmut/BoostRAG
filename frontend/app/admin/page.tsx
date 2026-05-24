'use client';

import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { FileText, ShieldCheck } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function AdminDashboardPage() {
  const t = useTranslations('admin');

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-center gap-3">
          <ShieldCheck className="h-8 w-8 text-primary" aria-hidden />
          <h1 className="text-3xl font-semibold">{t('dashboard.title')}</h1>
        </div>
        <p className="mt-2 text-muted-foreground">{t('dashboard.subtitle')}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" aria-hidden />
              {t('dashboard.documentsCard.title')}
            </CardTitle>
            <CardDescription>{t('dashboard.documentsCard.description')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link href="/admin/documents">{t('dashboard.documentsCard.action')}</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
