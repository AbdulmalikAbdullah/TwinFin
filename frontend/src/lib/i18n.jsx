import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { LANGS, isRtl, tr } from './strings'

/**
 * Language + direction for the whole app.
 *
 * Setting `dir` on <html> is what actually flips the layout: the CSS is written with
 * logical properties (inset-inline, margin-inline, text-align: end), so the entire page
 * mirrors from that one attribute rather than from a parallel set of RTL rules.
 */

const STORAGE_KEY = 'twin.lang'
const LangContext = createContext(null)

function initialLang() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved && LANGS.includes(saved)) return saved
  } catch {
    // Private mode / storage disabled — fall through to the browser's preference.
  }
  const browser = (navigator.language || 'en').slice(0, 2)
  return LANGS.includes(browser) ? browser : 'en'
}

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(initialLang)
  const rtl = isRtl(lang)

  useEffect(() => {
    const root = document.documentElement
    root.lang = lang
    root.dir = rtl ? 'rtl' : 'ltr'
    try {
      localStorage.setItem(STORAGE_KEY, lang)
    } catch {
      // Not being able to remember the choice is not a reason to break the page.
    }
  }, [lang, rtl])

  const t = useCallback((key, vars) => tr(lang, key, vars), [lang])
  const toggle = useCallback(() => setLang((l) => (l === 'ar' ? 'en' : 'ar')), [])

  const value = useMemo(() => ({ lang, rtl, t, setLang, toggle }), [lang, rtl, t, toggle])

  return <LangContext.Provider value={value}>{children}</LangContext.Provider>
}

export function useLang() {
  const ctx = useContext(LangContext)
  if (!ctx) throw new Error('useLang must be used inside <LanguageProvider>')
  return ctx
}
