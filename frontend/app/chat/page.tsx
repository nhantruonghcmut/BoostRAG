'use client';

import { useRouter } from 'next/navigation';

import { ChatPanel } from '@/components/chat/ChatPanel';
import { SessionSidebar } from '@/components/chat/SessionSidebar';

export default function NewChatPage() {
  const router = useRouter();

  return (
    <>
      <SessionSidebar />
      <main className="flex min-w-0 flex-1 flex-col">
        <ChatPanel
          onSessionCreated={(sessionId) => {
            router.replace(`/chat/${sessionId}`);
          }}
        />
      </main>
    </>
  );
}
