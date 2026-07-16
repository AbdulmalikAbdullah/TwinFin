import { NavLink, Route, Routes } from 'react-router-dom'
import Chat from './pages/Chat'
import Dashboard from './pages/Dashboard'
import Landing from './pages/Landing'
import { useLang } from './lib/i18n'

function LangToggle() {
  const { t, toggle } = useLang()
  return (
    <button
      className="lang-toggle"
      onClick={toggle}
      aria-label={t('nav.switchLangAria')}
      title={t('nav.switchLangAria')}
    >
      <svg viewBox="0 0 24 24" fill="none" width="15" height="15" aria-hidden="true">
        <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.7" />
        <path
          d="M3.5 9.5h17M3.5 14.5h17M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinecap="round"
        />
      </svg>
      {t('nav.switchLang')}
    </button>
  )
}

function Nav() {
  const { t } = useLang()
  return (
    <nav className="nav">
      <div className="container nav-inner">
        <NavLink to="/" className="brand">
          <span className="brand-mark" />
          Twin
        </NavLink>
        <div className="nav-links">
          <NavLink to="/" end className="nav-link">
            {t('nav.home')}
          </NavLink>
          <NavLink to="/dashboard" className="nav-link">
            {t('nav.dashboard')}
          </NavLink>
          <NavLink to="/chat" className="nav-link">
            {t('nav.chat')}
          </NavLink>
          <LangToggle />
        </div>
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <div className="shell">
      <Nav />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/chat" element={<Chat />} />
        {/* Anything else falls back to the landing page rather than a blank screen. */}
        <Route path="*" element={<Landing />} />
      </Routes>
    </div>
  )
}
