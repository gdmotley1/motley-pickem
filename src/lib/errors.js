/**
 * What a failure says to four family members on a phone.
 *
 * Every screen used to render `e.message` straight onto the page. On a dropped signal
 * that reads "TypeError: Failed to fetch", and a rejected RPC can put the Supabase
 * project URL on screen, which is both useless and a bit alarming. Nobody in this family
 * can act on either.
 *
 * The rule is narrow on purpose: recognise the handful of failures that actually happen
 * here and say what to do about them, and fall back to one plain sentence otherwise. It
 * is deliberately NOT a mapping of every Postgres error, because inventing friendly text
 * for a failure nobody has seen is how you end up hiding a real bug behind reassurance.
 *
 * The original message still goes to the console, so a problem is never lost.
 *
 * Two of these sentences are only true once you are signed in: there are no picks to
 * reassure anyone about on the sign-in screen, and no name at the top to tap. Pass
 * `atSignIn` from there and they change.
 */

/** Anything that smells like a URL, a token, or a stack frame has no place on screen. */
const LEAKY = /https?:\/\/|\bat\s+\w+|[A-Za-z0-9_-]{30,}/

const OFFLINE =
  'No connection. Your picks are safe on this phone; try again when you have signal.'
const OFFLINE_SIGNIN = 'No connection. Check your signal and try again.'

/** Said by both halves of the sign-in screen, so it lives in one place. */
export const NO_SESSION = 'Signed in, but the session did not start. Try your PIN again.'

export function friendly(err, opts = {}) {
  const {
    fallback = 'Something went wrong. Try again in a moment.',
    atSignIn = false,
  } = opts
  const raw = typeof err === 'string' ? err : err?.message || ''
  if (raw) console.warn('pickem:', err)

  const offline =
    (typeof navigator !== 'undefined' && navigator.onLine === false) ||
    // Every browser words this differently; "fetch" is the only common thread.
    /fetch|NetworkError|network request failed/i.test(raw)
  if (offline) return atSignIn ? OFFLINE_SIGNIN : OFFLINE

  // The two RLS rules this app actually enforces, which a player CAN trip by being slow.
  if (/kicked off|already started|locked/i.test(raw)) {
    return 'That game has already kicked off, so it can no longer be changed.'
  }
  if (/JWT|token|not authenticated|not signed in|session/i.test(raw)) {
    return atSignIn
      ? NO_SESSION
      : 'You have been signed out. Tap your name at the top to sign back in.'
  }

  // Anything else: show it only if it is a plain sentence somebody could repeat.
  if (raw && raw.length < 90 && !LEAKY.test(raw)) return raw
  return fallback
}
