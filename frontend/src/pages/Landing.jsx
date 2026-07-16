import { Link } from 'react-router-dom'
import { useLang } from '../lib/i18n'

const ICONS = [
  <svg viewBox="0 0 24 24" fill="none" width="20" height="20" key="1">
    <path
      d="M3 17.5 9 11l4 4 8-8.5M21 6.5h-5m5 0v5"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>,
  <svg viewBox="0 0 24 24" fill="none" width="20" height="20" key="2">
    <path
      d="M12 3v3m0 12v3m9-9h-3M6 12H3m14.5-6.4-2.1 2.1M8.6 15.4l-2.1 2.1m0-11.9 2.1 2.1m6.8 6.8 2.1 2.1"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinecap="round"
    />
    <circle cx="12" cy="12" r="3.2" stroke="currentColor" strokeWidth="1.9" />
  </svg>,
  <svg viewBox="0 0 24 24" fill="none" width="20" height="20" key="3">
    <path
      d="M12 21s7.5-4.2 7.5-10V5.8L12 3 4.5 5.8V11c0 5.8 7.5 10 7.5 10Z"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinejoin="round"
    />
    <path
      d="m9 11.8 2 2 4-4.2"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>,
]

export default function Landing() {
  const { t } = useLang()

  return (
    <>
      <section className="hero">
        <div className="hero-orb a" />
        <div className="hero-orb b" />

        <div className="container">
          <div className="hero-inner">
            <span className="eyebrow">
              <b>{t('landing.badge')}</b> {t('landing.eyebrow')}
            </span>

            <h1 className="hero-title">
              {t('landing.title1')}
              <br />
              <em>{t('landing.titleEm')}</em> {t('landing.title2')}
            </h1>

            <p className="hero-sub">{t('landing.sub')}</p>

            <div className="hero-cta">
              <Link to="/chat" className="btn btn-primary">
                {t('landing.ctaPrimary')}
                {/* `.arrow` flips with the reading direction — see styles.css. */}
                <svg
                  className="arrow"
                  viewBox="0 0 24 24"
                  fill="none"
                  width="17"
                  height="17"
                  aria-hidden="true"
                >
                  <path
                    d="M5 12h13m-5.5-6 6 6-6 6"
                    stroke="currentColor"
                    strokeWidth="2.1"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </Link>
              <Link to="/dashboard" className="btn btn-ghost">
                {t('landing.ctaSecondary')}
              </Link>
            </div>

            <p className="hero-note">
              {t('landing.note')} <em>{t('landing.noteExample')}</em>
            </p>
          </div>
        </div>
      </section>

      <section className="features">
        <div className="container">
          <div className="feature-grid">
            {[1, 2, 3].map((n, i) => (
              <div className="feature" key={n}>
                <div className="feature-icon">{ICONS[i]}</div>
                <h3>{t(`landing.f${n}.title`)}</h3>
                <p>{t(`landing.f${n}.body`)}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}
