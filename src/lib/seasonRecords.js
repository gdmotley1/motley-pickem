/**
 * The record book. Twelve records, each one a sentence anyone can read.
 *
 * WHAT WENT WRONG THE FIRST TIME, BECAUSE IT IS THE POINT OF THIS FILE
 *
 * The first version had seventeen records and Grant's verdict on seeing it was "literally
 * none of these stats makes sense at all". He was right. They were things like The Fade
 * (points lost by ranking a correct pick too low), Chalk rate, Perfect order and The
 * Anchor: every one needed a sentence of explanation, and the sentence had just been
 * deleted when the tall cards became squares. What shipped was seventeen invented terms
 * over seventeen bare numbers.
 *
 * Every record here is one Grant picked off a list, in his words, and every one can be
 * read cold: "Most points in a week. 195. Grant." If a record ever needs explaining
 * again, it does not belong in this file.
 *
 * WHERE EACH ONE COMES FROM
 *
 * Eight of the twelve come from get_season, which the tab already fetches: one row per
 * player per week with points, correct and games. Four need the picks themselves and so
 * need migration 015. That split is deliberate rather than incidental. It means the book
 * is not empty while 015 waits to be pasted, and it means losing the picks for any reason
 * still leaves two thirds of a record book standing.
 *
 * TIES, AND RECORDS NOBODY HAS SET
 *
 * Ties stand, so `holders` is a list. Separately, a record nobody has set yet is
 * UNCLAIMED, not a four-way tie on zero. Nobody has thrown a perfect week, so "Perfect
 * week, 0, all four" is an absence dressed as a statistic, which is exactly the kind of
 * thing that made the first book nonsense.
 */

/* ------------------------------------------------------------------ shaping ---- */

/** One row per player per week, from get_season. */
function byWeek(rows) {
  return (rows || [])
    .map((r) => ({
      player_id: r.player_id,
      week_no: Number(r.week_no),
      label: r.week_label,
      points: Number(r.points),
      correct: Number(r.correct),
      games: Number(r.games),
    }))
    .filter((w) => w.games > 0)
}

/** Group pick rows by game, so a game knows every pick made on it. */
function byGame(rows) {
  const m = new Map()
  for (const r of rows || []) {
    if (!m.has(r.game_id)) {
      m.set(r.game_id, {
        game_id: r.game_id,
        kickoff: r.kickoff,
        winner_abbr: r.winner_abbr,
        underdog_abbr: r.underdog_abbr,
        spread_line: r.spread_line == null ? null : Number(r.spread_line),
        picks: [],
      })
    }
    m.get(r.game_id).picks.push({
      player_id: r.player_id,
      pick_abbr: r.pick_abbr,
      confidence: Number(r.confidence),
      won: r.pick_abbr === r.winner_abbr,
    })
  }
  /* Kickoff order across the whole season, which is what a streak has to walk. Ties on
     kickoff break by id so the order is stable rather than whatever the server returned. */
  return [...m.values()].sort(
    (a, b) => new Date(a.kickoff) - new Date(b.kickoff) || Number(a.game_id) - Number(b.game_id),
  )
}

/* ---------------------------------------------------------------- the record ---- */

/**
 * Rank every seat on one record.
 *
 * @param lower  a smaller number wins it. Only "Fewest points in a week" uses this.
 */
function standing(seats, valueFor, { lower = false } = {}) {
  const rows = seats.map((p) => {
    const v = valueFor(p) || {}
    return {
      id: p.id,
      name: p.name,
      color: p.color,
      team_id: p.team_id,
      value: v.value == null ? null : v.value,
      display: v.display ?? (v.value == null ? '—' : String(v.value)),
    }
  })
  const ranked = [...rows].sort((a, b) => {
    if (a.value == null && b.value == null) return 0
    if (a.value == null) return 1
    if (b.value == null) return -1
    return lower ? a.value - b.value : b.value - a.value
  })
  const scored = ranked.filter((r) => r.value != null)
  const best = scored.length ? scored[0].value : null

  // Nobody has set it. See the note at the top of the file.
  const unclaimed = !scored.length || (!lower && best === 0)

  return {
    rows: ranked,
    best,
    unclaimed,
    holders: unclaimed ? [] : scored.filter((r) => r.value === best).map((r) => r.name),
    shared: !unclaimed && scored.filter((r) => r.value === best).length > 1,
  }
}

const record = (key, group, label, s) => ({ key, group, label, ...s })
const fmt = (n) => (Number.isInteger(n) ? String(n) : n.toFixed(1))

/**
 * @param seasonRows  get_season output. Required.
 * @param pickRows    get_season_picks output, or null before migration 015 is pasted.
 * @param roster      claimed seats
 */
