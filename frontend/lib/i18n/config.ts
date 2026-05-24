export const locales = ['vi', 'en'] as const;
export type Locale = (typeof locales)[number];

export const defaultLocale: Locale = 'vi';

export const localeNames: Record<Locale, string> = {
  vi: 'Tiếng Việt',
  en: 'English',
};

export const isLocale = (value: string): value is Locale =>
  (locales as readonly string[]).includes(value);

export const LOCALE_COOKIE = 'BOOSTRAG_LOCALE';
