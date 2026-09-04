/**
 * Matchup preview data, read straight from ESPN by the phone.
 *
 * Same reasoning as espn.js, and the same two endpoints' worth of trust: keyless, CORS
 * open (`Access-Control-Allow-Origin: *`, checked 2026-09-04), and nothing here is ever
 * written to Postgres. If any of it fails the sheet says so and the pick flow is
 * untouched, because none of this feeds grading.
 *
 * Two calls, deliberately different in shape:
 *
 *   rankings  one per session for the whole app, ~35KB. Feeds the little #6 next to a
 *             team name on every row, so it has to load whether or not a sheet is opened.
 *   summary   one per game, ~13KB, fetched only when a sheet actually opens and then
 *             cached for the session. Twenty of them would be 260KB, which is why this
 *             is lazy rather than prefetched with the slate.
 *
 * Everything is matched on ESPN team id, never on abbreviation. Two different "TUL"
 * teams can appear on one slate (Tulane is TULN, Tulsa is TLSA) and the same class of
 * mistake silently assigns data to the wrong team. `games.id` in Postgres IS the ESPN
 * event id, so no matching is needed there either.
 */

const SITE = 'https://site.api.espn.com/apis/site/v2/sports/football/college-football'

/* ------------------------------------------------------------------ rankings */

let ranksPromise = null

/**
 * Map of ESPN team id (string) to AP poll position.
 *
 * Deliberately the AP poll and not the coaches poll: it is the one people mean when they
 * say a team is ranked. Unranked teams are absent rather than stored as 99, so a caller
 * can treat a miss as "no rank" without knowing ESPN's sentinel. Cached for the life of
 * the page: the poll moves once a week.
 */
export function fetchRankings() {
  if (!ranksPromise) {
    ranksPromise = (async () => {
      const res = await fetch(`${SITE}/rankings`)
      if (!res.ok) throw new Error(`ESPN rankings: HTTP ${res.status}`)
      const data = await res.json()
      const ap = (data.rankings || []).find((p) => p.type === 'ap')
      const out = new Map()
      for (const entry of ap?.ranks || []) {
        const id = entry.team?.id
        const n = Number(entry.current)
        if (id && Number.isFinite(n)) out.set(String(id), n)
      }
      return out
    })().catch((e) => {
      // Let the next caller try again rather than caching a network blip forever.
      ranksPromise = null
      throw e
    })
  }
  return ranksPromise
}

/* ------------------------------------------------------------------- summary */

/**
 * Raw payloads, not normalised results.
 *
 * Caching the normalised object keyed on event id alone was wrong: the same event asked
 * for with home and away swapped came back from the cache with the first call's labels,
 * so a caller that disagreed about which team was home got silently mislabelled data
 * rather than an error. The app always passes the same ids from the same database row,
 * so it could not have happened in practice, but the shape invited it. Normalising on
 * every call removes the trap and costs nothing.
 */
const payloads = new Map()

/** The two teams' entries out of a summary block, keyed home/away by ESPN team id. */
function sides(list, homeId, awayId, pick) {
  const out = { home: null, away: null }
  for (const entry of list || []) {
    const id = String(entry.team?.id ?? '')
    if (id && id === String(homeId)) out.home = pick(entry)
    else if (id && id === String(awayId)) out.away = pick(entry)
  }
  return out
}

/** "56-3 W vs PUR" reduced to what a pill needs. */
const lastFive = (entry) =>
  (entry.events || [])
    .map((e) => ({
      result: e.gameResult === 'W' ? 'W' : e.gameResult === 'L' ? 'L' : null,
      score: e.score || null,
      opponent: e.opponent?.abbreviation || null,
      away: e.atVs === '@',
      date: e.gameDate || null,
    }))
    .filter((e) => e.result)
    .slice(-5)

/**
 * One game's preview, normalised and cached by ESPN event id.
 *
 * `homeId` and `awayId` come from the database row rather than from the payload, because
 * Postgres is the authority on which team is at home and the two must not disagree.
 *
 * Several fields are legitimately null and callers must render without them:
 *   winProb   absent for a game ESPN has no projection for
 *   records   present but "0-0" in week 1, which is honest and not worth hiding
 *   lastFive  empty for a team with no prior games in ESPN's window
 *   weather   absent for a dome, and for most games more than a few days out
 */
export async function fetchMatchup(eventId, homeId, awayId) {
  const key = String(eventId)
  if (!payloads.has(key)) {
    const p = (async () => {
      const res = await fetch(`${SITE}/summary?event=${key}`)
      if (!res.ok) throw new Error(`ESPN summary: HTTP ${res.status}`)
      return res.json()
    })().catch((e) => {
      payloads.delete(key)
      throw e
    })
    payloads.set(key, p)
  }
  return normalise(await payloads.get(key), homeId, awayId)
}

/**
 * The shaping half of fetchMatchup, split out so it runs per call rather than per event.
 *
 * Exported only so tests/test_matchup.py can drive it against a saved ESPN payload. The
 * app has no reason to call it directly: the network half is the whole point of
 * fetchMatchup. Keeping it importable is what lets the tests stay offline, which is the
 * same bargain tests/fixtures/slate_week01.json makes for the Python side.
 */
export function normalise(d, homeId, awayId) {
  // Win probability. ESPN labels these homeTeam/awayTeam itself, but they are matched on
  // id anyway so a disagreement with Postgres shows as a missing bar, not a lie.
  const proj = {}
  for (const side of ['homeTeam', 'awayTeam']) {
    const t = d.predictor?.[side]
    const n = Number(t?.gameProjection)
    if (t?.id && Number.isFinite(n)) proj[String(t.id)] = n
  }
  const winProb =
    proj[String(homeId)] != null && proj[String(awayId)] != null
      ? { home: proj[String(homeId)], away: proj[String(awayId)] }
      : null

  const competitors = d.header?.competitions?.[0]?.competitors || []
  const records = sides(competitors, homeId, awayId, (c) => {
    const rec = (c.record || []).find((r) => r.type === 'total')
    return rec?.displayValue || rec?.summary || null
  })

  const form = sides(d.lastFiveGames, homeId, awayId, lastFive)
  const w = d.gameInfo?.weather

  return {
    winProb,
    records,
    lastFive: { home: form.home || [], away: form.away || [] },
    venue: d.gameInfo?.venue?.fullName || null,
    // Temperature and rain chance only. ESPN's conditionId is an unlabelled numeric code
    // and its displayValue came back null, so there is nothing to name the sky with that
    // could be trusted.
    weather: Number.isFinite(Number(w?.temperature))
      ? { temp: Number(w.temperature), precip: Number(w?.precipitation) }
      : null,
  }
}
