'use client';

import { useTranslations } from 'next-intl';
import { Plus, MessageSquare } from 'lucide-react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import { chatApi } from '@/lib/api/chat';
import { cn } from '@/lib/utils/cn';

interface SessionSidebarProps {
  activeSessionId?: string;
}

export function SessionSidebar({ activeSessionId }: SessionSidebarProps) {
  const t = useTranslations('chat');

  const { data, isLoading } = useQuery({
    queryKey: ['chat', 'sessions'],
    queryFn: () => chatApi.listSessions(),
  });

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r bg-muted/20">
      <div className="border-b p-3">
        <Button asChild className="w-full justify-start gap-2" variant="outline">
          <Link href="/chat">
            <Plus className="h-4 w-4" aria-hidden />
            {t('newChat')}
          </Link>
        </Button>
      </div>

      <nav className="flex-1 overflow-y-auto p-2">
        {isLoading && (
          <p className="px-2 py-4 text-sm text-muted-foreground">{t('loadingSessions')}</p>
        )}
        {!isLoading && data?.items.length === 0 && (
          <p className="px-2 py-4 text-sm text-muted-foreground">{t('noSessions')}</p>
        )}
        {data?.items.map((session) => {
          const active = session.session_id === activeSessionId;
          return (
            <Link
              key={session.session_id}
              href={`/chat/${session.session_id}`}
              className={cn(
                'mb-1 flex items-start gap-2 rounded-md px-3 py-2 text-sm transition-colors',
                active
                  ? 'bg-primary/10 font-medium text-primary'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
              )}
            >
              <MessageSquare className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
              <span className="line-clamp-2">{session.title}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
