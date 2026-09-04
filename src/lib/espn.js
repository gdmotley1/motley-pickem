/**
 * Live scores, read straight from ESPN by the phone.
 *
 * The scores in Postgres are only ever as fresh as the sync job, and GitHub does not
 * honour the every-15-minutes schedule in .github/workflows/sync.yml: on the Thursday
 * of week 1 it ran at 22:42 and then not again until 00:25, so the Colorado game sat
 * on the board at 0-0 for the whole first half. Rather than fight the scheduler, the
 * client asks ESPN itself. The scoreboard endpoint needs no key, sends CORS headers,
 * and costs nothing.
 *
 * Display only. Winners, grading and the standings still come from the database via
 * the sync job, so if this file fails entirely the board simply shows the last synced
 * score and nothing else breaks.
 */

const SCOREBOARD =
  'https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard'

/**
 * ESPN files games under their Eastern date, so a Thursday 8pm kickoff is the 3rd even
 * though it is already the 4th in UTC. Taking the UTC date here would miss every night
 * game by a day.
 */
const etDate = (iso) =>
  new Date(iso).toLocaleDateString('en-CA', { timeZone: 'America/New_York' }).replace(/-/g, '')

/** "20260903-20260906" spans the whole week in one request instead of four. */
export function dateRange(games) {
  const days = (games || [])
    .map((g) => g.kickoff)
    .filter(Boolean)
    .map(etDate)
    .sort()
  if (!days.length) return null
  const first = days[0]
  const last = days[days.length - 1]
  return first === last ? first : `${first}-${last}`
}

/**
 * Map of ESPN event id to the live line, keyed as a string.
 *
 * `games.id` in Postgres IS the ESPN event id, so the merge on the board is a straight
 * lookup with no matching heuristics. Games that have not kicked off are left out, so
 * an unplayed game keeps the kickoff time the database gave it rather than showing a
 * meaningless 0-0.
 */
export async function fetchLiveScores(games) {
  const dates = dateRange(games)
  if (!dates) return new Map()

  const res = await fetch(`${SCOREBOARD}?groups=80&dates=${dates}`)
  if (!res.ok) throw new Error(`ESPN scoreboard: HTTP ${res.status}`)
  const data = await res.json()

  const out = new Map()
  for (const ev of data.events || []) {
    const comp = ev.competitions?.[0]
    const status = comp?.status?.type
    if (!comp || !status || status.state === 'pre') continue

    const scoreFor = (side) => {
      const n = Number(comp.competitors?.find((c) => c.homeAway === side)?.score)
      return Number.isFinite(n) ? n : null
    }

    out.set(String(ev.id), {
      away_score: scoreFor('away'),
      home_score: scoreFor('home'),
      // "11:34 - 4th" rather than "11:34 - 4th Quarter": the chip is a phone wide.
      status_detail: status.shortDetail || status.detail || null,
      completed: !!status.completed,
    })
  }
  return out
}
