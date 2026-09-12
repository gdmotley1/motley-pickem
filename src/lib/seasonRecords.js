/**
 * The record book, derived from get_season_picks' one row per player per graded game.
 *
 * Same rule as weekRecap.js and seasonStats.js: everything here is a count or a ratio
 * over rows the server returned. Nothing is characterised, and no superlative is claimed
 * that the numbers do not settle outright.
 *
 * THE SHAPE, AND WHY EVERY RECORD HAS THE SAME ONE
 *
 * Grant asked on 2026-09-11 for the holder plus the chasing pack, so that everybody sees
 * where THEY are on every record rather than only learning who won it. That forces one
 * rule on the whole file: a record is not "who holds it", it is a VALUE FOR ALL FOUR,
 * ranked. A record that can only name a winner does not belong here, and two candidates
 * were reshaped rather than admitted in that form:
 *
 *   "20-point disaster" was going to be a count of maximum-confidence losses, which is 0
 *   or 1 for most people most of the season and ranks four players into two buckets. It
 *   became "Biggest miss": the highest confidence each player has spent on a loser. Every
 *   player has one every week, it ranks cleanly, and it still names the moment.
 *
 *   "Heartbreaker" and "Stone cold" were a pair of counts over one-score games. They are
 *   one record now, "Coin flips", holding each player's record on games decided by three
 *   or fewer. Two halves of one question, and a record instead of a tally.
 *
 * Ties stand, here as everywhere. `holders` is a list.
 *
 * SORTING
 *
 * Each record says whether high or low wins via `lower`. The Fade and Slept on it are the
 * two where less is better, and getting that backwards would crown the worst player,
 * silently and plausibly. tests/records_check.mjs asserts the direction of both.
 */

import { ceiling } from './weekRecap.js'

/* ------------------------------------------------------------------ shaping ---- */

/** Group the flat rows by game, so a game knows all four picks on it. */
function byGame(rows) {
  const m = new Map()
  for (const r of rows) {
    if (!m.has(r.game_id)) {
      m.set(r.game_id, {
        game_id: r.game_id,
        week_no: r.week_no,
        week_label: r.week_label,
        kickoff: r.kickoff,
        home_abbr: r.home_abbr,
        away_abbr: r.away_abbr,
        home_id: r.home_id,
        away_id: r.away_id,
        home_score: r.home_score,
        away_score: r.away_score,
        winner_abbr: r.winner_abbr,
        favorite_abbr: r.favorite_abbr,
        underdog_abbr: r.underdog_abbr,
        spread_line: r.spread_line == null ? null : Number(r.spread_line),
        picks: [],
      })
    }
    m.get(r.game_id).picks.push({
      player_id: r.player_id,
      pick_abbr: r.pick_abbr,
      confidence: Number(r.confidence),
      auto: !!r.auto,
      won: r.pick_abbr === r.winner_abbr,
    })
  }
  /* Kickoff order across the whole season, which is what a streak has to walk. Ties on
     kickoff break by game id so the order is stable rather than whatever the server
     happened to return. */
  return [...m.values()].sort(
    (a, b) => new Date(a.kickoff) - new Date(b.kickoff) || Number(a.game_id) - Number(b.game_id),
  )
}

/** Margin of a finished game, or null if the scores never arrived. */
function margin(g) {
  if (g.home_score == null || g.away_score == null) return null
  return Math.abs(Number(g.home_score) - Number(g.away_score))
}

/** The team a player's pick was against. */
const otherSide = (g, abbr) => (abbr === g.home_abbr ? g.away_abbr : g.home_abbr)

/* ---------------------------------------------------------------- the record ---- */

/**
 * Turn a per-player map of {value, display, detail} into a ranked standing.
 *
 * @param lower  true when a smaller number is better.
 */
