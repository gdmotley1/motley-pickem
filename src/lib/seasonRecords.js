/**
 * The record book: everyone's numbers, the Hall of fame and the Hall of shame.
 *
 * WHAT GRANT CHOSE, AND HOW
 *
 * Every entry here came off a ballot he filled in on 2026-09-12, and the layouts off
 * numbered boards the same evening: 7, the trophy room for the Hall of fame; 10, the red
 * panel for the Hall of shame; and for everyone's numbers first headlines, then, once they
 * were live and read as "clunky and hard to read, like, what the record actually is", 4,
 * ranked ladders. Each key is also the file name of his badge art, so a record added here
 * without art fails tests/records_check.mjs.
 *
 * The version before this had twelve records drawn as tiny squares, and the one before
 * that had seventeen invented statistics ("literally none of these stats makes sense at
 * all"). Every label must still read cold: "Worst miss. 20 on OU. Parker."
 *
 * WEEKS
 *
 * Anything "in a week" counts finished weeks only, via finishedWeeks. Season totals, the
 * season record and every pick record count every graded game. See seasonStats.js for
 * the bug that split them.
 *
 * TIES, NULLS AND NOBODY-YET
 *
 * Ties stand, so a record has leaders, plural. A player a record does not apply to (never
 * lost a pick, so no worst miss) has a null, sorts last and never leads; returning zero
 * would rank them as worst at it. An award nobody has earned is UNCLAIMED, drawn as up for
 * grabs, never as a tie on zero.
 *
 * WITHOUT THE PICKS
 *
 * Seven of the seventeen need get_season_picks (migration 015). If that call fails, they
 * are left out rather than shown as unclaimed, because "up for grabs" would be a claim
 * this book cannot back. The rest come from get_season, which the tab already has.
 */

import { SLATE, finishedWeeks } from './seasonStats.js'

/* ------------------------------------------------------------------ the lists ---- */

/** Everyone's numbers, in the order the tab draws them. */
export const NUMBERS = [
  { key: 'best_week', label: 'Most points in a week' },
  { key: 'best_record', label: 'Best record in a week' },
  { key: 'low_week', label: 'Fewest points in a week', lower: true, bad: true },
  { key: 'streak', label: 'Longest winning streak', picks: true },
  { key: 'worst_miss', label: 'Worst miss', bad: true, picks: true },
  { key: 'my_upset', label: 'Biggest upset you called', picks: true },
  { key: 'weeks_won', label: 'Weeks won' },
  { key: 'season_record', label: 'Season record' },
]

/** The Hall of fame, easiest first, which is the order it fills up in. */
export const FAME = [
  { key: 'season_points', label: 'Most points in a season' },
  // Grant, 2026-09-25: "take off the 'in a week' line on biggest margin of victory so it
  // even". It was the one label that ran to three lines in a trophy-room card while every
  // other one took two. The week is still named in the detail under it ("Won Week 2 by 33").
  { key: 'margin', label: 'Biggest margin of victory' },
  { key: 'big_upset', label: 'Biggest upset called', picks: true },
  { key: 'only_one', label: 'Only one who called it', picks: true },
  { key: 'three_upsets', label: 'Three upsets in one week', picks: true },
  { key: 'two_td_upset', label: 'Two-touchdown upset', picks: true },
  { key: 'win_by_20', label: 'Won a week by 20 or more' },
  { key: 'perfect_week', label: 'Perfect week' },
]

export const SHAME = [{ key: 'lost_20', label: 'Lost your 20', picks: true }]

/** Every badge the book can draw, one art file each. */
export const BADGE_KEYS = [...NUMBERS, ...FAME, ...SHAME].map((x) => x.key)

/* ---------------------------------------------------------------- formatting ---- */

