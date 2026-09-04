/**
 * Motley Pick'em service worker.
 *
 * The app had a manifest and icons from the start, so it installed to a home screen and
 * got an icon and a splash, and then it was a shell around a page that needed the
 * network. Every cold launch re-fetched the bundle and the logos, and at a tailgate on
 * two bars it simply did not open. This is the piece that makes it an app.
 *
 * Ships from static/, which vite copies to the site root verbatim. That means no
 * bundling and no import.meta.env in here: the base path is read off this file's own
 * location instead, so a move from /motley-pickem/ to a custom domain needs no edit.
 *
 * ---------------------------------------------------------------------------
 * THE RULE THAT OUTRANKS EVERYTHING, RESTATED FOR CACHING
 *
 * Locking and pick visibility are enforced by Postgres RLS. A cache must never be able
 * to soften that, so nothing that talks to Supabase is touched here: every request that
 * is not a same-origin GET is passed straight through and never stored. That covers
 * every RPC, which are POSTs, and it covers ESPN, whose whole value is being live.
 *
 * The consequence is deliberate. Offline you get the app, instantly, and its own error
 * states where data would be. You do not get yesterday's scores dressed up as today's.
 * ------------------------------------------------------------------------- */

// Bump to invalidate the shell and the assets. Logos are excluded on purpose, below.
const VERSION = 'v1'

const SHELL = `pickem-shell-${VERSION}`
const ASSETS = `pickem-assets-${VERSION}`

/**
 * Logos are NOT versioned with the rest.
 *
 * A team's mark does not change when the app deploys, and there are 276 of them at about
 * 12MB. Tying them to VERSION would re-download a week's worth on every deploy for no
 * reason. They are also never precached: only about 40 teams appear in a given week, so
 * they arrive on first use and stay.
 */
const LOGOS = 'pickem-logos'

const KEEP = new Set([SHELL, ASSETS, LOGOS])

/** "/motley-pickem/" here, "/" on a custom domain. Derived, never hard-coded. */
const BASE = new URL('./', self.location).pathname
const INDEX = BASE + 'index.html'

self.addEventListener('install', (event) => {
  // The shell only. Everything else arrives on first use, which keeps the install cheap
  // and means a failed fetch here can never block the worker from taking over.
  event.waitUntil(
    caches
      .open(SHELL)
      .then((cache) => cache.add(new Request(INDEX, { cache: 'reload' })))
      .catch(() => {})
      .then(() => self.skipWaiting()),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((names) => Promise.all(names.filter((n) => !KEEP.has(n)).map((n) => caches.delete(n))))
      // Claiming immediately is safe here specifically because the build emits ONE
      // bundle with no code splitting. With lazy chunks, swapping assets under a running
      // page can ask for a chunk the new deploy renamed. Without them there is nothing
      // to miss, and the alternative is worse: a home-screen app is never really closed,
      // so a worker that waits for that would leave the family on an old build for days.
      .then(() => self.clients.claim()),
  )
})

/** Only ever store a real, complete, same-origin response. */
async function keep(cacheName, request, response) {
  if (!response || response.status !== 200 || response.type !== 'basic') return response
  const cache = await caches.open(cacheName)
  cache.put(request, response.clone())
  return response
}

/** Immutable by content hash, so the cached copy is always the right one. */
async function cacheFirst(cacheName, request) {
  const hit = await caches.match(request)
  if (hit) return hit
  return keep(cacheName, request, await fetch(request))
}

/**
 * The document, and only the document.
 *
 * index.html carries no content hash, so it is the one file that has to come from the
 * network when there is one, or a deploy would never be picked up. Falling back to the
 * cached copy is what makes the app open on a bad signal.
 */
async function networkFirstDocument(request) {
  try {
    const fresh = await fetch(request);
    // Keyed on INDEX rather than the request: a deep link would otherwise store itself
    // as a second, identical shell.
    keep(SHELL, new Request(INDEX), fresh.clone());
    return fresh
  } catch {
    const cached = (await caches.match(INDEX)) || (await caches.match(request))
    if (cached) return cached
    throw new Error('offline and no cached shell')
  }
}

self.addEventListener('fetch', (event) => {
  const { request } = event

  // Anything that is not a plain same-origin GET is none of this worker's business.
  // Supabase RPCs are POSTs and ESPN is cross-origin, so both fall out here.
  if (request.method !== 'GET') return
  const url = new URL(request.url)
  if (url.origin !== self.location.origin) return

  if (request.mode === 'navigate') {
    event.respondWith(networkFirstDocument(request))
    return
  }

  if (url.pathname.startsWith(BASE + 'logos/')) {
    event.respondWith(cacheFirst(LOGOS, request))
    return
  }

  // Hashed bundles, icons and the manifest: all immutable or near enough.
  if (
    url.pathname.startsWith(BASE + 'assets/') ||
    url.pathname.startsWith(BASE + 'icons/') ||
    url.pathname.endsWith('.webmanifest')
  ) {
    event.respondWith(cacheFirst(ASSETS, request))
    return
  }

  // Everything else same-origin (the offline demo week, say): network, then whatever
  // was stored last.
  event.respondWith(
    fetch(request)
      .then((res) => keep(ASSETS, request, res))
      .catch(async () => {
        const hit = await caches.match(request)
        if (hit) return hit
        throw new Error('offline and uncached: ' + url.pathname)
      }),
  )
})
