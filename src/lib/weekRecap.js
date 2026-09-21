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
    const top = scores.get(leaders[0]).points
    /* The best total under the new leaders, so a reversal can be told as a score:
       "James takes the week, 196 to 194" rather than only "James wins it on 196". */
    let nextPts = -1
    for (const [id, s] of scores) if (!leaders.includes(id) && s.points > nextPts) nextPts = s.points
    const nextIds = [...scores].filter(([id, s]) => !leaders.includes(id) && s.points === nextPts).map(([id]) => id)
    out.push({
      game_id: g.game_id,
      label: matchupLabel(g),
      instead: loserOf(g),
      actual: g.winner_abbr,
      leaders: leaders.map((id) => names.get(id) || `#${id}`),
      shared: leaders.length > 1,
      points: top,
      next: nextIds.length ? { names: nextIds.map((id) => names.get(id) || `#${id}`), points: nextPts } : null,
      // Nobody who actually won the week would still be on top.
      reversal: leaders.every((id) => !base.includes(id)),
    })
  }
  // A result that hands the week to someone else outright reads before one that only
  // makes it a tie. Both were recomputed; the order is a fact about them, not a ranking.
  return out.sort((a, b) => Number(b.reversal) - Number(a.reversal))
}

/**
 * Who had what riding on one game, biggest wager first. Only ever called on a game that
 * has kicked off, which is the only kind get_board returns rows for.
 */
export function stakes(game, rows) {
  return rows
    .filter((r) => r.game_id === game.game_id)
    .map((r) => ({
      player_id: r.player_id,
      name: r.player_name,
      pick: r.pick_abbr,
      confidence: r.confidence,
      won: !!game.winner_abbr && r.pick_abbr === game.winner_abbr,
    }))
    .sort((a, b) => b.confidence - a.confidence || a.player_id - b.player_id)
}

/** Kickoff order, ties on the clock broken by game id so the order never wobbles. */
function byKickoff(games) {
  return [...games].sort((a, b) => String(a.kickoff).localeCompare(String(b.kickoff)) || a.game_id - b.game_id)
}

/**
 * Where everyone stood after each game, in kickoff order.
 *
 * Kickoff order rather than the order games went final, because that is the only order
 * the data has. Close enough to tell the week as it happened, and labelled as what it is.
 *
 * `changes` counts the times a different player took the lead outright; a tie at the top
 * is not a change, and neither is the first player to lead alone. `lockedAt` is the game
 * after which the week's actual winners were on top and never left it, or null when the
 * week ended shared, since nobody took a shared lead "for good".
 */
export function race(games, rows, roster) {
  const order = byKickoff(games.filter((g) => g.winner_abbr))
  const pts = new Map(roster.map((p) => [p.id, 0]))
  const steps = order.map((g) => {
    for (const r of rows) {
      if (r.game_id === g.game_id && r.pick_abbr === g.winner_abbr && pts.has(r.player_id)) {
        pts.set(r.player_id, pts.get(r.player_id) + r.confidence)
      }
    }
    const points = Object.fromEntries(pts)
    const rank = {}
    for (const [id, v] of pts) rank[id] = 1 + [...pts.values()].filter((o) => o > v).length
    const top = Math.max(...pts.values())
    return {
      game_id: g.game_id,
      label: matchupLabel(g),
      points,
      rank,
      leaders: [...pts].filter(([, v]) => v === top).map(([id]) => id).sort((a, b) => a - b),
    }
  })

  let changes = 0
  let holder = null
  const led = new Map(roster.map((p) => [p.id, 0]))
  for (const s of steps) {
    if (s.leaders.length !== 1) continue
    led.set(s.leaders[0], led.get(s.leaders[0]) + 1)
    if (holder !== null && s.leaders[0] !== holder) changes += 1
    holder = s.leaders[0]
  }

  const last = steps[steps.length - 1]
  let lockedAt = null
  if (last && last.leaders.length === 1) {
    let i = steps.length - 1
    while (i > 0 && sameSet(steps[i - 1].leaders, last.leaders)) i -= 1
    lockedAt = i + 1
  }
  const most = Math.max(0, ...led.values())
  return {
    steps,
    changes,
    lockedAt,
    ledMost: { ids: [...led].filter(([, n]) => n === most && most > 0).map(([id]) => id), games: most },
  }
}

/**
 * The games all of you picked the same way, and how each went. A game only counts once
 * every seat has a pick on it, which after kickoff is always, thanks to the auto-pick.
 */
