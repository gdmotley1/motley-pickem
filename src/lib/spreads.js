/**
 * Spread bands, for the Setup screen's filter.
 *
 * The pool is every FBS game in the week and it is mostly mismatches: of Week 2's 86
 * games, 39 were priced at 21 points or more and the median line was 20.5. Dad is
 * choosing twenty of those on a phone, and a confidence pool only works if the games are
 * worth ranking, so "show me the ones that are actually close" is the cut that does the
 * most for him. CLAUDE.md already warns that ESPN's featured list is a brand list rather
 * than a good-games list; this is the same problem one screen later.
 *
 * Thresholds, not a partition. `One score` deliberately contains every `Toss-up`, because
 * they answer different questions and nobody reading a chip expects a bucket.
 */

/** Counts are Week 2's, kept here only as a sense of scale when reading the labels. */
export const BANDS = [
  { id: 'tossup', name: 'Toss-up', hint: '3 or less', test: (s) => s <= 3 },
  { id: 'onescore', name: 'One score', hint: '8 or less', test: (s) => s <= 8 },
  { id: 'lopsided', name: 'Lopsided', hint: '17 or more', test: (s) => s >= 17 },
]

const BY_ID = new Map(BANDS.map((b) => [b.id, b]))

/**
 * The magnitude of a game's line, or null when it has none.
 *
 * `spread_line` is stored as a positive number with `favorite_abbr` naming the side, but
 * abs() costs nothing and means a future sign convention cannot silently invert every
 * band. A game with no line has no margin to test, so it is null rather than 0: a
 * pick'em with no published line is not the same thing as a toss-up.
 */
export const margin = (game) =>
  game?.spread_line === null || game?.spread_line === undefined
    ? null
    : Math.abs(Number(game.spread_line))

/** True when the game's line falls in the band. A game with no line is in no band. */
export function inBand(game, id) {
  const band = BY_ID.get(id)
  const m = margin(game)
  return !!band && m !== null && band.test(m)
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