const num = (v) => Number(v) || 0
const fmt = (n) => (Number.isInteger(n) ? String(n) : n.toFixed(1))
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`
const andList = (xs) => (xs.length <= 1 ? xs[0] || '' : `${xs.slice(0, -1).join(', ')} and ${xs[xs.length - 1]}`)
const DASH = '–'

/* ------------------------------------------------------------------ shaping ---- */

function shapeWeeks(rows) {
  return (rows || [])
    .map((r) => ({
      player_id: r.player_id,
      week_no: num(r.week_no),
      label: r.week_label,
      points: num(r.points),
      correct: num(r.correct),
      games: num(r.games),
    }))
    .filter((w) => w.games > 0)
}

/** Every graded pick, in kickoff order across the season, which is what a streak walks. */
function shapePicks(rows) {
  return (rows || [])
    .map((r) => {
      const spread = r.spread_line == null ? null : Math.abs(Number(r.spread_line))
      return {
        player_id: r.player_id,
        week_no: num(r.week_no),
        label: r.week_label,
        game_id: r.game_id,
        kickoff: r.kickoff,
        team: r.pick_abbr,
        stake: num(r.confidence),
        won: r.pick_abbr === r.winner_abbr,
        dog: spread != null && r.pick_abbr === r.underdog_abbr,
        spread,
      }
    })
    .sort((a, b) => new Date(a.kickoff) - new Date(b.kickoff) || Number(a.game_id) - Number(b.game_id))
}

/* ------------------------------------------------------------------ ranking ---- */

/**
 * Rank every seat on one record, best first. Standard competition ranking, so a tie
 * shares a place (1, 1, 3). Nulls sort last and hold nothing.
 *
 * On a bad-news record the top of the ranking is the WORST: the biggest miss, or the
 * fewest points, which is why `lower` and `bad` are separate.
 */
function rank(rows, { lower = false, bad = false } = {}) {
  const vals = rows.map((r) => r.value).filter((v) => v != null)
  for (const r of rows) {
    r.rank = r.value == null ? null : 1 + vals.filter((v) => (lower ? v < r.value : v > r.value)).length
    r.mark = null
    if (r.rank === 1) r.mark = bad ? 'worst' : r.value > 0 ? 'best' : null
  }
  // Array sort is stable, so a tie keeps seat order.
  return [...rows].sort((a, b) => {
    if (a.value == null && b.value == null) return 0
    if (a.value == null) return 1
    if (b.value == null) return -1
    return lower ? a.value - b.value : b.value - a.value
  })
}

/* What a row says instead of a number when the record does not apply to that person. */
const NONE = { worst_miss: 'No misses yet' }

/* The one line a ladder row may carry under its name, by what kind of detail it is.
   Grant, looking at the first ladders: "make everything uniform ... no weird text or
   spaces. take the of 1 out of week". So a card's rows all follow one rule:
     WEEKLY  the week it happened: every row shows its week, or, when every row's week is
             the same week, none of them do
     TEAM    the team it was on, which is the record itself: every row shows it
     the rest ("in a row", "of 1", season record) print the number and nothing else */
const WEEKLY = new Set(['best_week', 'best_record', 'low_week'])
const TEAM = new Set(['worst_miss', 'my_upset'])

/**
 * One record as a ladder: every seat, best first. Grant picked the ladder (option 4) on
 * 2026-09-12 after the headline version read as "clunky and hard to read, like, what the
 * record actually is".
 *
 *   lead   holds the record, so the row is drawn big (gold, or red on a bad-news record)
 *   note   the line under the name, or '' (see WEEKLY and TEAM)
 *   empty  the words under the name for someone the record does not apply to, whose
 *          number column then shows a dash like everyone else's shows a number
 */
export function rungs(key, rows) {
  const valued = rows.filter((r) => r.value != null)
  const sameWeek = valued.every((r) => r.detail === (valued[0] && valued[0].detail))
  return rows.map((r) => {
    const empty = r.value == null ? r.detail || NONE[key] || 'None yet' : ''
    let note = ''
    if (!empty && TEAM.has(key)) note = r.detail
    if (!empty && WEEKLY.has(key) && !sameWeek) note = r.detail
    return { ...r, lead: !!r.mark, note, empty }
  })
}

/* ------------------------------------------------------------------- the book ---- */

/**
 * @param seasonRows  get_season output. Required.
 * @param pickRows    get_season_picks output, or null if that call failed.
 * @param roster      claimed seats: { id, name, color, team_id }
 */
export function seasonRecords(seasonRows, pickRows, roster) {
  const seats = (roster || []).filter((p) => p && p.name)
  const weeks = shapeWeeks(seasonRows)
  if (!weeks.length || !seats.length) {
    return { numbers: [], fame: [], shame: [], weeks: 0, hasPicks: false }
  }

  const done = finishedWeeks(seasonRows)
  const doneNos = [...done].sort((a, b) => a - b)
  const lastDone = doneNos.length ? doneNos[doneNos.length - 1] : 0
  const picks = shapePicks(pickRows)
  const hasPicks = picks.length > 0
  const label = new Map(weeks.map((w) => [w.week_no, w.label]))
  const seatOf = new Map(seats.map((p) => [p.id, p]))
  const person = (p) => ({ id: p.id, name: p.name, color: p.color, team_id: p.team_id })

  const finishedFor = (p) => weeks.filter((w) => w.player_id === p.id && done.has(w.week_no))
  const picksFor = (p) => picks.filter((x) => x.player_id === p.id)
  const topOf = (n) => Math.max(...weeks.filter((w) => w.week_no === n).map((w) => w.points))

  /* ------------------------------------------------------ everyone's numbers ---- */

  const calc = {
    best_week(p) {
      const ws = finishedFor(p)
      if (!ws.length) return {}
      const b = ws.reduce((a, c) => (c.points >= a.points ? c : a))
      return { value: b.points, display: String(b.points), detail: b.label }
    },
    best_record(p) {
      const ws = finishedFor(p)
      if (!ws.length) return {}
      const b = ws.reduce((a, c) => (c.correct >= a.correct ? c : a))
      return { value: b.correct, display: `${b.correct}-${b.games - b.correct}`, detail: b.label }
    },
    // Needs two finished weeks. With one, everybody's fewest is the same number as their
    // most, which reads as a bug.
    low_week(p) {
      const ws = finishedFor(p)
      if (ws.length < 2) return {}
      const b = ws.reduce((a, c) => (c.points <= a.points ? c : a))
      return { value: b.points, display: String(b.points), detail: b.label }
    },
    streak(p) {
      const mine = picksFor(p)
      if (!mine.length) return {}
      let run = 0
      let best = 0
      for (const x of mine) {
        run = x.won ? run + 1 : 0
        if (run > best) best = run
      }
      return { value: best, display: String(best), detail: 'in a row' }
    },
    // Stake and team only, per Grant: "8 on GT". Not the opponent, not the score. The 8
    // is the number column, so the note is the team alone, the same as Biggest upset you
    // called beside it (copy audit, 2026-09-14).
    worst_miss(p) {
      const lost = picksFor(p).filter((x) => !x.won)
      if (!lost.length) return {}
      const w = lost.reduce((a, c) => (c.stake >= a.stake ? c : a))
      return { value: w.stake, display: String(w.stake), detail: w.team }
    },
    my_upset(p) {
      const ups = picksFor(p).filter((x) => x.won && x.dog)
      if (!ups.length) return { detail: 'None yet' }
      const u = ups.reduce((a, c) => (c.spread >= a.spread ? c : a))
      return { value: u.spread, display: `+${fmt(u.spread)}`, detail: u.team }
    },
    // Ties stand, so a shared week counts for everyone who shared it.
    weeks_won(p) {
      if (!doneNos.length) return {}
      const n = doneNos.filter((wk) =>
        weeks.some((w) => w.player_id === p.id && w.week_no === wk && w.points === topOf(wk)),
      ).length
      return { value: n, display: String(n), detail: `of ${doneNos.length}` }
    },
    // Live: every graded pick, finished week or not.
    season_record(p) {
      const ws = weeks.filter((w) => w.player_id === p.id)
      if (!ws.length) return {}
      const c = ws.reduce((n, w) => n + w.correct, 0)
      const g = ws.reduce((n, w) => n + w.games, 0)
      return { value: c, display: `${c}-${g - c}`, detail: '' }
    },
  }

  const waiting = (key) => {
    if (key === 'low_week') return `Starts once Week ${Math.max(2, lastDone + 1)} is final`
    if (key === 'best_week' || key === 'best_record' || key === 'weeks_won') {
      return `Starts once Week ${lastDone + 1} is final`
    }
    return 'Nothing yet'
  }

  const numbers = NUMBERS.filter((d) => hasPicks || !d.picks).map((d) => {
    const raw = seats.map((p) => {
      const v = calc[d.key](p) || {}
      return {
        ...person(p),
        value: v.value == null ? null : v.value,
        display: v.value == null ? DASH : v.display,
        detail: v.detail || '',
      }
    })
    const rows = rank(raw, d)
    const open = rows.some((r) => r.value != null) ? null : waiting(d.key)
    return {
      key: d.key,
      label: d.label,
      bad: !!d.bad,
      open,
      rows: rungs(d.key, rows),
    }
  })

  /* ----------------------------------------------------------- fame and shame ---- */

  // Holders in the order they first earned it, each with how many times.
  const counted = (ids) => {
    const m = new Map()
    for (const id of ids) m.set(id, (m.get(id) || 0) + 1)
    return [...m].filter(([id]) => seatOf.has(id)).map(([id, count]) => ({ ...person(seatOf.get(id)), count }))
  }

  const totals = new Map(
    seats.map((p) => [p.id, weeks.filter((w) => w.player_id === p.id).reduce((n, w) => n + w.points, 0)]),
  )
  const topTotal = Math.max(0, ...totals.values())

  const margins = []
  for (const n of doneNos) {
    const inWeek = weeks.filter((w) => w.week_no === n).sort((a, b) => b.points - a.points)
    if (inWeek.length > 1 && inWeek[0].points > inWeek[1].points) {
      margins.push({ id: inWeek[0].player_id, week_no: n, by: inWeek[0].points - inWeek[1].points })
    }
  }

  const ups = picks.filter((x) => x.won && x.dog)

  const byGame = new Map()
  for (const x of picks) {
    if (!byGame.has(x.game_id)) byGame.set(x.game_id, [])
    byGame.get(x.game_id).push(x)
  }
  const lone = [...byGame.values()]
    .filter((xs) => xs.length > 1)
    .map((xs) => xs.filter((x) => x.won))
    .filter((right) => right.length === 1)
    .map((right) => right[0])

  const award = {
    season_points() {
      const ids = seats.filter((p) => topTotal > 0 && totals.get(p.id) === topTotal).map((p) => p.id)
      return { holders: counted(ids), detail: `${topTotal} points` }
    },
    margin() {
      if (!margins.length) return {}
      const m = Math.max(...margins.map((x) => x.by))
      const best = margins.filter((x) => x.by === m)
      return {
        holders: counted(best.map((x) => x.id)),
        detail: best.length === 1 ? `Won ${label.get(best[0].week_no)} by ${m}` : `${m} points clear`,
      }
    },
    big_upset() {
      if (!ups.length) return {}
      const m = Math.max(...ups.map((x) => x.spread))
      const best = ups.filter((x) => x.spread === m)
      const teams = [...new Set(best.map((x) => x.team))]
      // One record, not a tally: calling the same size of upset twice is not "x2".
      const holders = counted(best.map((x) => x.player_id)).map((h) => ({ ...h, count: 1 }))
      return { holders, detail: `${teams.join(' and ')} +${fmt(m)}` }
    },
    only_one() {
      return {
        holders: counted(lone.map((x) => x.player_id)),
        detail: lone.length === 1 ? `${lone[0].team}, ${lone[0].label}` : plural(lone.length, 'game', 'games'),
      }
    },
    three_upsets() {
      const hits = []
      for (const n of [...new Set(ups.map((x) => x.week_no))].sort((a, b) => a - b)) {
        for (const p of seats) {
          if (ups.filter((x) => x.week_no === n && x.player_id === p.id).length >= 3) {
            hits.push({ id: p.id, week_no: n })
          }
        }
      }
      return {
        holders: counted(hits.map((h) => h.id)),
        detail: hits.length === 1 ? label.get(hits[0].week_no) : plural(hits.length, 'week', 'weeks'),
      }
    },
    two_td_upset() {
      const hits = ups.filter((x) => x.spread >= 14)
      return {
        holders: counted(hits.map((x) => x.player_id)),
        detail: hits.length === 1 ? `${hits[0].team} +${fmt(hits[0].spread)}` : plural(hits.length, 'upset', 'upsets'),
      }
    },
    win_by_20() {
      const hits = margins.filter((x) => x.by >= 20)
      return {
        holders: counted(hits.map((x) => x.id)),
        detail: hits.length === 1 ? `Won ${label.get(hits[0].week_no)} by ${hits[0].by}` : plural(hits.length, 'week', 'weeks'),
      }
    },
    perfect_week() {
      const hits = weeks.filter((w) => done.has(w.week_no) && w.games >= SLATE && w.correct === w.games)
      return {
        holders: counted(hits.map((w) => w.player_id)),
        detail: hits.length === 1 ? hits[0].label : plural(hits.length, 'week', 'weeks'),
      }
    },
    // "2 times" under two names read like each of them did it twice (copy audit,
    // 2026-09-14), so more than one says whose 20 went on what: "Parker on OU, Grant on KENN".
    lost_20() {
      const hits = picks.filter((x) => x.stake === SLATE && !x.won)
      const holders = counted(hits.map((x) => x.player_id))
      const teamsOf = (id) => hits.filter((x) => x.player_id === id).map((x) => x.team)
      return {
        holders,
        detail: hits.length === 1
          ? `${SLATE} on ${hits[0].team}, ${hits[0].label}`
          : holders.map((h) => `${h.name} on ${andList(teamsOf(h.id))}`).join(', '),
      }
    },
  }

  const awards = (list) =>
    list
      .filter((d) => hasPicks || !d.picks)
      .map((d) => {
        const a = award[d.key]() || {}
        const holders = a.holders || []
        return {
          key: d.key,
          label: d.label,
          holders,
          claimed: holders.length > 0,
          detail: holders.length ? a.detail : '',
        }
      })

  return {
    numbers,
    fame: awards(FAME),
    shame: awards(SHAME),
    weeks: doneNos.length,
    hasPicks,
  }
}
