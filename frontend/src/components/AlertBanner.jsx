import { useLang } from '../lib/i18n'

/**
 * The "Twin protects you" moment.
 *
 * DANGER is loud and pulses   it means the purchase breaks the emergency fund or guts
 * cash flow. INFO is calm and green: an explicit all-clear, so the user always gets a
 * verdict rather than silence. The message itself is written (and localised) by the
 * engine; only the heading lives in the UI.
 */

function WarnIcon() {
  return (
    <svg className="alert-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M12 8.5v4.2M12 16.2h.01M10.3 3.9 2.6 17.3a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg className="alert-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9.2" stroke="currentColor" strokeWidth="1.9" />
      <path
        d="m8.3 12.2 2.5 2.5 4.9-5.3"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

const ICON = { danger: WarnIcon, warning: WarnIcon, info: CheckIcon }

export default function AlertBanner({ alert }) {
  const { t } = useLang()
  if (!alert) return null

  const level = ICON[alert.level] ? alert.level : 'info'
  const Icon = ICON[level]

  return (
    <div
      className={`alert alert-${level}`}
      role={level === 'danger' ? 'alert' : 'status'}
    >
      <Icon />
      <div className="alert-body">
        <div className="alert-title">{t(`alert.${level}`)}</div>
        <div className="alert-msg">{alert.message}</div>
      </div>
    </div>
  )
}