function standing(roster, valueFor, { lower = false } = {}) {
  const rows = roster.map((p) => {
    const v = valueFor(p) || {}
    return {
      id: p.id,
      name: p.name,
      color: p.color,
      team_id: p.team_id,
      value: v.value == null ? null : v.value,
      display: v.display ?? (v.value == null ? '—' : String(v.value)),
      detail: v.detail || '',
      teamId: v.teamId || null,
    }
  })
  /* A null is "this record does not apply to you", not "you scored zero". Nicole has no
     school, so Homer has nothing to say about her, and sorting her to the bottom on a
     zero would read as her being bad at it. Nulls sort last and never hold a record. */
  const ranked = [...rows].sort((a, b) => {
    if (a.value == null && b.value == null) return 0
    if (a.value == null) return 1
    if (b.value == null) return -1
    return lower ? a.value - b.value : b.value - a.value
  })
  const scored = ranked.filter((r) => r.value != null)
  const best = scored.length ? scored[0].value : null
  return {
    rows: ranked,
    best,
    holders: scored.filter((r) => r.value === best).map((r) => r.name),
    shared: scored.filter((r) => r.value === best).length > 1,
  }
}

/** Wrap a standing with its label and group. */
const record = (key, group, label, blurb, s) => ({ key, group, label, blurb, ...s })

/* ------------------------------------------------------------- per-player cuts ---- */

/** Every pick a player made, in kickoff order. */
function pickIndex(games) {
  const by = new Map()
  for (const g of games) {
    for (const p of g.picks) {
      if (!by.has(p.player_id)) by.set(p.player_id, [])
      by.get(p.player_id).push({ ...p, game: g })
    }
  }
  return by
}

/** Per player per week: points, correct, games, ceiling. */
function weekly(games) {
  const by = new Map()
  for (const g of games) {
    for (const p of g.picks) {
      const k = `${p.player_id}:${g.week_no}`
      if (!by.has(k)) {
        by.set(k, {
          player_id: p.player_id, week_no: g.week_no, label: g.week_label,
          points: 0, correct: 0, games: 0,
        })
      }
      const w = by.get(k)
      w.games += 1
      if (p.won) {
        w.correct += 1
        w.points += p.confidence
      }
    }
  }
  return [...by.values()].map((w) => ({ ...w, ceiling: ceiling(w.correct, w.games) }))
}

const fmt = (n) => (Number.isInteger(n) ? String(n) : n.toFixed(1))

/**
 * @param rows    get_season_picks output
 * @param roster  claimed seats, with id, name, color, team_id
 */
