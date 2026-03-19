import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { translations, localeNames } from './translations';
import type { Locale, Translations } from './translations';

type I18nCtx = {
  locale: Locale;
  t: Translations;
  setLocale: (l: Locale) => void;
  localeNames: Record<Locale, string>;
};

const STORAGE_KEY = 'paperflow_locale';

function detectLocale(): Locale {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored && stored in translations) return stored as Locale;
  const nav = navigator.language?.toLowerCase() ?? '';
  if (nav.startsWith('es')) return 'es';
  if (nav.startsWith('pt')) return 'pt';
  return 'en';
}

const I18nContext = createContext<I18nCtx>({
  locale: 'en',
  t: translations.en,
  setLocale: () => {},
  localeNames,
});

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(detectLocale);

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    localStorage.setItem(STORAGE_KEY, l);
    document.documentElement.lang = l;
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  return (
    <I18nContext.Provider value={{ locale, t: translations[locale], setLocale, localeNames }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  return useContext(I18nContext);
}

export { localeNames };
export type { Locale, Translations };
