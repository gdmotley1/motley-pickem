/**
 * Everything the week screen says about a finished week.
 *
 * The house rule for this file: nothing in here is an opinion. Every value is either a
 * count over the picks and results, or a what-if that is actually recomputed rather than
 * asserted. That constraint came from a real failure. An earlier draft of this screen
 * claimed "UNLV at Hawaii decided it" because that game carried a seven point swing
 * between the top two and the final margin was seven. It reads well and it is empty:
 * the margin is the sum of every game they differed on, so any game with a seven point
 * swing has an equal claim, and there were three. `decisiveGames` replaces that with the
 * question that does have an answer, by flipping one result at a time and re-running the
 * standings to see whether the winner actually changes.
 *
 * Kept out of the screen so the gate can check it: tests/recap_check.mjs runs every
 * function here against a saved copy of the real Week 1 board.
 */

/**
 * The most a ranking could have banked, given how many picks came in.
 *
 * A week spends confidence 1..n exactly once, so a player who got c games right could at
 * best have put their top c values on those c games: n + (n-1) + ... + (n-c+1). Comparing
 * what they actually scored against that separates the two halves of this game, picking
 * and ranking, which the raw point total mixes together. It is also the one stat here
 * that can flatter someone who finished last, and in Week 1 it did.
 */
export function ceiling(correct, games) {
  const n = Math.max(0, games | 0)
  const c = Math.min(Math.max(0, correct | 0), n)
  if (!c) return 0
  return (c * (2 * n - c + 1)) / 2
}

/** The team that did not win. Used to flip a result for the counterfactuals. */
function loserOf(game) {
  return game.winner_abbr === game.home_abbr ? game.away_abbr : game.home_abbr
}

export function matchupLabel(game) {
  return `${game.away_abbr} at ${game.home_abbr}`
}

/** Points each player would hold if `winners` were the results. */
function scoreWith(rows, winners) {
  const by = new Map()
  for (const r of rows) {
    const s = by.get(r.player_id) || { points: 0, correct: 0, played: 0 }
    const w = winners.get(r.game_id)
    if (w) {
      s.played += 1
      if (r.pick_abbr === w) {
        s.points += r.confidence
        s.correct += 1
      }
    }
    by.set(r.player_id, s)
  }
  return by
}

/** Everyone tied on the top score. Ties stand, so this is a set, never one person. */
function leadersOf(scores) {
  let best = -1
  for (const s of scores.values()) if (s.points > best) best = s.points
  const out = []
  for (const [id, s] of scores) if (s.points === best) out.push(id)
  return out.sort((a, b) => a - b)
}

const sameSet = (a, b) => a.length === b.length && a.every((x, i) => x === b[i])

/**
 * Which single results would have changed who won the week.
 *
 * For each game, flip the winner, re-score everybody, and keep the game only if the set
 * of leaders comes out different. That is the honest version of "the game that decided
 * it": a game is in this list because the week genuinely turns on it, not because it
 * happened to carry a swing the same size as the final margin.
 *
 * Most weeks this list is short. Some weeks it is empty, and that is worth printing too:
 * a week nobody could have changed with one result was won on the whole slate.
 */
export function decisiveGames(games, rows, names) {
  const winners = new Map(games.map((g) => [g.game_id, g.winner_abbr]))
  const base = leadersOf(scoreWith(rows, winners))
  const out = []

  for (const g of games) {
    if (!g.winner_abbr) continue
    const alt = new Map(winners)
    alt.set(g.game_id, loserOf(g))
    const scores = scoreWith(rows, alt)
    const leaders = leadersOf(scores)
    if (sameSet(leaders, base)) continue
    out.push({
      game_id: g.game_id,
      label: matchupLabel(g),
      instead: loserOf(g),
      actual: g.winner_abbr,
      leaders: leaders.map((id) => names.get(id) || `#${id}`),
      shared: leaders.length > 1,
      points: leaders.map((id) => scores.get(id).points)[0],
    })
  }
  return out
}

/**
 * A game where the favourite lost, and who had it.
 *
 * `favorite_abbr` is frozen at kickoff by the sync job, so a game that never had a line
 * has no favourite and cannot be an upset. Those are skipped rather than guessed at.
 */
export function upsets(games, rows) {
  const out = []
  for (const g of games) {
    if (!g.winner_abbr || !g.favorite_abbr) continue
    if (g.favorite_abbr === g.winner_abbr) continue
    const called = rows.filter((r) => r.game_id === g.game_id && r.pick_abbr === g.winner_abbr)
    out.push({
      game_id: g.game_id,
      label: matchupLabel(g),
      winner: g.winner_abbr,
      line: g.spread_line == null ? null : Math.abs(Number(g.spread_line)),
      calledBy: called.map((r) => r.player_name),
      points: called.map((r) => r.confidence),
    })
  }
  return out.sort((a, b) => (b.line || 0) - (a.line || 0))
}

