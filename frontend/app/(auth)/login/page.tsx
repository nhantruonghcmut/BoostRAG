import { getTranslations } from 'next-intl/server';

import { LoginForm } from '@/components/auth/LoginForm';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export async function generateMetadata() {
  const t = await getTranslations('auth.login');
  return { title: t('title') };
}

export default async function LoginPage() {
  const t = await getTranslations('auth.login');
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('title')}</CardTitle>
        <CardDescription>{t('subtitle')}</CardDescription>
      </CardHeader>
      <CardContent>
        <LoginForm />
      </CardContent>
    </Card>
  );
}
