/**
 * Reminders: the switch that turns Web Push on for this device, and the four kinds.
 *
 * Lives here rather than in App.jsx so outputs/harness/reminders.html can mount it in
 * every state without a backend, which is the only way to actually look at the states
 * that need a real phone to reach.
 *
 * The whole component is built around the thing that actually goes wrong. iOS will only
 * do this from a Home Screen install, and a permission it has denied can never be asked
 * for again by script. So an unsupported device gets a sentence explaining which of
 * those it is, rather than a button that does nothing when tapped.
 */
import { useCallback, useEffect, useState } from 'react'

import * as api from '../lib/api.js'
import { friendly } from '../lib/errors.js'
import { disablePush, enablePush, pushStatus } from '../lib/push.js'
import { Sheet, Spinner } from './ui.jsx'

/* The four kinds, in the order they matter. `key` matches the notify_* columns in
   migrations/012_push.sql and the prefs object src/lib/api.js sends. */
const NOTIFY_KINDS = [
  /* Kept to one line like the other three. The first draft ran to three, which made this
     row twice the height of its neighbours and the list read as ragged. */
  {
    key: 'picks',
    label: 'Pick reminders',
    sub: 'A few hours before your next kickoff, and once more at the wire.',
  },
  { key: 'live', label: 'New week is up', sub: 'When the slate gets published.' },
  { key: 'results', label: 'Week results', sub: 'When the last game of the week goes final.' },
  { key: 'passed', label: 'Someone passed you', sub: 'When you drop a place during the games.' },
]

/**
 * Everything the sheet draws, given a state rather than fetching one.
 *
 * Split out from the container below so outputs/harness/reminders.html can mount every
 * state side by side. That is not a nicety here: the states that matter most are the
 * ones that need a real iPhone with notifications denied to reach, so without this the
 * only way to look at them is to break a phone on purpose.
 */
export function RemindersView({ state, prefs, busy, error, onToggle, onSetKind, onClose }) {
  return (
    <>
      <h2 className="sheet__title">Reminders</h2>

      {state === null && <Spinner />}

      {state && !state.supported && <p className="sheet__sub">{state.reason}</p>}

      {state?.supported && (
        <>
          <p className="sheet__sub">
            {state.on
              ? 'This phone will buzz for the things you leave on below.'
              : 'Get a nudge before your picks lock, so a week never gets away from you.'}
          </p>

          {state.on && prefs && (
            <ul className="notiflist">
              {NOTIFY_KINDS.map(({ key, label, sub }) => (
                <li key={key} className="notifrow">
                  <div className="notifrow__text">
                    <span className="notifrow__label">{label}</span>
                    <span className="notifrow__sub">{sub}</span>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={!!prefs[key]}
                    aria-label={label}
                    className={`switch${prefs[key] ? ' is-on' : ''}`}
                    onClick={() => onSetKind(key, !prefs[key])}
                  >
                    <span className="switch__dot" />
                  </button>
                </li>
              ))}
            </ul>
          )}

          {error && <p className="notif__err">{error}</p>}

          <button className="btn" disabled={busy} onClick={() => onToggle(!state.on)}>
            {busy
              ? 'One moment…'
              : state.on
                ? 'Turn off on this phone'
                : 'Turn on reminders'}
          </button>
        </>
      )}

      <button className="btn btn--ghost" onClick={onClose}>
        Done
      </button>
    </>
  )
}

/**
 * The container: per device for the switch, per player for the four kinds.
 */
export default function RemindersSheet({ open, onClose }) {
  const [state, setState] = useState(null) // null = still looking
  const [prefs, setPrefs] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    const status = await pushStatus()
    setState(status)
    if (!status.supported) return
    try {
      const rows = await api.myPushState(status.endpoint ?? '')
      const row = Array.isArray(rows) ? rows[0] : rows
      if (row) {
        setPrefs({
          picks: row.notify_picks,
          live: row.notify_live,
          results: row.notify_results,
          passed: row.notify_passed,
        })
      }
    } catch {
      /* The switch still works without them; the four rows just do not render. */
    }
  }, [])

  useEffect(() => {
    if (!open) return
    setError(null)
    load()
  }, [open, load])

  const toggle = async (on) => {
    setBusy(true)
    setError(null)
    try {
      if (on) await enablePush()
      else await disablePush()
      await load()
    } catch (e) {
      /* The sentences push.js raises are already written for this family, and friendly()
         passes a short, non-leaky one straight through. What it catches is everything
         else: a dropped signal here reads "TypeError: Failed to fetch" otherwise. */
      setError(friendly(e, { fallback: 'Could not change that. Try again in a moment.' }))
    } finally {
      setBusy(false)
    }
  }

  const setKind = async (key, value) => {
    const next = { ...prefs, [key]: value }
    setPrefs(next) // optimistic: a switch that lags behind the thumb feels broken
    try {
      await api.setNotifyPrefs(next)
    } catch {
      setPrefs(prefs) // put it back rather than lie about what the server holds
      setError('Could not save that. Try again.')
    }
  }

  return (
    <Sheet open={open} onClose={onClose} label="Reminders">
      <RemindersView
        state={state}
        prefs={prefs}
        busy={busy}
        error={error}
        onToggle={toggle}
        onSetKind={setKind}
        onClose={onClose}
      />
    </Sheet>
  )
}
