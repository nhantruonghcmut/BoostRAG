'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Bug } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { CitationLink, SimpleMarkdown } from '@/components/chat/CitationLink';
import { StreamingText } from '@/components/chat/StreamingText';
import { ChunkDebugDrawer } from '@/components/chat/ChunkDebugDrawer';
import type { Citation } from '@/lib/types/api';
import { cn } from '@/lib/utils/cn';

interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  isStreaming?: boolean;
  messageId?: string;
  showDebug?: boolean;
}

export function MessageBubble({
  role,
  content,
  citations,
  isStreaming,
  messageId,
  showDebug,
}: MessageBubbleProps) {
  const t = useTranslations('chat');
  const [debugOpen, setDebugOpen] = useState(false);
  const isUser = role === 'user';

  return (
    <div className={cn('flex w-full', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[85%] rounded-2xl px-4 py-3',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted',
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm">{content}</p>
        ) : (
          <div className="text-sm">
            {isStreaming ? (
              <StreamingText text={content} isStreaming />
            ) : (
              <SimpleMarkdown content={content} />
            )}
            {citations && citations.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1 border-t border-border/50 pt-2">
                {citations.map((c) => (
                  <CitationLink key={c.citation_id} citationId={c.citation_id} />
                ))}
              </div>
            )}
          </div>
        )}

        {!isUser && messageId && showDebug && !isStreaming && (
          <div className="mt-2 border-t border-border/50 pt-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 gap-1 px-2 text-xs"
              onClick={() => setDebugOpen(true)}
            >
              <Bug className="h-3.5 w-3.5" aria-hidden />
              {t('debug')}
            </Button>
          </div>
        )}
      </div>

      {debugOpen && messageId && (
        <ChunkDebugDrawer messageId={messageId} onClose={() => setDebugOpen(false)} />
      )}
    </div>
  );
}
