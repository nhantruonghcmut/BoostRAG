'use client';

import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Send, Square } from 'lucide-react';

import { MessageBubble } from '@/components/chat/MessageBubble';
import { Button } from '@/components/ui/button';
import { useChatStream, type ChatMessageState } from '@/lib/chat/useChatStream';
import { chatApi } from '@/lib/api/chat';

interface ChatPanelProps {
  sessionId?: string;
  onSessionCreated?: (sessionId: string) => void;
}

export function ChatPanel({ sessionId, onSessionCreated }: ChatPanelProps) {
  const t = useTranslations('chat');
  const [input, setInput] = useState('');
  const [includeDebug, setIncludeDebug] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  const { messages, isStreaming, error, sendMessage, loadHistory, stopStreaming } =
    useChatStream({
      sessionId,
      onSessionCreated,
    });

  useEffect(() => {
    if (!sessionId) {
      loadHistory([]);
      return;
    }
    chatApi
      .getMessages(sessionId)
      .then((resp) => {
        const items: ChatMessageState[] = resp.items.map((m) => ({
          id: m.message_id,
          role: m.role,
          content: m.content,
          citations: m.citations ?? undefined,
          messageId: m.role === 'assistant' ? m.message_id : undefined,
        }));
        loadHistory(items);
      })
      .catch(() => loadHistory([]));
  }, [sessionId, loadHistory]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    void sendMessage(input, includeDebug);
    setInput('');
  };

  return (
    <div className="flex h-full flex-1 flex-col">
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center text-muted-foreground">
            <p className="text-lg font-medium">{t('emptyTitle')}</p>
            <p className="mt-1 max-w-md text-sm">{t('emptyHint')}</p>
          </div>
        )}
        <div className="mx-auto flex max-w-3xl flex-col gap-4">
          {messages.map((msg) => (
            <MessageBubble
              key={msg.id}
              role={msg.role}
              content={msg.content}
              citations={msg.citations}
              isStreaming={msg.isStreaming}
              messageId={msg.messageId}
              showDebug={includeDebug}
            />
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      {error && (
        <p className="px-4 pb-2 text-center text-sm text-destructive">{error}</p>
      )}

      <form
        onSubmit={handleSubmit}
        className="border-t bg-background px-4 py-4"
      >
        <div className="mx-auto flex max-w-3xl flex-col gap-2">
          <label className="flex items-center gap-2 text-xs text-muted-foreground">
            <input
              type="checkbox"
              checked={includeDebug}
              onChange={(e) => setIncludeDebug(e.target.checked)}
              className="rounded"
            />
            {t('enableDebug')}
          </label>
          <div className="flex gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={t('inputPlaceholder')}
              rows={2}
              disabled={isStreaming}
              className="flex-1 resize-none rounded-lg border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
            />
            {isStreaming ? (
              <Button type="button" variant="outline" size="icon" onClick={stopStreaming}>
                <Square className="h-4 w-4" aria-hidden />
              </Button>
            ) : (
              <Button type="submit" size="icon" disabled={!input.trim()}>
                <Send className="h-4 w-4" aria-hidden />
              </Button>
            )}
          </div>
        </div>
      </form>
    </div>
  );
}