export function seasonRecords(rows, roster) {
  const games = byGame(rows || [])
  const seats = (roster || []).filter((p) => p.name)
  if (!games.length || !seats.length) return { records: [], family: null, weeks: 0 }

  const picks = pickIndex(games)
  const weeks = weekly(games)
  const mine = (p) => picks.get(p.id) || []
  const myWeeks = (p) => weeks.filter((w) => w.player_id === p.id)
  const out = []

  /* ============================================================ THE PERSONAL ==== */

  // The Anchor. Everyone spends a 20 every week on their surest thing; nobody has ever
  // known whose surest thing is actually surest.
  out.push(record('anchor', 'personal', 'The Anchor',
    'Your record on the game you put 20 points on',
    standing(seats, (p) => {
      /* Their TOP pick each week, not a hard-coded 20. In this pool the top is always 20
         because a week is always twenty games, and hard-coding it was the first version:
         it returns nothing at all on any week that is not exactly twenty, silently, and
         "your surest thing" is what the record actually means. */
      const top = new Map()
      for (const x of mine(p)) {
        const w = x.game.week_no
        if (!top.has(w) || x.confidence > top.get(w).confidence) top.set(w, x)
      }
      const at20 = [...top.values()]
      if (!at20.length) return {}
      const w = at20.filter((x) => x.won).length
      const last = at20[at20.length - 1]
      return {
        // Wins first, then rate, so 5-1 beats 2-0 rather than losing to it on percentage.
        value: w * 100 + Math.round((w / at20.length) * 99),
        display: `${w}-${at20.length - w}`,
        detail: `last: ${last.pick_abbr} in ${last.game.week_label}`,
      }
    })))

  // Homer. Only means anything for a seat with a school, and only over games their school
  // actually played on a slate.
  out.push(record('homer', 'personal', 'Homer',
    'Your record picking your own school',
    standing(seats, (p) => {
      if (!p.team_id) return { display: 'no school', detail: 'pick a team to unlock' }
      const theirs = mine(p).filter((x) => {
        const g = x.game
        return String(g.home_id) === String(p.team_id) || String(g.away_id) === String(p.team_id)
      })
      if (!theirs.length) return { display: 'not on a slate yet' }
      const took = theirs.filter((x) => {
        const g = x.game
        const abbr = String(g.home_id) === String(p.team_id) ? g.home_abbr : g.away_abbr
        return x.pick_abbr === abbr
      })
      const w = took.filter((x) => x.won).length
      return {
        value: took.length ? w * 100 + Math.round((w / took.length) * 99) : 0,
        display: took.length ? `${w}-${took.length - w}` : 'never backs them',
        detail: `backed them ${took.length} of ${theirs.length}`,
        teamId: p.team_id,
      }
    })))

  // The Fade. Points lost to ORDERING, not to picking: how far under your own ceiling you
  // finished. This is what explains an 17-3 week that still lost.
  out.push(record('fade', 'personal', 'The Fade',
    'Points left behind by ranking a right pick too low. Less is better.',
    standing(seats, (p) => {
      const ws = myWeeks(p)
      if (!ws.length) return {}
      const lost = ws.reduce((n, w) => n + (w.ceiling - w.points), 0)
      const worst = [...ws].sort((a, b) => (b.ceiling - b.points) - (a.ceiling - a.points))[0]
      return {
        value: lost,
        display: `-${lost}`,
        detail: `worst: -${worst.ceiling - worst.points} in ${worst.label}`,
      }
    }, { lower: true })))

  // Chalk. Who plays it safe and who takes dogs. Games with no line are excluded rather
  // than counted as chalk: with no favourite there was no safe side to take.
  out.push(record('chalk', 'personal', 'Chalk rate',
    'Share of your picks on the Vegas favourite',
    standing(seats, (p) => {
      const priced = mine(p).filter((x) => x.game.favorite_abbr)
      if (!priced.length) return {}
      const fav = priced.filter((x) => x.pick_abbr === x.game.favorite_abbr).length
      const pct = Math.round((fav / priced.length) * 100)
      return {
        value: pct,
        display: `${pct}%`,
        detail: pct >= 75 ? 'plays the chalk' : pct <= 55 ? 'takes the dogs' : 'mixes it up',
      }
    })))

  /* ================================================================ THE DRAMA ==== */

  // Biggest miss. Was "20-point disaster" and a count; see the note at the top of the file.
  out.push(record('miss', 'drama', 'Biggest miss',
    'The most confidence you have ever spent on a losing pick',
    standing(seats, (p) => {
      const lost = mine(p).filter((x) => !x.won)
      if (!lost.length) return {}
      const worst = lost.reduce((a, b) => (b.confidence > a.confidence ? b : a))
      return {
        value: worst.confidence,
        display: String(worst.confidence),
        detail: `${worst.pick_abbr} over ${otherSide(worst.game, worst.pick_abbr)}, ${worst.game.week_label}`,
      }
    })))

  // Lone wolf. Only really possible in a pool this small, which is what makes it worth
  // printing here and nowhere else.
  out.push(record('wolf', 'drama', 'Lone wolf',
    'Games where you were the only one who called it',
    standing(seats, (p) => {
      const alone = mine(p).filter(
        (x) => x.won && x.game.picks.filter((q) => q.pick_abbr === x.game.winner_abbr).length === 1,
      )
      if (!alone.length) return { value: 0, display: '0', detail: 'never gone it alone' }
      const best = alone.reduce((a, b) => (b.confidence > a.confidence ? b : a))
      return {
        value: alone.length,
        display: String(alone.length),
        detail: `best: ${best.pick_abbr} at ${best.confidence}, ${best.game.week_label}`,
      }
    })))

  // Upset special. The biggest line you have beaten from the wrong side of it.
  out.push(record('upset', 'drama', 'Upset special',
    'The biggest underdog you took that went on to win',
    standing(seats, (p) => {
      const dogs = mine(p).filter(
        (x) => x.won && x.game.spread_line != null && x.pick_abbr === x.game.underdog_abbr,
      )
      if (!dogs.length) return { value: 0, display: '—', detail: 'no dogs have hit' }
      const best = dogs.reduce((a, b) =>
        Math.abs(b.game.spread_line) > Math.abs(a.game.spread_line) ? b : a)
      const line = Math.abs(best.game.spread_line)
      return {
        value: line,
        display: `+${fmt(line)}`,
        detail: `${best.pick_abbr} over ${otherSide(best.game, best.pick_abbr)}, ${best.game.week_label}`,
      }
    })))

  // Coin flips. Heartbreaker and Stone cold folded into one record, as a record.
  out.push(record('flips', 'drama', 'Coin flips',
    'Your record on games decided by three points or fewer',
    standing(seats, (p) => {
      const close = mine(p).filter((x) => {
        const m = margin(x.game)
        return m != null && m <= 3
      })
      if (!close.length) return {}
      const w = close.filter((x) => x.won).length
      return {
        value: w * 100 + Math.round((w / close.length) * 99),
        display: `${w}-${close.length - w}`,
        detail: `${close.length} one-score game${close.length === 1 ? '' : 's'}`,
      }
    })))

  // Slept on it. An auto-pick is a game you never opened the app for.
  out.push(record('slept', 'drama', 'Slept on it',
    'Games that auto-picked because you never got to them. Less is better.',
    standing(seats, (p) => {
      const autos = mine(p).filter((x) => x.auto)
      return {
        value: autos.length,
        display: String(autos.length),
        detail: autos.length
          ? `latest: ${autos[autos.length - 1].game.week_label}`
          : 'has never missed one',
      }
    }, { lower: true })))

  /* ========================================================== THE TEAM LEDGER ==== */

  /** Points banked and lost per team, for one player. */
  function ledger(p) {
    const m = new Map()
    for (const x of mine(p)) {
      const id = x.pick_abbr === x.game.home_abbr ? x.game.home_id : x.game.away_id
      const k = x.pick_abbr
      if (!m.has(k)) m.set(k, { abbr: k, id, won: 0, lost: 0, n: 0 })
      const e = m.get(k)
      e.n += 1
      if (x.won) e.won += x.confidence
      else e.lost += x.confidence
    }
    return [...m.values()]
  }

  out.push(record('money', 'teams', 'Money team',
    'The team that has banked you the most points',
    standing(seats, (p) => {
      const best = ledger(p).filter((t) => t.won > 0).sort((a, b) => b.won - a.won)[0]
      if (!best) return {}
      return {
        value: best.won,
        display: `+${best.won}`,
        detail: `${best.abbr}, ${best.n} pick${best.n === 1 ? '' : 's'}`,
        teamId: best.id,
      }
    })))

  out.push(record('nemesis', 'teams', 'Nemesis',
    'The team that has cost you the most points',
    standing(seats, (p) => {
      const worst = ledger(p).filter((t) => t.lost > 0).sort((a, b) => b.lost - a.lost)[0]
      if (!worst) return { display: 'nothing has hurt yet' }
      return {
        value: worst.lost,
        display: `-${worst.lost}`,
        detail: `${worst.abbr}, ${worst.n} pick${worst.n === 1 ? '' : 's'}`,
        teamId: worst.id,
      }
    })))

  out.push(record('loyal', 'teams', 'Most picked',
    'The team you keep coming back to',
    standing(seats, (p) => {
      const top = ledger(p).sort((a, b) => b.n - a.n)[0]
      if (!top) return {}
      return {
        value: top.n,
        display: `${top.n}x`,
        detail: `${top.abbr}, ${top.won - top.lost >= 0 ? '+' : ''}${top.won - top.lost} net`,
        teamId: top.id,
      }
    })))

  /* ============================================================== THE CLASSIC ==== */

  out.push(record('best', 'classic', 'Best week',
    'The most points anyone has scored in one week',
    standing(seats, (p) => {
      const ws = myWeeks(p)
      if (!ws.length) return {}
      const b = ws.reduce((a, c) => (c.points > a.points ? c : a))
      return { value: b.points, display: String(b.points), detail: b.label }
    })))

  out.push(record('worst', 'classic', 'Worst week',
    'The fewest points anyone has scored in one week. Less is worse.',
    standing(seats, (p) => {
      const ws = myWeeks(p)
      if (!ws.length) return {}
      const b = ws.reduce((a, c) => (c.points < a.points ? c : a))
      return { value: b.points, display: String(b.points), detail: b.label }
    }, { lower: true })))

  out.push(record('sharp', 'classic', 'Sharpest week',
    'The most games anyone has called right in one week',
    standing(seats, (p) => {
      const ws = myWeeks(p)
      if (!ws.length) return {}
      const b = ws.reduce((a, c) => (c.correct > a.correct ? c : a))
      return {
        value: b.correct,
        display: `${b.correct}-${b.games - b.correct}`,
        detail: `${b.label}, ${b.points} pts`,
      }
    })))

  out.push(record('order', 'classic', 'Perfect order',
    'The closest anyone has come to banking every point their picks were worth',
    standing(seats, (p) => {
      const ws = myWeeks(p).filter((w) => w.ceiling > 0)
      if (!ws.length) return {}
      const b = ws.reduce((a, c) =>
        c.points / c.ceiling > a.points / a.ceiling ? c : a)
      const pct = Math.round((b.points / b.ceiling) * 100)
      return {
        value: pct,
        display: `${pct}%`,
        detail: pct === 100 ? `${b.label}, flawless` : b.label,
      }
    })))

  out.push(record('streak', 'classic', 'Hot streak',
    'The longest run of correct picks, game by game, across weeks',
    standing(seats, (p) => {
      let run = 0
      let best = 0
      let end = null
      for (const x of mine(p)) {
        if (x.won) {
          run += 1
          if (run > best) {
            best = run
            end = x.game
          }
        } else run = 0
      }
      return {
        value: best,
        display: String(best),
        detail: end ? `ended ${end.week_label}` : 'no run yet',
      }
    })))

  /* ============================================================= THE FAMILY ==== */
  /* Not per-player, so these do not get a standing. Four facts about the four of you. */

  const unanimousRight = games.filter(
    (g) => g.picks.length === seats.length && g.picks.every((q) => q.won))
  const unanimousWrong = games.filter(
    (g) => g.picks.length === seats.length && g.picks.every((q) => !q.won))
  const trap = games
    .map((g) => ({ g, missed: g.picks.filter((q) => !q.won).length }))
    .filter((x) => x.missed > 0)
    .sort((a, b) =>
      b.missed - a.missed ||
      /* Same number fooled: the one that cost the most is the bigger trap. */
      b.g.picks.reduce((n, q) => n + (q.won ? 0 : q.confidence), 0) -
        a.g.picks.reduce((n, q) => n + (q.won ? 0 : q.confidence), 0))[0]

  /** Weeks won against each other person, head to head. */
  const grid = seats.map((a) => ({
    id: a.id,
    name: a.name,
    color: a.color,
    team_id: a.team_id,
    vs: seats
      .filter((b) => b.id !== a.id)
      .map((b) => {
        let w = 0
        let l = 0
        for (const wk of new Set(weeks.map((x) => x.week_no))) {
          const A = weeks.find((x) => x.player_id === a.id && x.week_no === wk)
          const B = weeks.find((x) => x.player_id === b.id && x.week_no === wk)
          if (!A || !B) continue
          if (A.points > B.points) w += 1
          else if (A.points < B.points) l += 1
        }
        return { id: b.id, name: b.name, w, l }
      }),
  }))

  const family = {
    unanimousRight: unanimousRight.length,
    unanimousWrong: unanimousWrong.length,
    trap: trap
      ? {
          label: `${trap.g.away_abbr} at ${trap.g.home_abbr}`,
          week: trap.g.week_label,
          missed: trap.missed,
          winner: trap.g.winner_abbr,
          homeId: trap.g.home_id,
          awayId: trap.g.away_id,
          cost: trap.g.picks.reduce((n, q) => n + (q.won ? 0 : q.confidence), 0),
        }
      : null,
    grid,
  }

  return { records: out, family, weeks: new Set(weeks.map((w) => w.week_no)).size }
}

export const GROUPS = [
  ['personal', 'How you play'],
  ['drama', 'One game, one moment'],
  ['teams', 'The team ledger'],
  ['classic', 'The record book'],
]
