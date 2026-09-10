/**
 * One week's scoreboard, derived from what the board is already allowed to show.
 *
 * Kept out of the screen so it can be checked on its own: everything here is a pure
 * function of the three things Board already has in hand.
 */

/**
 * Everyone's week so far: points banked, record, and the most they can still finish on.
 *
 * The ceiling is the part worth explaining. A week is always worth the same total,
 * because confidence 1 to 20 is spent exactly once, so what a player has left is that
 * total minus every confidence value already revealed, plus whatever sits on a game that
 * has kicked off but is not final. Deriving it that way is what keeps it legal: an
 * unplayed game contributes its points to the ceiling without anyone learning which game
 * holds which number, which is exactly what get_board refuses to tell us.
 *
 * Winners come off the game rows, which the caller has already laid the live ESPN score
 * over, so a final counts here the moment it happens rather than when the sync job runs.
 *
 * One soft edge: between a kickoff and the auto-pick cron five minutes later, a player
 * who never submitted has no row for that game, so its points still count towards their
 * ceiling. It corrects itself on the next poll.
 */
export function weekScore(games, rows, roster) {
  const n = games.length
  const total = (n * (n + 1)) / 2
  const winners = new Map(games.map((g) => [g.game_id, g.winner_abbr]))

  const by = new Map(
    roster.map((p) => [
      p.id,
      {
        id: p.id,
        name: p.name,
        color: p.color,
        // Carried through for the scorebug, which draws each player's school mark and
        // sets their block to that school's other colour. Reading it off the roster
        // here keeps <WeekScore> a pure function of `score` with nothing else to join.
        team_id: p.team_id,
        points: 0,
        correct: 0,
        played: 0,
        spent: 0,
        open: 0,
      },
    ]),
  )

  for (const r of rows) {
    const s = by.get(r.player_id)
    if (!s) continue
    s.spent += r.confidence
    const winner = winners.get(r.game_id)
    if (!winner) {
      s.open += r.confidence // kicked off, not final: still on the table
      continue
    }
    s.played += 1
    if (r.pick_abbr === winner) {
      s.correct += 1
      s.points += r.confidence
    }
  }

  const players = [...by.values()]
    .map((s) => ({ ...s, live: Math.max(0, total - s.spent) + s.open }))
    // Same order the standings use: points, then games called right.
    .sort((a, b) => b.points - a.points || b.correct - a.correct)

  // Ties stand, so the lead is a value rather than a person: everyone on it is a leader.
  const best = players[0]?.points || 0

  /* Standings position, ties sharing a number and the next player skipping past them:
     128, 128, 124 is 1, 1, 3 rather than 1, 2, 3. Computed here rather than in the
     scorebug because the sort that decides it already lives here, and two places
     deriving a rank is how they come to disagree. Ranked on points alone: `correct` is
     a tiebreak for row ORDER only, and the pool has no tiebreaker. */
  let rank = 0
  players.forEach((p, i) => {
    if (i === 0 || p.points !== players[i - 1].points) rank = i + 1
    p.rank = rank
    p.shared = false
  })
  for (const p of players) p.shared = players.filter((q) => q.rank === p.rank).length > 1

  /* How many games are on right now, for the LIVE chip. A game that has kicked off with
     no winner yet is in progress; `withLive` has already laid ESPN's view over the row,
     so this is as current as the last poll. */
  const playing = games.filter((g) => g.locked && !g.winner_abbr).length
  const graded = games.filter((g) => g.winner_abbr).length

  return { total, best, players, playing, graded, slateSize: n }
}
