/**
 * FBS conference ids, for the Setup screen's filter.
 *
 * The pool is every FBS game in the week, about ninety of them, so it needs cutting down
 * before it is any use on a phone. `games.home_conf` / `away_conf` have carried these
 * since migration 001; migration 007 is what finally returns them from `get_pool`.
 *
 * Ids and names read off ESPN's own group endpoint on 2026-09-04, not typed from memory:
 *   sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2026/types/2/groups/<id>
 * They match `fetch_slate.FBS_CONFERENCES`, which is the set the slate pull filters on.
 * Order here is display order, so the conferences this family actually watches come first.
 */
export const CONFERENCES = [
  { id: 8, name: 'SEC' },
  { id: 5, name: 'Big Ten' },
  { id: 1, name: 'ACC' },
  { id: 4, name: 'Big 12' },
  { id: 9, name: 'Pac-12' },
  { id: 151, name: 'American' },
  { id: 17, name: 'Mtn West' },
  { id: 37, name: 'Sun Belt' },
  { id: 12, name: 'CUSA' },
  { id: 15, name: 'MAC' },
  { id: 18, name: 'Indep.' },
]

const BY_ID = new Map(CONFERENCES.map((c) => [c.id, c]))

/** Short conference name for an id, or null. Coerced: ESPN types these as strings. */
export function confName(id) {
  const n = Number(id)
  return Number.isFinite(n) ? (BY_ID.get(n)?.name ?? null) : null
}

/** True when either team in a game belongs to the conference. */
export const inConference = (game, id) =>
  Number(game.home_conf) === Number(id) || Number(game.away_conf) === Number(id)

/**
 * The conferences with at least one game this week, in display order, each with a count.
 *
 * Built from the pool rather than hard-coded so a chip is never offered that filters to
 * nothing. A game counts once per conference, so a cross-conference game appears under
 * both, and the counts deliberately sum to more than the number of games.
 */
export function availableConferences(pool) {
  return CONFERENCES.map((c) => ({
    ...c,
    count: (pool || []).filter((g) => inConference(g, c.id)).length,
  })).filter((c) => c.count > 0)
}
