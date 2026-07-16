/**
 * Number formatting. Every riyal figure in the UI goes through here.
 *
 * Arabic keeps Latin digits (120,000) and swaps only the currency word — which is what
 * Saudi banking apps do, and which keeps the figures verifiable against the English view
 * at a glance.
 */

const CURRENCY = { en: 'SAR', ar: 'ريال' }

export const sar = (n, lang = 'en') =>
  typeof n === 'number'
    ? `${Math.round(n).toLocaleString('en-US')} ${CURRENCY[lang] ?? CURRENCY.en}`
    : '—'

/** Compact form for chart axes, where "343,600 SAR" would not fit. */
export const sarShort = (n) => {
  if (typeof n !== 'number') return '—'
  const abs = Math.abs(n)
  if (abs >= 1000) return `${(n / 1000).toFixed(abs >= 10000 ? 0 : 1)}k`
  return `${Math.round(n)}`
}

export const CHART = {
  savings: '#D8653B',
  income: '#8685D8',
  expenses: '#212145',
  floor: '#C8393A',
}
