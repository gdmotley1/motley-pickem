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
  return { total, best, players }
}
