import { getRequestConfig } from 'next-intl/server';
import { cookies, headers } from 'next/headers';

import { LOCALE_COOKIE, defaultLocale, isLocale, type Locale } from './config';

function detectLocale(): Locale {
  const cookieStore = cookies();
  const cookieLocale = cookieStore.get(LOCALE_COOKIE)?.value;
  if (cookieLocale && isLocale(cookieLocale)) return cookieLocale;

  const accept = headers().get('accept-language') ?? '';
  for (const part of accept.split(',')) {
    const tag = part.trim().split(';')[0]?.toLowerCase().slice(0, 2);
    if (tag && isLocale(tag)) return tag;
  }
  return defaultLocale;
}

export default getRequestConfig(async () => {
  const locale = detectLocale();
  const messages = (await import(`../../messages/${locale}.json`)).default;
  return { locale, messages };
});
