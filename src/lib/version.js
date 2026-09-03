/**
 * Detect when a newer build has been deployed.
 *
 * GitHub Pages serves index.html with max-age=600 and an installed PWA can hold it far
 * longer, so a phone keeps running an old bundle after a deploy. Vite content-hashes
 * every asset, so the set of hashed filenames in index.html is a build fingerprint.
 *
 * It compares ALL hashed assets, not just the JS. A CSS-only change leaves the JS hash
 * untouched, and an earlier version of this that watched only index-*.js reported "up to
 * date" after a real deploy.
 *
 * Nothing reloads on its own: a silent reload mid-pick would lose work, so the app
 * offers a button instead.
 */
const HASHED = /index-[A-Za-z0-9_-]+\.(?:js|css)/g

const fingerprint = (text) => [...new Set(text.match(HASHED) || [])].sort().join('|')

function running() {
  const refs = [
    ...[...document.querySelectorAll('script[src]')].map((s) => s.src),
    ...[...document.querySelectorAll('link[rel="stylesheet"][href]')].map((l) => l.href),
  ].join(' ')
  return fingerprint(refs)
}

export async function newBuildAvailable() {
  const mine = running()
  if (!mine) return false
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}index.html`, { cache: 'reload' })
    if (!res.ok) return false
    const served = fingerprint(await res.text())
    return !!served && served !== mine
  } catch {
    return false // offline, or the check failed. Never block the app on this.
  }
}