export function seasonRecords(seasonRows, pickRows, roster) {
  const weeks = byWeek(seasonRows)
  const seats = (roster || []).filter((p) => p.name)
  if (!weeks.length || !seats.length) return { records: [], weeks: 0, hasPicks: false }

  const mine = (p) => weeks.filter((w) => w.player_id === p.id)
  const weekNos = [...new Set(weeks.map((w) => w.week_no))].sort((a, b) => a - b)
  const out = []

  /* ================================================================ BY THE WEEK ==== */

  out.push(record('week_points', 'week', 'Most points in a week',
    standing(seats, (p) => {
      const ws = mine(p)
      if (!ws.length) return {}
      return { value: Math.max(...ws.map((w) => w.points)) }
    })))

  out.push(record('week_record', 'week', 'Best record in a week',
    standing(seats, (p) => {
      const ws = mine(p)
      if (!ws.length) return {}
      const b = ws.reduce((a, c) => (c.correct > a.correct ? c : a))
      return { value: b.correct, display: `${b.correct}-${b.games - b.correct}` }
    })))

  /* The only record where the lowest number wins it, and the only one where holding it is
     bad news. Grant asked for it by name. */
  out.push(record('week_low', 'week', 'Fewest points in a week',
    standing(seats, (p) => {
      const ws = mine(p)
      if (!ws.length) return {}
      return { value: Math.min(...ws.map((w) => w.points)) }
    }, { lower: true })))

  out.push(record('blowout', 'week', 'Biggest blowout',
    standing(seats, (p) => {
      let best = 0
      for (const n of weekNos) {
        const meThis = weeks.find((w) => w.player_id === p.id && w.week_no === n)
        if (!meThis) continue
        const others = weeks.filter((w) => w.week_no === n && w.player_id !== p.id)
        if (!others.length) continue
        const margin = meThis.points - Math.max(...others.map((w) => w.points))
        if (margin > best) best = margin
      }
      return { value: best }
    })))

  /* ============================================================== BY THE SEASON ==== */

  out.push(record('weeks_won', 'season', 'Most weeks won',
    standing(seats, (p) => {
      let n = 0
      for (const wk of weekNos) {
        const inWeek = weeks.filter((w) => w.week_no === wk)
        const top = Math.max(...inWeek.map((w) => w.points))
        // Ties stand, so a shared week counts for everyone who shared it.
        if (inWeek.some((w) => w.player_id === p.id && w.points === top)) n += 1
      }
      return { value: n }
    })))

  out.push(record('record', 'season', 'Best overall record',
    standing(seats, (p) => {
      const ws = mine(p)
      if (!ws.length) return {}
      const c = ws.reduce((n, w) => n + w.correct, 0)
      const g = ws.reduce((n, w) => n + w.games, 0)
      return { value: c, display: `${c}-${g - c}` }
    })))

  out.push(record('points', 'season', 'Most points in a season',
    standing(seats, (p) => {
      const ws = mine(p)
      if (!ws.length) return {}
      return { value: ws.reduce((n, w) => n + w.points, 0) }
    })))

  /* A week is always twenty games in this pool, per memory/decisions.md, and `games` here
     counts only the ones already GRADED. Without the floor, the first final of a Thursday
     night makes whoever called it 1-for-1 and hands them a perfect week. */
  out.push(record('perfect', 'season', 'Perfect week',
    standing(seats, (p) => {
      const n = mine(p).filter((w) => w.games >= 20 && w.correct === w.games).length
      return { value: n, display: n ? `${n}x` : '0' }
    })))

  /* ============================================================== SINGLE GAMES ==== */
  /* The four that need the picks, and therefore migration 015. Everything above works
     from the aggregates the tab already fetches. */

  const games = byGame(pickRows)
  const hasPicks = games.length > 0

  if (hasPicks) {
    const picksOf = new Map()
    for (const g of games) {
      for (const pk of g.picks) {
        if (!picksOf.has(pk.player_id)) picksOf.set(pk.player_id, [])
        picksOf.get(pk.player_id).push({ ...pk, game: g })
      }
    }
    const theirs = (p) => picksOf.get(p.id) || []

    out.push(record('streak', 'games', 'Longest winning streak',
      standing(seats, (p) => {
        let run = 0
        let best = 0
        for (const x of theirs(p)) {
          run = x.won ? run + 1 : 0
          if (run > best) best = run
        }
        return { value: best }
      })))

    out.push(record('upset', 'games', 'Biggest upset called',
      standing(seats, (p) => {
        const hit = theirs(p).filter(
          (x) => x.won && x.game.spread_line != null && x.pick_abbr === x.game.underdog_abbr)
        if (!hit.length) return { value: 0, display: '—' }
        const line = Math.max(...hit.map((x) => Math.abs(x.game.spread_line)))
        return { value: line, display: `+${fmt(line)}` }
      })))

    out.push(record('worst_pick', 'games', 'Worst pick',
      standing(seats, (p) => {
        const lost = theirs(p).filter((x) => !x.won)
        if (!lost.length) return {}
        return { value: Math.max(...lost.map((x) => x.confidence)) }
      })))

    out.push(record('lone', 'games', 'Only one who called it',
      standing(seats, (p) => ({
        value: theirs(p).filter(
          (x) => x.won &&
            x.game.picks.filter((q) => q.pick_abbr === x.game.winner_abbr).length === 1,
        ).length,
      }))))
  }

  return { records: out, weeks: weekNos.length, hasPicks }
}

export const GROUPS = [
  ['week', 'By the week'],
  ['season', 'By the season'],
  ['games', 'Single games'],
]
