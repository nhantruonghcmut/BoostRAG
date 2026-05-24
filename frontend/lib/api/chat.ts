import { useAuthStore } from '@/lib/auth/store';
import type {
  ChatMessageListResponse,
  ChatSessionListResponse,
  ChatSessionRead,
  ChatStreamEvent,
  ChatStreamRequest,
  ChunkTraceRead,
} from '@/lib/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

async function authFetch(path: string, init?: RequestInit): Promise<Response> {
  const token = useAuthStore.getState().accessToken;
  const headers = new Headers(init?.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (!headers.has('Content-Type') && init?.body) {
    headers.set('Content-Type', 'application/json');
  }
  return fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: 'include',
    headers,
  });
}

function parseSseChunk(buffer: string): { events: ChatStreamEvent[]; rest: string } {
  const events: ChatStreamEvent[] = [];
  const parts = buffer.split('\n\n');
  const rest = parts.pop() ?? '';

  for (const part of parts) {
    if (!part.trim()) continue;
    let type = 'message';
    let dataStr = '';
    for (const line of part.split('\n')) {
      if (line.startsWith('event:')) type = line.slice(6).trim();
      if (line.startsWith('data:')) dataStr = line.slice(5).trim();
    }
    if (dataStr) {
      try {
        events.push({ type: type as ChatStreamEvent['type'], data: JSON.parse(dataStr) });
      } catch {
        // skip malformed
      }
    }
  }
  return { events, rest };
}

export const chatApi = {
  async createSession(title?: string): Promise<ChatSessionRead> {
    const resp = await authFetch('/chat/sessions', {
      method: 'POST',
      body: JSON.stringify({ title }),
    });
    if (!resp.ok) throw new Error('Failed to create session');
    return resp.json();
  },

  async listSessions(): Promise<ChatSessionListResponse> {
    const resp = await authFetch('/chat/sessions');
    if (!resp.ok) throw new Error('Failed to list sessions');
    return resp.json();
  },

  async getMessages(sessionId: string): Promise<ChatMessageListResponse> {
    const resp = await authFetch(`/chat/sessions/${sessionId}/messages`);
    if (!resp.ok) throw new Error('Failed to load messages');
    return resp.json();
  },

  async getTrace(messageId: string): Promise<ChunkTraceRead> {
    const resp = await authFetch(`/chat/messages/${messageId}/trace`);
    if (!resp.ok) throw new Error('Failed to load trace');
    return resp.json();
  },

  async stream(
    payload: ChatStreamRequest,
    onEvent: (event: ChatStreamEvent) => void,
    signal?: AbortSignal,
  ): Promise<void> {
    const resp = await authFetch('/chat/stream', {
      method: 'POST',
      body: JSON.stringify(payload),
      signal,
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => null);
      throw new Error(err?.error?.message || `Stream failed (${resp.status})`);
    }

    const reader = resp.body?.getReader();
    if (!reader) throw new Error('No response body');

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const { events, rest } = parseSseChunk(buffer);
      buffer = rest;
      for (const event of events) {
        onEvent(event);
      }
    }

    if (buffer.trim()) {
      const { events } = parseSseChunk(`${buffer}\n\n`);
      for (const event of events) {
        onEvent(event);
      }
    }
  },
};
