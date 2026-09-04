/**
 * The 139 schools you can wear as a profile picture.
 *
 * Built by scripts/build_team_library.py into static/data/teams.json, which carries far
 * more than a name: `bg` is a colour that school's mark actually shows up on, and `cut`
 * says whether to use the light or dark drawing of it. Both were decided by measuring
 * every logo at build time, so nothing here has to think about contrast.
 *
 * Loaded once per session, about 18KB. Two shapes are needed and they are different:
 *
 *   `teamById` is SYNCHRONOUS, because <Avatar> renders inside lists and cannot await.
 *   Before the file lands it returns undefined and the avatar falls back to an initial,
 *   which is exactly what an unset team looks like anyway, so there is no flash of
 *   anything wrong.
 *
 *   `useTeams` is the hook the picker uses, and it re-renders when the file arrives.
 */
import { useEffect, useState } from 'react'

let cache = null
let inFlight = null
const waiting = new Set()

const url = () => `${import.meta.env.BASE_URL}data/teams.json`

/** Kick off the one fetch. Safe to call from anywhere, any number of times. */
export function loadTeams() {
  if (cache) return Promise.resolve(cache)
  if (!inFlight) {
    inFlight = fetch(url())
      .then((r) => {
        if (!r.ok) throw new Error(`teams.json ${r.status}`)
        return r.json()
      })
      .then((rows) => {
        cache = rows
        waiting.forEach((fn) => fn(rows))
        waiting.clear()
        return rows
      })
      .catch((e) => {
        // A missing library is not worth an error screen: every avatar simply stays an
        // initial, which is the same thing an unset team looks like. Allow a retry.
        inFlight = null
        console.warn('team library unavailable', e)
        return []
      })
  }
  return inFlight
}

/** Synchronous lookup for render paths. Undefined until the library has landed. */
export function teamById(id) {
  if (!id || !cache) return undefined
  return cache.find((t) => t.id === id)
}

export function useTeams() {
  const [teams, setTeams] = useState(cache)
  useEffect(() => {
    if (cache) return undefined
    let alive = true
    const fn = (rows) => alive && setTeams(rows)
    waiting.add(fn)
    loadTeams().then(fn)
    return () => {
      alive = false
      waiting.delete(fn)
    }
  }, [])
  return teams
}

/** Path to the cut of the mark that was chosen for this team's background. */
export function markUrl(team) {
  const file = team.cut === 'dark' ? `${team.id}-dark` : team.id
  return `${import.meta.env.BASE_URL}logos/${file}.png`
}

/**
 * Rank a search box query against a team.
 *
 * Deliberately generous, because the people using this are typing on a phone and may
 * know the mascot but not the school, or the other way round. "bobcat" has to find
 * Georgia College, and "uga" has to find Georgia. Returns 0 for no match; higher is a
 * better match, so the list can sort by it.
 */
export function score(team, query) {
  const q = query.trim().toLowerCase()
  if (!q) return 1
  const school = team.school.toLowerCase()
  const abbr = (team.abbr || '').toLowerCase()
  const mascot = (team.mascot || '').toLowerCase()
  if (abbr === q) return 100
  if (school === q) return 90
  if (school.startsWith(q)) return 80
  if (mascot.startsWith(q)) return 60
  if (abbr.startsWith(q)) return 55
  if (school.includes(q)) return 40
  if (mascot.includes(q)) return 30
  return 0
}
