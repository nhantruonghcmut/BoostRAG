import { getTranslations } from 'next-intl/server';

import { RegisterForm } from '@/components/auth/RegisterForm';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export async function generateMetadata() {
  const t = await getTranslations('auth.register');
  return { title: t('title') };
}

export default async function RegisterPage() {
  const t = await getTranslations('auth.register');
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('title')}</CardTitle>
        <CardDescription>{t('subtitle')}</CardDescription>
      </CardHeader>
      <CardContent>
        <RegisterForm />
      </CardContent>
    </Card>
  );
}