export function unanimous(games, rows, roster) {
  const seats = new Set(roster.map((p) => p.id))
  return byKickoff(games.filter((g) => g.winner_abbr))
    .map((g) => {
      const on = rows.filter((r) => r.game_id === g.game_id && seats.has(r.player_id))
      if (on.length !== seats.size || new Set(on.map((r) => r.pick_abbr)).size !== 1) return null
      return {
        game_id: g.game_id,
        label: matchupLabel(g),
        pick: on[0].pick_abbr,
        won: on[0].pick_abbr === g.winner_abbr,
        total: on.reduce((n, r) => n + r.confidence, 0),
      }
    })
    .filter(Boolean)
}

/** Picks nobody else in the family made, per player, biggest first. */
export function alone(games, rows, roster) {
  const graded = new Map(games.filter((g) => g.winner_abbr).map((g) => [g.game_id, g]))
  return roster.map((p) => {
    const picks = rows
      .filter((r) => r.player_id === p.id && graded.has(r.game_id))
      .filter((r) => rows.every((o) => o.game_id !== r.game_id || o.player_id === p.id || o.pick_abbr !== r.pick_abbr))
      .map((r) => {
        const g = graded.get(r.game_id)
        return { game_id: r.game_id, label: matchupLabel(g), pick: r.pick_abbr, confidence: r.confidence, won: r.pick_abbr === g.winner_abbr }
      })
      .sort((a, b) => b.confidence - a.confidence)
    return { id: p.id, name: p.name, color: p.color, team_id: p.team_id, picks, right: picks.filter((x) => x.won).length }
  })
}

/**
 * One player's week against the nearest rival: the runner-up if they won it outright,
 * whoever won it otherwise. Every game where the two banked a different number, split
 * into where you pulled ahead and where they got points back, biggest first. The nets
 * add up to the gap between you, which is the check that nothing was dropped.
 */
export function headToHead(games, rows, players, meId) {
  const me = players.find((p) => p.id === meId)
  if (!me) return null
  const rival = me.rank === 1
    ? players.find((p) => p.id !== meId && (p.rank === 1 || p.rank === 2)) || players.find((p) => p.id !== meId)
    : players.find((p) => p.rank === 1)
  if (!rival) return null
  const earned = (r, g) => (r && r.pick_abbr === g.winner_abbr ? r.confidence : 0)
  const diffs = byKickoff(games.filter((g) => g.winner_abbr))
    .map((g) => {
      const a = rows.find((r) => r.game_id === g.game_id && r.player_id === meId)
      const b = rows.find((r) => r.game_id === g.game_id && r.player_id === rival.id)
      const side = (r) => (r ? { pick: r.pick_abbr, confidence: r.confidence, won: r.pick_abbr === g.winner_abbr } : null)
      return { game_id: g.game_id, label: matchupLabel(g), mine: side(a), theirs: side(b), net: earned(a, g) - earned(b, g) }
    })
    .filter((d) => d.net !== 0)
  return {
    rival: { id: rival.id, name: rival.name },
    gap: me.points - rival.points,
    gained: diffs.filter((d) => d.net > 0).sort((a, b) => b.net - a.net),
    lost: diffs.filter((d) => d.net < 0).sort((a, b) => a.net - b.net),
  }
}

/** "A, B and C", the way every name list in the recap reads. */
export const andList = (xs) =>
  xs.length <= 1 ? xs[0] || '' : `${xs.slice(0, -1).join(', ')} and ${xs[xs.length - 1]}`

/**
 * Who called which upset, one sentence per set of callers: "Grant, Parker and Nicole called
 * FAU. Nicole called USF". It used to put every caller against every team, "Grant, Parker
 * and Nicole called FAU and USF", which read as if all three had both when only Nicole had
 * USF (copy audit, 2026-09-14). Takes upsets() output; names keep the order they came in.
 */
export function calledLine(list) {
  const groups = new Map()
  for (const u of list) {
    if (!u.calledBy.length) continue
    const key = [...u.calledBy].sort().join('|')
    if (!groups.has(key)) groups.set(key, { names: u.calledBy, teams: [] })
    groups.get(key).teams.push(u.winner)
  }
  return [...groups.values()].map((g) => `${andList(g.names)} called ${andList(g.teams)}`).join('. ')
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
    sweepGames: sweeps.map((g) => ({ game_id: g.game_id, label: matchupLabel(g), winner: g.winner_abbr })),
    slateSize: slate.length,
    race: complete ? race(slate, board, seats) : null,
    unanimous: complete ? unanimous(slate, board, seats) : [],
    alone: complete ? alone(slate, board, seats) : [],
  }
}
