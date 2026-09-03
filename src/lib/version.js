/**
 * Detect when a newer build has been deployed.
 *
 * GitHub Pages serves index.html with max-age=600 and an installed PWA can hold it far
 * longer, so a phone keeps running an old bundle after a deploy. The asset filenames are
 * content-hashed, so comparing the hash this page loaded against the one the server is
 * currently serving is enough to spot it. Nothing reloads on its own: a silent reload
 * mid-pick would lose work, so the app offers a button instead.
 */
const BUNDLE = /index-[A-Za-z0-9_-]+\.js/

function runningBundle() {
  const tag = [...document.querySelectorAll('script[src]')].find((s) => BUNDLE.test(s.src))
  return tag ? tag.src.split('/').pop() : null
}

export async function newBuildAvailable() {
  const mine = runningBundle()
  if (!mine) return false
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}index.html`, { cache: 'reload' })
    if (!res.ok) return false
    const served = ((await res.text()).match(BUNDLE) || [])[0]
    return !!served && served !== mine
  } catch {
    return false // offline, or the check itself failed. Never block the app on this.
  }
}
