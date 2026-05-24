'use client';

import { useTranslations } from 'next-intl';
import { X } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import { chatApi } from '@/lib/api/chat';

interface ChunkDebugDrawerProps {
  messageId: string;
  onClose: () => void;
}

export function ChunkDebugDrawer({ messageId, onClose }: ChunkDebugDrawerProps) {
  const t = useTranslations('chat');

  const { data, isLoading, error } = useQuery({
    queryKey: ['chat', 'trace', messageId],
    queryFn: () => chatApi.getTrace(messageId),
  });

  return (
    <div className="fixed inset-y-0 right-0 z-40 flex w-full max-w-md flex-col border-l bg-background shadow-xl">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <h2 className="font-semibold">{t('debugTitle')}</h2>
        <Button type="button" variant="ghost" size="icon" onClick={onClose} aria-label="Close">
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {isLoading && <p className="text-sm text-muted-foreground">{t('loadingTrace')}</p>}
        {error && <p className="text-sm text-destructive">{t('traceError')}</p>}
        {data && (
          <div className="space-y-4">
            <div className="rounded-md bg-muted/50 p-3 text-xs">
              <p>
                <span className="font-medium">{t('query')}:</span> {data.query}
              </p>
              <p className="mt-1 text-muted-foreground">
                {data.embedding_model} · {data.llm_model} · {data.latency_ms}ms
              </p>
            </div>

            <section>
              <h3 className="mb-2 text-sm font-medium">{t('usedChunks')}</h3>
              <div className="space-y-3">
                {data.used_chunks.map((chunk) => (
                  <div key={chunk.chunk_id} className="rounded-md border p-3 text-xs">
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <span className="font-medium">
                        [{chunk.citation_id}] {chunk.document_name}
                      </span>
                      <span className="shrink-0 text-muted-foreground">
                        v:{chunk.vector_score?.toFixed(3)} r:
                        {chunk.rerank_score?.toFixed(3) ?? '—'}
                      </span>
                    </div>
                    {chunk.page_number != null && (
                      <p className="text-muted-foreground">
                        {t('page')} {chunk.page_number}
                        {chunk.heading_context ? ` · ${chunk.heading_context}` : ''}
                      </p>
                    )}
                    <p className="mt-2 line-clamp-4 whitespace-pre-wrap">{chunk.text}</p>
                  </div>
                ))}
              </div>
            </section>

            {data.retrieved_chunks.length > data.used_chunks.length && (
              <section>
                <h3 className="mb-2 text-sm font-medium">{t('retrievedChunks')}</h3>
                <p className="text-xs text-muted-foreground">
                  {t('retrievedCount', {
                    retrieved: data.retrieved_chunks.length,
                    used: data.used_chunks.length,
                  })}
                </p>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
