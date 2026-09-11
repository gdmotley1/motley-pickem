/**
 * Turning reminders on, from the browser's side.
 *
 * There is no App Store here and nothing was ever submitted anywhere. Web Push is a
 * browser API: the phone generates its own keypair, hands back a subscription naming a
 * URL at Apple or Google, and anyone holding our VAPID private key can POST an
 * encrypted payload to it. `src/lib/api.js` stores the subscription, the service worker
 * in `static/sw.js` renders what arrives, and `migrations/012_push.sql` decides who is
 * due for what.
 *
 * ---------------------------------------------------------------------------
 * THE iOS RULES, WHICH ARE THE ONLY HARD ONES
 *
 * 1. Safari on iPhone delivers push ONLY to a site added to the Home Screen. A tab in
 *    Safari can call none of this and reports no support at all. All four of the family
 *    run it from the Home Screen, confirmed 2026-09-11, which is what makes this viable.
 * 2. `Notification.requestPermission()` must be called from a real user gesture. Calling
 *    it on load is denied outright and, worse, denied permanently.
 * 3. A denied permission cannot be re-requested by script, ever. The only route back is
 *    iOS Settings, so the UI has to say that rather than offering a button that silently
 *    does nothing.
 * ------------------------------------------------------------------------- */
import * as api from './api.js'

/** The public half of the VAPID pair. Public by design: it ships in the bundle, exactly
    like the anon key, and is useless without the private half. */
const VAPID_PUBLIC = import.meta.env.VITE_VAPID_PUBLIC_KEY || ''

/**
 * Why push might be unavailable, in the words the sheet shows.
 *
 * Every one of these is an ordinary state rather than an error, which is why they read
 * as explanations. The commonest by far is the first: someone opened the link in Safari
 * instead of tapping the icon on their Home Screen.
 */
export const UNSUPPORTED = {
  noWorker: 'Reminders need the app on your Home Screen. Open it from the icon, not Safari.',
  noPush: 'This browser cannot do notifications.',
  noKey: 'Reminders are not configured on this build.',
  denied: 'Notifications are turned off for this app. Turn them back on in Settings, then come back.',
}

/** base64url to the Uint8Array applicationServerKey wants. Safari rejects anything else. */
function urlBase64ToUint8Array(base64) {
  const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4)
  const raw = atob(padded.replace(/-/g, '+').replace(/_/g, '/'))
  const out = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i += 1) out[i] = raw.charCodeAt(i)
  return out
}

/** A subscription's keys arrive as ArrayBuffers and have to be sent as base64url. */
function encodeKey(subscription, name) {
  const raw = subscription.getKey(name)
  if (!raw) return null
  let binary = ''
  const bytes = new Uint8Array(raw)
  for (let i = 0; i < bytes.length; i += 1) binary += String.fromCharCode(bytes[i])
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

/**
 * Can this device do it at all, and has it already been asked?
 *
 * Never throws and never prompts. Safe to call on load, which is the point: the sheet
 * has to render the right thing before anyone taps anything.
 */
export async function pushStatus() {
  if (api.MOCK) return { supported: false, reason: UNSUPPORTED.noWorker }
  if (!('serviceWorker' in navigator)) return { supported: false, reason: UNSUPPORTED.noWorker }
  if (!('PushManager' in window)) return { supported: false, reason: UNSUPPORTED.noPush }
  if (!VAPID_PUBLIC) return { supported: false, reason: UNSUPPORTED.noKey }

  const permission = Notification.permission
  if (permission === 'denied') return { supported: false, reason: UNSUPPORTED.denied }

  let endpoint = null
  try {
    const reg = await navigator.serviceWorker.ready
    const sub = await reg.pushManager.getSubscription()
    endpoint = sub ? sub.endpoint : null
  } catch {
    /* A worker that has not activated yet is not a failure, just a not-yet. */
  }
  return { supported: true, permission, endpoint, on: !!endpoint }
}

/**
 * Ask for permission, subscribe, and store it. MUST be called from a tap.
 *
 * Returns the endpoint on success. Throws with a readable message otherwise, because
 * every failure here is something the person holding the phone can act on.
 */
export async function enablePush() {
  const status = await pushStatus()
  if (!status.supported) throw new Error(status.reason)

  const permission = await Notification.requestPermission()
  if (permission !== 'granted') {
    throw new Error(
      permission === 'denied' ? UNSUPPORTED.denied : 'Reminders were not turned on.',
    )
  }

  const reg = await navigator.serviceWorker.ready
  /* Reuse an existing subscription rather than making a second one. Safari returns the
     same endpoint anyway, but Chrome will happily hand out a new one and orphan the
     old, which then fails forever with a 410 nobody is watching for. */
  const sub =
    (await reg.pushManager.getSubscription()) ||
    (await reg.pushManager.subscribe({
      userVisibleOnly: true, // required, and true is also what we actually do
      applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC),
    }))

  const p256dh = encodeKey(sub, 'p256dh')
  const auth = encodeKey(sub, 'auth')
  if (!p256dh || !auth) throw new Error('This device did not return usable push keys.')

  await api.savePushSubscription(sub.endpoint, p256dh, auth)
  return sub.endpoint
}

/**
 * Turn reminders off on this device.
 *
 * Drops the server row first. If the browser-side unsubscribe then fails, the worst case
 * is a live subscription nobody sends to, which is harmless. The other order risks a
 * row we can never reach again, which sends to a dead endpoint forever.
 */
export async function disablePush() {
  const reg = await navigator.serviceWorker.ready
  const sub = await reg.pushManager.getSubscription()
  if (!sub) return
  try {
    await api.deletePushSubscription(sub.endpoint)
  } finally {
    await sub.unsubscribe()
  }
}

/**
 * Re-save the current subscription under the signed-in player.
 *
 * Two things make this necessary. The browser rotates a subscription occasionally and
 * the worker posts `resubscribe` when it does. And a device can change hands: the seat
 * switcher means the phone that was Nicole's is now Parker's, and the endpoint has to
 * follow, or the notifications keep going to the wrong name.
 */
export async function syncSubscription() {
  const status = await pushStatus()
  if (!status.supported || !status.endpoint) return null
  const reg = await navigator.serviceWorker.ready
  const sub = await reg.pushManager.getSubscription()
  if (!sub) return null
  const p256dh = encodeKey(sub, 'p256dh')
  const auth = encodeKey(sub, 'auth')
  if (!p256dh || !auth) return null
  await api.savePushSubscription(sub.endpoint, p256dh, auth)
  return sub.endpoint
}
