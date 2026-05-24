'use client';

import { useTranslations } from 'next-intl';

import { DocumentTable } from '@/components/admin/DocumentTable';
import { DocumentUploader } from '@/components/admin/DocumentUploader';

export default function AdminDocumentsPage() {
  const t = useTranslations('admin.documents');

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-semibold">{t('pageTitle')}</h1>
        <p className="mt-2 text-muted-foreground">{t('pageDescription')}</p>
      </div>

      <DocumentUploader />
      <DocumentTable />
    </div>
  );
}
