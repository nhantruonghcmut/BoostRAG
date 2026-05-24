'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { Loader2, Pencil, RefreshCw, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

import { AclEditDialog } from '@/components/admin/AclEditDialog';
import { DOCUMENTS_QUERY_KEY } from '@/components/admin/DocumentUploader';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { documentsApi } from '@/lib/api/documents';
import type { DocumentStatus, DocumentSummary } from '@/lib/types/api';
import {
  ApiError,
  isProcessingDocumentStatus,
  normalizeDocumentStatus,
} from '@/lib/types/api';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** index;
  return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatDate(value: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function statusBadgeVariant(status: DocumentStatus): 'secondary' | 'info' | 'success' | 'destructive' {
  switch (status) {
    case 'READY':
      return 'success';
    case 'FAILED':
      return 'destructive';
    case 'PENDING':
      return 'secondary';
    default:
      return 'info';
  }
}

export function DocumentTable() {
  const t = useTranslations('admin.documents');
  const qc = useQueryClient();
  const [editingDocument, setEditingDocument] = useState<DocumentSummary | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: DOCUMENTS_QUERY_KEY,
    queryFn: async () => {
      const response = await documentsApi.listDocuments();
      return {
        ...response,
        items: response.items.map((item) => ({
          ...item,
          status: normalizeDocumentStatus(item.status),
        })),
      };
    },
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? [];
      const hasProcessing = items.some((doc) => isProcessingDocumentStatus(doc.status));
      return hasProcessing ? 3000 : false;
    },
  });

  const documents = useMemo(() => data?.items ?? [], [data?.items]);

  const deleteDocument = useMutation({
    mutationFn: documentsApi.deleteDocument,
    onSuccess: () => {
      toast.success(t('delete.success'));
      qc.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY });
    },
    onError: (error: unknown) => {
      const message = error instanceof ApiError ? error.message : t('delete.error');
      toast.error(message);
    },
  });

  const reindexDocument = useMutation({
    mutationFn: documentsApi.reindexDocument,
    onSuccess: () => {
      toast.success(t('reindex.success'));
      qc.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY });
    },
    onError: (error: unknown) => {
      const message = error instanceof ApiError ? error.message : t('reindex.error');
      toast.error(message);
    },
  });

  const onDelete = (doc: DocumentSummary) => {
    if (!window.confirm(t('delete.confirm', { name: doc.name }))) return;
    deleteDocument.mutate(doc.document_id);
  };

  const onReindex = (doc: DocumentSummary) => {
    reindexDocument.mutate(doc.document_id);
  };

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle>{t('table.title')}</CardTitle>
            <CardDescription>
              {data ? t('table.total', { count: data.total }) : t('table.loading')}
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
            <RefreshCw className={isLoading ? 'h-4 w-4 animate-spin' : 'h-4 w-4'} aria-hidden />
            {t('table.refresh')}
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center gap-2 py-12 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" aria-hidden />
              {t('table.loading')}
            </div>
          ) : isError ? (
            <p className="py-8 text-center text-destructive">{t('table.error')}</p>
          ) : documents.length === 0 ? (
            <p className="py-8 text-center text-muted-foreground">{t('table.empty')}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-3 pr-4 font-medium">{t('table.columns.name')}</th>
                    <th className="pb-3 pr-4 font-medium">{t('table.columns.status')}</th>
                    <th className="pb-3 pr-4 font-medium">{t('table.columns.size')}</th>
                    <th className="pb-3 pr-4 font-medium">{t('table.columns.level')}</th>
                    <th className="pb-3 pr-4 font-medium">{t('table.columns.groups')}</th>
                    <th className="pb-3 font-medium">{t('table.columns.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((doc) => (
                    <tr key={doc.document_id} className="border-b last:border-0">
                      <td className="py-3 pr-4">
                        <div className="font-medium">{doc.name}</div>
                        <div className="text-xs text-muted-foreground">{formatDate(doc.uploaded_at)}</div>
                      </td>
                      <td className="py-3 pr-4">
                        <Badge
                          variant={statusBadgeVariant(doc.status)}
                          className={isProcessingDocumentStatus(doc.status) ? 'animate-pulse' : undefined}
                        >
                          {t(`status.${doc.status}`)}
                        </Badge>
                      </td>
                      <td className="py-3 pr-4">{formatBytes(doc.size_bytes)}</td>
                      <td className="py-3 pr-4">{doc.required_level}</td>
                      <td className="py-3 pr-4">
                        {doc.allowed_groups.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {doc.allowed_groups.map((group) => (
                              <Badge key={group} variant="outline">
                                {group}
                              </Badge>
                            ))}
                          </div>
                        ) : (
                          <span className="text-muted-foreground">{t('table.noGroups')}</span>
                        )}
                      </td>
                      <td className="py-3">
                        <div className="flex flex-wrap gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setEditingDocument(doc)}
                            aria-label={t('actions.editAcl')}
                          >
                            <Pencil className="h-4 w-4" aria-hidden />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => onReindex(doc)}
                            disabled={reindexDocument.isPending}
                            aria-label={t('actions.reindex')}
                          >
                            <RefreshCw className="h-4 w-4" aria-hidden />
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => onDelete(doc)}
                            disabled={deleteDocument.isPending}
                            aria-label={t('actions.delete')}
                          >
                            <Trash2 className="h-4 w-4" aria-hidden />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <AclEditDialog
        document={editingDocument}
        open={editingDocument !== null}
        onOpenChange={(open) => {
          if (!open) setEditingDocument(null);
        }}
      />
    </>
  );
}
