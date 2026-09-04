/**
 * Live scores and live grading, read straight from ESPN by the phone.
 *
 * The database is only ever as fresh as the sync job, and GitHub does not honour the
 * every-15-minutes schedule in .github/workflows/sync.yml: on the Thursday of week 1 it
 * ran at 22:42 and then not again until 00:25, so the Colorado game sat on the board at
 * 0-0 for the whole first half. Rather than fight the scheduler, the client asks ESPN
 * itself. The scoreboard endpoint needs no key, sends CORS headers, and costs nothing.
 *
 * Display only. The winner written to Postgres is still the sync job's to write, and
 * `liveWinner` always defers to it when it is there. If this file fails entirely the
 * board falls back to the last synced score and nothing breaks.
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

/**
 * The days still worth asking about: a game that has kicked off and whose result we do
 * not already have, either from the database or from an earlier poll.
 *
 * A final score never changes, so once a day is settled it never needs fetching again.
 * This matters because the payload is not small: gzipped, the whole week is 81KB and a
 * Saturday alone is 64KB, against 12KB for a Thursday night. Asking only for the days
 * still in play keeps a Thursday poll at 12KB and stops the polling altogether once the
 * last game is over.
 */
export function pendingDates(games, previous) {
  const now = Date.now()
  const days = new Set()
  for (const g of games || []) {
    if (!g.kickoff) continue
    if (new Date(g.kickoff).getTime() > now) continue
    if (g.winner_abbr) continue
    if (previous?.get(String(g.game_id))?.completed) continue
    days.add(etDate(g.kickoff))
  }
  return [...days].sort()
}

/**
 * Map of ESPN event id to the live line, keyed as a string, carrying forward everything
 * already known so a narrowed fetch never drops a result we had.
 *
 * `games.id` in Postgres IS the ESPN event id, so the merge is a straight lookup with no
 * matching heuristics. Games that have not kicked off are skipped, so an unplayed game
 * keeps the kickoff time the database gave it rather than showing a meaningless 0-0.
 */
export async function fetchLiveScores(games, previous) {
  const days = pendingDates(games, previous)
  if (!days.length) return previous || new Map()
  const dates = days.length === 1 ? days[0] : `${days[0]}-${days[days.length - 1]}`

  const res = await fetch(`${SCOREBOARD}?groups=80&dates=${dates}`)
  if (!res.ok) throw new Error(`ESPN scoreboard: HTTP ${res.status}`)
  const data = await res.json()

  const out = new Map(previous || [])
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

/**
 * The winner to show: whatever the database has graded, else what the final score says.
 *
 * Returns null while a game is unfinished, so callers never have to guess. Deliberately
 * returns the abbreviation off the game row rather than off the ESPN payload, so a
 * difference in how the two spell a team can never produce a winner that matches nobody's
 * pick. A tie returns null; college football does not have them, and inventing a winner
 * from one would be worse than showing nothing.
 */
export function liveWinner(game, live) {
  if (game.winner_abbr) return game.winner_abbr
  const l = live?.get(String(game.game_id))
  if (!l?.completed) return null
  if (l.home_score == null || l.away_score == null) return null
  if (l.home_score === l.away_score) return null
  return l.home_score > l.away_score ? game.home_abbr : game.away_abbr
}

/** A game row with the live score, status and winner laid over the database values. */
export function withLive(game, live) {
  const l = live?.get(String(game.game_id))
  if (!l) return game
  return {
    ...game,
    away_score: l.away_score ?? game.away_score,
    home_score: l.home_score ?? game.home_score,
    status_detail: l.status_detail || game.status_detail,
    winner_abbr: liveWinner(game, live),
  }
}
