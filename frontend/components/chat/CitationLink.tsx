'use client';

import { useState } from 'react';

import type { ChunkTraceChunk } from '@/lib/types/api';

interface CitationLinkProps {
  citationId: number;
  chunk?: ChunkTraceChunk;
  onClick?: () => void;
}

export function CitationLink({ citationId, onClick }: CitationLinkProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mx-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded bg-primary/15 px-1 text-xs font-medium text-primary hover:bg-primary/25"
      aria-label={`Citation ${citationId}`}
    >
      [{citationId}]
    </button>
  );
}

interface CitationPreviewProps {
  chunk: ChunkTraceChunk;
  onClose: () => void;
}

export function CitationPreview({ chunk, onClose }: CitationPreviewProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="max-h-[80vh] w-full max-w-lg overflow-auto rounded-lg border bg-background p-4 shadow-lg">
        <div className="mb-2 flex items-start justify-between gap-2">
          <div>
            <p className="font-medium">{chunk.document_name}</p>
            {chunk.page_number != null && (
              <p className="text-xs text-muted-foreground">Page {chunk.page_number}</p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            ✕
          </button>
        </div>
        <p className="whitespace-pre-wrap text-sm">{chunk.text}</p>
      </div>
    </div>
  );
}

/** Simple markdown-ish: paragraphs + inline code */
export function SimpleMarkdown({ content }: { content: string }) {
  const lines = content.split('\n');
  return (
    <div className="space-y-2 text-sm leading-relaxed">
      {lines.map((line, i) => {
        if (!line.trim()) return <br key={i} />;
        const formatted = line.split(/(`[^`]+`)/g).map((seg, j) => {
          if (seg.startsWith('`') && seg.endsWith('`')) {
            return (
              <code key={j} className="rounded bg-muted px-1 py-0.5 font-mono text-xs">
                {seg.slice(1, -1)}
              </code>
            );
          }
          return <span key={j}>{seg}</span>;
        });
        return <p key={i}>{formatted}</p>;
      })}
    </div>
  );
}
