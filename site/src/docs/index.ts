import { createContext, useContext } from 'react'
import type { DocsContent } from './types'
import { ru } from './ru'
import { en } from './en'
import { es } from './es'
import { fr } from './fr'
import { ja } from './ja'
import { de } from './de'

export type Lang = 'ru' | 'en' | 'es' | 'fr' | 'ja' | 'de'

export const LANGS: { id: Lang; label: string; short: string }[] = [
  { id: 'ru', label: 'Русский', short: 'RU' },
  { id: 'en', label: 'English', short: 'EN' },
  { id: 'es', label: 'Español', short: 'ES' },
  { id: 'fr', label: 'Français', short: 'FR' },
  { id: 'ja', label: '日本語', short: 'JA' },
  { id: 'de', label: 'Deutsch', short: 'DE' },
]

const contents: Record<Lang, DocsContent> = { ru, en, es, fr, ja, de }

export function getContent(lang: Lang): DocsContent {
  return contents[lang] ?? en
}

const LANG_IDS: Lang[] = ['ru', 'en', 'es', 'fr', 'ja', 'de']

export function detectLang(): Lang {
  try {
    const saved = localStorage.getItem('dor-lang')
    if (LANG_IDS.includes(saved as Lang)) return saved as Lang
  } catch {
    /* noop */
  }
  const nav = (typeof navigator !== 'undefined' ? navigator.language : 'en').toLowerCase()
  const prefix = nav.slice(0, 2) as Lang
  return LANG_IDS.includes(prefix) ? prefix : 'en'
}

interface LangCtx {
  lang: Lang
  setLang: (l: Lang) => void
  t: DocsContent
}

export const LangContext = createContext<LangCtx>({
  lang: 'en',
  setLang: () => {},
  t: en,
})

export const useLang = () => useContext(LangContext)
