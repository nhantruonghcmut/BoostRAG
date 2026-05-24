'use client';

import { useCallback, useRef, useState } from 'react';

import { chatApi } from '@/lib/api/chat';
import type { ChatStreamEvent, Citation } from '@/lib/types/api';

export interface ChatMessageState {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  isStreaming?: boolean;
  messageId?: string;
}

interface UseChatStreamOptions {
  sessionId?: string;
  onSessionCreated?: (sessionId: string) => void;
}

export function useChatStream({ sessionId, onSessionCreated }: UseChatStreamOptions) {
  const [messages, setMessages] = useState<ChatMessageState[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (query: string, includeDebug = false) => {
      if (!query.trim() || isStreaming) return;

      setError(null);
      const userMsg: ChatMessageState = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: query.trim(),
      };
      const assistantMsg: ChatMessageState = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: '',
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await chatApi.stream(
          { session_id: sessionId, query: query.trim(), include_debug: includeDebug },
          (event: ChatStreamEvent) => {
            if (event.type === 'start') {
              const data = event.data as { session_id?: string };
              if (data.session_id && onSessionCreated) {
                onSessionCreated(data.session_id);
              }
            }

            if (event.type === 'token') {
              const data = event.data as { text?: string };
              if (data.text) {
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last?.role === 'assistant') {
                    updated[updated.length - 1] = {
                      ...last,
                      content: last.content + data.text,
                    };
                  }
                  return updated;
                });
              }
            }

            if (event.type === 'citations') {
              const raw = event.data as unknown;
              const citations = (Array.isArray(raw) ? raw : []) as Citation[];
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last?.role === 'assistant') {
                  updated[updated.length - 1] = { ...last, citations };
                }
                return updated;
              });
            }

            if (event.type === 'done') {
              const data = event.data as { message_id?: string };
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last?.role === 'assistant') {
                  updated[updated.length - 1] = {
                    ...last,
                    isStreaming: false,
                    messageId: data.message_id,
                  };
                }
                return updated;
              });
            }

            if (event.type === 'error') {
              const data = event.data as { message?: string };
              setError(data.message || 'Stream error');
            }
          },
          controller.signal,
        );
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          setError((err as Error).message || 'Failed to send message');
        }
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.role === 'assistant' && last.isStreaming) {
            updated[updated.length - 1] = {
              ...last,
              isStreaming: false,
              content: last.content || '…',
            };
          }
          return updated;
        });
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [isStreaming, onSessionCreated, sessionId],
  );

  const loadHistory = useCallback((items: ChatMessageState[]) => {
    setMessages(items);
  }, []);

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return {
    messages,
    isStreaming,
    error,
    sendMessage,
    loadHistory,
    stopStreaming,
  };
}
