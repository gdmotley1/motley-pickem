import { useEffect, useRef, useState } from 'react'
import * as api from '../lib/api.js'
import { Avatar, Sheet, Spinner } from '../components/ui.jsx'

const PIN_LENGTH = 4

/**
 * Four seats. An empty one is claimed by typing a name and a PIN; a taken one just needs
 * its PIN. No account, no email, nothing to reset, so everyone in the family gets in on
 * the first try.
 */
export default function SignIn({ onSignedIn }) {
  const [seats, setSeats] = useState(null)
  const [active, setActive] = useState(null)
  const [error, setError] = useState(null)
  // Keep the last opened seat around while the sheet slides out, so it does not go
  // blank mid-animation.
  const shown = useRef(null)
  if (active) shown.current = active

  const refresh = () => api.listSeats().then(setSeats)

  useEffect(() => {
    refresh().catch((e) => setError(e.message))
  }, [])

  async function finish() {
    try {
      const me = await api.whoami()
      if (me) onSignedIn(me)
      else setError('Signed in, but the session did not start. Try your PIN again.')
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="signin">
      <p className="signin__kicker">College Football</p>
      <h1 className="signin__title">Motley Pick&apos;em</h1>
      <p className="signin__sub">Twenty games a week. Twenty points. Tap your name.</p>

      {!seats && !error && <Spinner />}
      {/* Shown whether or not the seats loaded. Gating this on !seats hid a real
          failure: claiming a seat worked, whoami then died, and the screen just sat
          there with no explanation. */}
      {error && <p className="err">{error}</p>}

      {seats && (
        <div className="seats">
          {seats.map((s) => (
            <SeatTile key={s.id} seat={s} onClick={() => setActive(s)} />
          ))}
        </div>
      )}

      {seats && (
        <p className="signin__hint">
          Your phone stays signed in. Tap your name at the top to switch any time.
        </p>
      )}

      <Sheet open={!!active} onClose={() => setActive(null)} label="Sign in">
        {shown.current && (
          <SeatForm
            key={shown.current.id}
            seat={shown.current}
            onClose={() => setActive(null)}
            onDone={finish}
            onClaimed={refresh}
          />
        )}
      </Sheet>
    </div>
  )
}

function SeatTile({ seat, onClick }) {
  return (
    <button
      className={`seat${seat.claimed ? '' : ' is-empty'}`}
      onClick={onClick}
      aria-label={seat.claimed ? `Sign in as ${seat.name}` : `Claim seat ${seat.id}`}
    >
      {seat.claimed ? (
        <>
          <Avatar name={seat.name} color={seat.color} size={38} />
          <span className="seat__name">
            {seat.name}
            {seat.is_admin && <span className="seat__role">Commissioner</span>}
          </span>
        </>
      ) : (
        <>
          <span className="seat__plus">+</span>
          <span className="seat__name">Empty seat</span>
        </>
      )}
    </button>
  )
}

function SeatForm({ seat, onClose, onDone, onClaimed }) {
  const claiming = !seat.claimed
  const [name, setName] = useState('')
  const [pin, setPin] = useState('')
  const [confirm, setConfirm] = useState('')
  const [stage, setStage] = useState(claiming ? 'name' : 'pin')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const nameRef = useRef(null)

  useEffect(() => {
    if (stage === 'name') setTimeout(() => nameRef.current?.focus(), 240)
  }, [stage])

  const onConfirmStage = stage === 'confirm'
  const target = onConfirmStage ? confirm : pin
  const setTarget = onConfirmStage ? setConfirm : setPin

  // Submitting on the fourth digit is what makes this feel instant rather than
  // "type four digits, then hunt for a button".
  useEffect(() => {
    if (target.length !== PIN_LENGTH || busy) return
    if (stage === 'pin' && claiming) {
      setStage('confirm')
      return
    }
    submit()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target])

  async function submit() {
    setBusy(true)
    setError(null)
    try {
      if (claiming) {
        if (pin !== confirm) throw new Error('Those PINs did not match')
        await api.claimSeat(seat.id, name.trim(), pin)
        onClaimed?.()
      } else {
        await api.signIn(seat.id, pin)
      }
      await onDone()
    } catch (e) {
      setError(e.message)
      setPin('')
      setConfirm('')
      setStage('pin')
    } finally {
      setBusy(false)
    }
  }

  const press = (d) => {
    if (busy || target.length >= PIN_LENGTH) return
    setError(null)
    setTarget(target + d)
    navigator.vibrate?.(8)
  }

  const back = () => {
    setError(null)
    if (stage === 'confirm') {
      setConfirm('')
      setStage('pin')
    } else if (stage === 'pin' && claiming) {
      setPin('')
      setStage('name')
    } else {
      onClose()
    }
  }

  const heading =
    stage === 'name'
      ? 'Who are you?'
      : stage === 'confirm'
        ? 'Confirm your PIN'
        : claiming
          ? 'Pick a 4-digit PIN'
          : `Hi, ${seat.name}`

  const sub =
    stage === 'name'
      ? 'This is how everyone sees you on the board.'
      : stage === 'confirm'
        ? 'Once more, so a typo cannot lock you out.'
        : claiming
          ? 'You will use this on any new phone.'
          : 'Enter your PIN to continue'

  return (
    <>
      <h2 className="sheet__title">{heading}</h2>
        <p className="sheet__sub">{sub}</p>

        {stage === 'name' ? (
          <>
            <label className="label" htmlFor="seat-name">
              Your name
            </label>
            <input
              id="seat-name"
              ref={nameRef}
              className="field"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Grant"
              maxLength={18}
              autoComplete="off"
              enterKeyHint="next"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && name.trim()) setStage('pin')
              }}
            />
            <div style={{ height: 16 }} />
            <button className="btn" disabled={!name.trim()} onClick={() => setStage('pin')}>
              Continue
            </button>
          </>
        ) : (
          <>
            <div className={`pin${error ? ' shake' : ''}`}>
              {Array.from({ length: PIN_LENGTH }).map((_, i) => (
                <span
                  key={i}
                  className={`pin__dot${
                    error ? ' is-bad' : i < target.length ? ' is-on' : ''
                  }`}
                />
              ))}
            </div>

            <div className="keypad">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((d) => (
                <button key={d} className="key" onClick={() => press(String(d))}>
                  {d}
                </button>
              ))}
              <button className="key key--ghost" onClick={back}>
                Back
              </button>
              <button className="key" onClick={() => press('0')}>
                0
              </button>
              <button
                className="key key--ghost"
                onClick={() => {
                  setError(null)
                  setTarget(target.slice(0, -1))
                }}
                aria-label="Delete last digit"
              >
                ⌫
              </button>
            </div>
          </>
        )}

        {error && <p className="err">{error}</p>}

      <button className="btn btn--ghost" onClick={onClose}>
        {claiming ? 'Cancel' : 'Not you? Pick another name'}
      </button>
    </>
  )
}
