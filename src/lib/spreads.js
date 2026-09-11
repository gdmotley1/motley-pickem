/**
 * The Setup screen's spread filter.
 *
 * The pool is every FBS game in the week and it is mostly mismatches: of Week 2's 86
 * games, 39 were priced at 21 points or more and the median line was 20.5. Dad is
 * choosing twenty of those on a phone, and a confidence pool only works if the games are
 * worth ranking, so cutting by how close a game is does more for him than anything else
 * on the screen.
 *
 * ---------------------------------------------------------------------------
 * THE FILTER IS THE TAG. THEY ARE NOT TWO THINGS.
 *
 * This used to define its own thresholds, and they did not line up with the tier chip
 * printed on every row. Three bands (Toss-up at 3 or less, One score at 8, Lopsided at
 * 17 or more) against five tags (toss-up at 4, close at 10, medium at 18, big at 28,
 * blowout above). So a game chipped "toss-up" at 3.5 was hidden by the Toss-up filter,
 * and "close", "medium", "big" and "blowout" could not be filtered for at all. Grant
 * caught it on 2026-09-11.
 *
 * The fix is not to copy the numbers across, because a copy drifts the first time either
 * side changes. `inTier` matches on the tier the database already stored, so the chip you
 * tap and the chip printed on the row are reading the same value. The thresholds live in
 * exactly one place, scripts/suggest_slate.py TIERS, and this file never needs to know
 * them: the hints below are documentation, not logic.
 * ------------------------------------------------------------------------- */

/**
 * The five tiers, in order of how close the game is.
 *
 * `id` must equal the value suggest_slate.tier_of() writes to games.tier. `hint` is the
 * point range it corresponds to, shown under the label and used to explain an empty
 * list; it is never used to decide anything.
 */
export const BANDS = [
  { id: 'toss-up', name: 'Toss-up', hint: '4 or less' },
  { id: 'close', name: 'Close', hint: 'up to 10' },
  { id: 'medium', name: 'Medium', hint: 'up to 18' },
  { id: 'big', name: 'Big', hint: 'up to 28' },
  { id: 'blowout', name: 'Blowout', hint: 'over 28' },
]

const BY_ID = new Map(BANDS.map((b) => [b.id, b]))

/**
 * The magnitude of a game's line, or null when it has none.
 *
 * `spread_line` is stored as a positive number with `favorite_abbr` naming the side, but
 * abs() costs nothing and means a future sign convention cannot silently invert anything
 * reading this. Still used for sorting and for counting unpriced games; no longer used to
 * decide which filter a game belongs to.
 */
export const margin = (game) =>
  game?.spread_line === null || game?.spread_line === undefined
    ? null
    : Math.abs(Number(game.spread_line))

/**
 * True when the game carries this tier.
 *
 * A game with no posted line has no tier, so it is in no band, which is the same answer
 * the old threshold version gave and the right one: a pick'em with no published line is
 * not a toss-up. OU at MICH is that case live right now, with DraftKings showing the
 * spread OFF.
 */
export function inBand(game, id) {
  return BY_ID.has(id) && !!game?.tier && game.tier === id
}

/**
 * The bands with at least one game this week, each with a count.
 *
 * Built from the pool rather than hard-coded so a chip is never offered that filters to
 * nothing, which is the same rule availableConferences() follows.
 */
export function availableBands(pool) {
  return BANDS.map((b) => ({
    ...b,
    count: (pool || []).filter((g) => inBand(g, b.id)).length,
  })).filter((b) => b.count > 0)
}

/** How many games in the pool have no published line at all. */
export const unpricedCount = (pool) =>
  (pool || []).filter((g) => margin(g) === null).length
