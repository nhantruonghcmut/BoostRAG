import Link from 'next/link';
import { Sparkles } from 'lucide-react';

import { LanguageSwitcher } from '@/components/common/LanguageSwitcher';

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-muted/30">
      <header className="container flex h-16 items-center justify-between">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <Sparkles className="h-5 w-5 text-primary" aria-hidden />
          <span>BoostRAG</span>
        </Link>
        <LanguageSwitcher />
      </header>
      <main className="container flex flex-1 items-center justify-center py-10">
        <div className="w-full max-w-md">{children}</div>
      </main>
    </div>
  );
}