/**
 * Per-player detail, including where each person gained and lost against the field.
 *
 * "Against the field" is the comparison worth making. A player's biggest correct pick is
 * almost always just whatever they put 20 on, which says nothing. The game where they
 * took the most points out of everybody else is a real edge, and it is symmetric: the
 * same arithmetic finds where the week got away from them.
 */
export function playerBreakdown(games, rows, roster) {
  const winners = new Map(games.map((g) => [g.game_id, g.winner_abbr]))
  const byGame = new Map()
  for (const r of rows) {
    if (!byGame.has(r.game_id)) byGame.set(r.game_id, [])
    byGame.get(r.game_id).push(r)
  }
  const gameById = new Map(games.map((g) => [g.game_id, g]))
  const earned = (r) => (r.pick_abbr === winners.get(r.game_id) ? r.confidence : 0)

  return roster.map((p) => {
    const mine = rows.filter((r) => r.player_id === p.id)
    let points = 0
    let correct = 0
    let best = null
    let worst = null
    let alone = 0
    let autos = 0

    for (const r of mine) {
      const got = earned(r)
      points += got
      if (got) correct += 1
      if (r.auto) autos += 1

      const others = (byGame.get(r.game_id) || []).filter((o) => o.player_id !== p.id)
      if (others.length) {
        const avg = others.reduce((n, o) => n + earned(o), 0) / others.length
        const edge = got - avg
        const entry = {
          game_id: r.game_id,
          label: matchupLabel(gameById.get(r.game_id)),
          pick: r.pick_abbr,
          confidence: r.confidence,
          won: got > 0,
          edge: Math.round(edge * 10) / 10,
        }
        // Ties happen, and picking whichever game kicked off first is arbitrary. Break
        // toward the one the player put more confidence on: that is the game they had
        // more say in and the one they will remember. In Week 1 this was a real tie,
        // Miami at Stanford and Wisconsin at Notre Dame both -16.0 for Nicole.
        if (!best || edge > best.edge || (edge === best.edge && r.confidence > best.confidence))
          best = entry
        if (!worst || edge < worst.edge || (edge === worst.edge && r.confidence > worst.confidence))
          worst = entry
        if (got && others.every((o) => o.pick_abbr !== r.pick_abbr)) alone += 1
      }
    }

    const games_n = mine.length
    const cap = ceiling(correct, games_n)
    return {
      ...p,
      points,
      correct,
      games: games_n,
      wrong: games_n - correct,
      ceiling: cap,
      captured: cap ? Math.round((points / cap) * 100) : 0,
      soloRight: alone,
      autos,
      best: best && best.edge > 0 ? best : null,
      worst: worst && worst.edge < 0 ? worst : null,
    }
  })
}

/**
 * The whole recap. `complete` gates the screen: the write-up only appears once every
 * game in the slate has a winner, so no number in it can move after someone has read it.
 */
export function weekRecap(games, rows, roster) {
  const slate = games || []
  const board = rows || []
  const seats = roster || []
  const complete = slate.length > 0 && slate.every((g) => g.winner_abbr)

  const names = new Map(seats.map((p) => [p.id, p.name]))
  const players = playerBreakdown(slate, board, seats).sort(
    (a, b) => b.points - a.points || b.correct - a.correct,
  )

  let lastPts = null
  let lastPos = 0
  players.forEach((p, i) => {
    if (p.points !== lastPts) {
      lastPos = i + 1
      lastPts = p.points
    }
    p.rank = lastPos
  })

  const leaders = players.filter((p) => p.rank === 1)
  const runnerUp = players.find((p) => p.rank !== 1) || null
  const favWins = slate.filter((g) => g.favorite_abbr && g.favorite_abbr === g.winner_abbr).length
  const lined = slate.filter((g) => g.favorite_abbr && g.winner_abbr).length

  // Games nobody in the family got right, and games everybody did.
  const played = new Set(board.map((r) => r.game_id))
  const scored = slate.filter((g) => g.winner_abbr && played.has(g.game_id))
  const whiffs = scored.filter((g) =>
    board.every((r) => r.game_id !== g.game_id || r.pick_abbr !== g.winner_abbr),
  )
  const sweeps = scored.filter((g) =>
    board.every((r) => r.game_id !== g.game_id || r.pick_abbr === g.winner_abbr),
  )

  return {
    complete,
    players,
    leaders,
    margin: runnerUp ? players[0].points - runnerUp.points : 0,
    shared: leaders.length > 1,
    decisive: complete ? decisiveGames(slate, board, names) : [],
    upsets: complete ? upsets(slate, board) : [],
    chalk: { won: favWins, of: lined },
    whiffs: whiffs.map((g) => ({ game_id: g.game_id, label: matchupLabel(g), winner: g.winner_abbr })),
    sweeps: sweeps.length,
    slateSize: slate.length,
  }
}
