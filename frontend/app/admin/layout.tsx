'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { ArrowLeft, FileText, LayoutDashboard } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/lib/auth/store';
import { useCurrentUser } from '@/lib/auth/useAuth';
import { cn } from '@/lib/utils/cn';

const NAV_ITEMS = [
  { href: '/admin', icon: LayoutDashboard, labelKey: 'admin.nav.dashboard' as const },
  { href: '/admin/documents', icon: FileText, labelKey: 'admin.nav.documents' as const },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const t = useTranslations();
  const pathname = usePathname();
  const router = useRouter();
  const accessToken = useAuthStore((s) => s.accessToken);
  const { data: user, isLoading } = useCurrentUser();

  useEffect(() => {
    if (!accessToken) {
      router.replace('/login');
    } else if (!isLoading && user && user.role !== 'admin') {
      router.replace('/chat');
    }
  }, [accessToken, isLoading, router, user]);

  if (!accessToken || (isLoading && !user)) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        {t('common.loading')}
      </div>
    );
  }

  if (user && user.role !== 'admin') {
    return null;
  }

  return (
    <div className="min-h-screen bg-muted/30">
      <header className="border-b bg-background">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-3">
            <Button asChild variant="ghost" size="sm">
              <Link href="/">
                <ArrowLeft className="h-4 w-4" aria-hidden />
                {t('common.back')}
              </Link>
            </Button>
            <span className="font-semibold">{t('admin.title')}</span>
          </div>
          {user && <span className="text-sm text-muted-foreground">{user.email}</span>}
        </div>
      </header>

      <div className="container flex gap-8 py-8">
        <aside className="hidden w-56 shrink-0 md:block">
          <nav className="space-y-1">
            {NAV_ITEMS.map(({ href, icon: Icon, labelKey }) => {
              const active = pathname === href || (href !== '/admin' && pathname.startsWith(href));
              return (
                <Link
                  key={href}
                  href={href}
                  className={cn(
                    'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                    active
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                  )}
                >
                  <Icon className="h-4 w-4" aria-hidden />
                  {t(labelKey)}
                </Link>
              );
            })}
          </nav>
        </aside>

        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
