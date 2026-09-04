import React from 'react'
import { createRoot } from 'react-dom/client'
import './theme.css'
import './app.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

/**
 * Register the service worker, in production only.
 *
 * Not in dev: it would cache the dev server's modules and then serve them back over the
 * top of an edit, which reads as "my change did nothing" and costs an hour to work out.
 * It also sits under outputs/harness/, where the whole point is to run the real
 * components against a stubbed network.
 *
 * Failure is swallowed on purpose. No worker means the app behaves exactly as it did
 * before this file existed, which is a working app that needs a signal.
 */
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register(`${import.meta.env.BASE_URL}sw.js`, { scope: import.meta.env.BASE_URL })
      .catch(() => {})
  })
}
