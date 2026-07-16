import { useEffect, useState } from 'react'
import { useLang } from '../lib/i18n'

/**
 * Animated Financial Health Score gauge (0–100).
 *
 * The score, its band label and its four component names are all computed and localised in
 * Python — this only draws them. The arc animates from 0 on mount so the number lands
 * rather than just appearing, and the stroke colour tracks the band.
 */

const BAND = (score) => {
  if (score >= 85) return '#1F8A5F'
  if (score >= 70) return '#8685D8'
  if (score >= 50) return '#D8653B'
  return '#C8393A'
}

const RADIUS = 46
const CIRCUM = 2 * Math.PI * RADIUS

export default function HealthGauge({ health }) {
  const { t } = useLang()
  const target = health?.score ?? 0
  const [shown, setShown] = useState(0)

  // Count the number up in step with the arc sweep. Both take ~1.4s.
  useEffect(() => {
    if (!health) return
    let frame
    const start = performance.now()
    const DURATION = 1400

    const tick = (now) => {
      const t = Math.min(1, (now - start) / DURATION)
      // Same easing curve as the CSS transition on the arc, so they stay in sync.
      const eased = 1 - Math.pow(1 - t, 3)
      setShown(target * eased)
      if (t < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [target, health])

  if (!health) {
    return (
      <div className="gauge-card">
        <div className="skeleton" style={{ width: 108, height: 108, borderRadius: '50%' }} />
        <div className="gauge-detail">
          <div className="skeleton" style={{ height: 12, width: 90, marginBottom: 10 }} />
          <div className="skeleton" style={{ height: 20, width: 130 }} />
        </div>
      </div>
    )
  }

  const offset = CIRCUM * (1 - target / 100)

  return (
    <div className="gauge-card">
      <div className="gauge">
        <svg viewBox="0 0 108 108" width="108" height="108" aria-hidden="true">
          <circle className="gauge-track" cx="54" cy="54" r={RADIUS} />
          <circle
            className="gauge-fill"
            cx="54"
            cy="54"
            r={RADIUS}
            stroke={BAND(target)}
            strokeDasharray={CIRCUM}
            strokeDashoffset={offset}
          />
        </svg>
        {/* "85/100" is a numeric expression — keep it LTR in either direction. */}
        <bdi className="gauge-num num">
          {Math.round(shown)}
          <span>/100</span>
        </bdi>
      </div>

      <div className="gauge-detail">
        <div className="stat-label">{t('dash.health')}</div>
        <div className="gauge-verdict">{health.label}</div>
        <div className="gauge-bars">
          {health.components.map((c) => (
            <div className="gauge-bar-row" key={c.name}>
              <span className="name">{c.name}</span>
              <bdi className="pts">
                {c.points}/{c.max_points}
              </bdi>
              <span className="gauge-bar">
                <i style={{ width: `${(c.points / c.max_points) * 100}%` }} />
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
