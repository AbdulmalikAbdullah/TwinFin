import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { LanguageProvider } from './lib/i18n'
import './styles.css'

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <LanguageProvider>
      {/* BASE_URL is '/TwinFin/' in the deployed build and '/' in dev, so the same
          routes work in both. Without it every <Link> would point outside the repo path. */}
      <BrowserRouter basename={import.meta.env.BASE_URL}>
        <App />
      </BrowserRouter>
    </LanguageProvider>
  </React.StrictMode>,
)
