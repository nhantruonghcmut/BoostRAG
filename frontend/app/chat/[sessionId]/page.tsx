'use client';

import { ChatPanel } from '@/components/chat/ChatPanel';
import { SessionSidebar } from '@/components/chat/SessionSidebar';

interface SessionChatPageProps {
  params: { sessionId: string };
}

export default function SessionChatPage({ params }: SessionChatPageProps) {
  return (
    <>
      <SessionSidebar activeSessionId={params.sessionId} />
      <main className="flex min-w-0 flex-1 flex-col">
        <ChatPanel sessionId={params.sessionId} />
      </main>
    </>
  );
}
