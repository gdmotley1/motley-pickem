/** Small shared pieces. Kept in one file so the screens stay about their own logic. */
import { useCallback, useEffect, useState } from 'react'
import { createPortal } from 'react-dom'

const EXIT_MS = 200

/**
 * Renders into document.body.
 *
 * `position: fixed` resolves against the nearest ancestor with a transform, not the
 * viewport. The screen wrapper is a motion.div that keeps a transform after animating,
 * so a fixed bar inside it anchored to the page instead of the screen and ended up at
 * y=1533 in an 812px viewport. Portalling past that subtree is the fix.
 */
export function Portal({ children }) {
  if (typeof document === 'undefined') return null
  return createPortal(children, document.body)
}

/**
 * Bottom sheet that owns its own mount/unmount.
 *
 * This deliberately does NOT use AnimatePresence. Under React 19 the exit animation
 * never completed, so a closed sheet stayed in the DOM and its full-screen scrim kept
 * swallowing every tap on the page behind it. Here the close is a CSS animation plus a
 * timer we control, so the node is always gone afterwards.
 */
export function Sheet({ open, onClose, label, children }) {
  const [mounted, setMounted] = useState(open)
  const [closing, setClosing] = useState(false)

  const finish = useCallback(() => {
    setMounted(false)
    setClosing(false)
  }, [])

  useEffect(() => {
    if (open) {
      setMounted(true)
      setClosing(false)
      return undefined
    }
    if (!mounted) return undefined
    setClosing(true)
    // The close is driven by animationend below. This timer is only a safety net: a
    // backgrounded tab throttles timers AND animations, so whichever lands first wins
    // and the sheet can never be left mounted over the page.
    const t = setTimeout(finish, EXIT_MS * 4)
    return () => clearTimeout(t)
  }, [open, mounted, finish])

  // Escape closes, and the page behind must not scroll while a sheet is up.
  useEffect(() => {
    if (!mounted) return undefined
    const onKey = (e) => e.key === 'Escape' && onClose?.()
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [mounted, onClose])

  if (!mounted) return null

  return (
    <Portal>
      <div
        className={`sheet__scrim${closing ? ' is-out' : ''}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        className={`sheet${closing ? ' is-out' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label={label}
        onAnimationEnd={(e) => {
          if (closing && e.target === e.currentTarget) finish()
        }}
      >
        <div className="sheet__grab" />
        {children}
      </div>
    </Portal>
  )
}

/** Same reasoning as Sheet: a stuck toast would sit over the tab bar forever. */
export function Toast({ message, onDone, ms = 2600 }) {
  const [closing, setClosing] = useState(false)

  useEffect(() => {
    if (!message) return undefined
    setClosing(false)
    const a = setTimeout(() => setClosing(true), ms)
    const b = setTimeout(() => onDone?.(), ms + EXIT_MS)
    return () => {
      clearTimeout(a)
      clearTimeout(b)
    }
  }, [message, ms, onDone])

  if (!message) return null
  return (
    <Portal>
      <div className={`toast${closing ? ' is-out' : ''}`}>{message}</div>
    </Portal>
  )
}

export function Back({ onClick, label = 'Back' }) {
  return (
    <button className="back" onClick={onClick}>
      <Chevron />
      {label}
    </button>
  )
}

export function Chevron({ dir = 'left', size = 16 }) {
  const d = { left: 'M13 4 7 10l6 6', right: 'M7 4l6 6-6 6' }[dir]
  return (
    <svg viewBox="0 0 20 20" width={size} height={size} aria-hidden="true">
      <path
        d={d}
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  )
}

export function Avatar({ name, color, size = 26 }) {
  const initials = (name || '?')
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase()
  return (
    <span
      className="avatar"
      style={{ background: color, width: size, height: size, fontSize: size * 0.42 }}
      aria-hidden="true"
    >
      {initials}
    </span>
  )
}

export function Empty({ icon, title, children }) {
  return (
    <div className="empty">
      <div className="empty__icon">{icon}</div>
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  )
}

export const Spinner = () => <div className="spinner" role="status" aria-label="Loading" />

export function Screen({ eyebrow, title, sub, children, action }) {
  return (
    <>
      <div className="screen">
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
          <h2 className="h1" style={{ flex: 1 }}>
            {title}
          </h2>
          {action}
        </div>
        {sub && <p className="sub">{sub}</p>}
      </div>
      {children}
    </>
  )
}

/* ------------------------------------------------------------------ icons */

export const IconPicks = () => (
  <svg viewBox="0 0 24 24" width="21" height="21" aria-hidden="true" fill="none">
    <path
      d="M5 7h14M5 12h14M5 17h8"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
    />
  </svg>
)

export const IconBoard = () => (
  <svg viewBox="0 0 24 24" width="21" height="21" aria-hidden="true" fill="none">
    <rect x="3" y="4" width="18" height="16" rx="2.5" stroke="currentColor" strokeWidth="2" />
    <path d="M3 9.5h18M9 9.5V20" stroke="currentColor" strokeWidth="2" />
  </svg>
)

export const IconTrophy = () => (
  <svg viewBox="0 0 24 24" width="21" height="21" aria-hidden="true" fill="none">
    <path
      d="M7 4h10v5a5 5 0 0 1-10 0V4Z"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinejoin="round"
    />
    <path
      d="M7 6H4.5v1A3 3 0 0 0 7 10M17 6h2.5v1a3 3 0 0 1-2.5 3M9.5 20h5M12 14v6"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
    />
  </svg>
)

export const IconAdmin = () => (
  <svg viewBox="0 0 24 24" width="21" height="21" aria-hidden="true" fill="none">
    <path
      d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"
      stroke="currentColor"
      strokeWidth="2"
    />
    <path
      d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.03 1.56V21a2 2 0 1 1-4 0v-.07A1.7 1.7 0 0 0 8.9 19.3a1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.7 1.7 0 0 0 4.54 15a1.7 1.7 0 0 0-1.56-1.03H3a2 2 0 1 1 0-4h.07A1.7 1.7 0 0 0 4.7 8.9a1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.7 1.7 0 0 0 9 4.54a1.7 1.7 0 0 0 1.03-1.56V3a2 2 0 1 1 4 0v.07A1.7 1.7 0 0 0 15.1 4.7a1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.7 1.7 0 0 0 19.46 9v.07a1.7 1.7 0 0 0 1.56 1.03H21a2 2 0 1 1 0 4h-.07a1.7 1.7 0 0 0-1.53 1Z"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
)

export const IconClock = () => (
  <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" fill="none">
    <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" />
    <path d="M12 7v5l3 2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  </svg>
)

export const IconGrip = () => (
  <svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true">
    <path
      d="M7 6h.01M13 6h.01M7 10h.01M13 10h.01M7 14h.01M13 14h.01"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
    />
  </svg>
)

export const IconLock = ({ size = 12 }) => (
  <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true" fill="none">
    <rect x="4.5" y="10.5" width="15" height="10" rx="2.2" stroke="currentColor"
          strokeWidth="2.2" />
    <path d="M8 10.5V7.5a4 4 0 0 1 8 0v3" stroke="currentColor" strokeWidth="2.2"
          strokeLinecap="round" />
  </svg>
)
