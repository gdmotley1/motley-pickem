/**
 * The season tab, derived from get_season's one row per player per week.
 *
 * Same rule as weekRecap.js: everything here is a count or a ratio over rows the server
 * returned. Nothing is characterised, and no superlative is claimed that the numbers do
 * not settle outright. Where a stat needs the picks themselves, it is not here, because
 * get_season deliberately does not return them.
 *
 * Ties are first-class throughout, not an edge case. The house rule is that ties stand,
 * so a week has winners rather than a winner, and so does the season.
 */

import { ceiling } from './weekRecap.js'

/** Everyone tied on the best value of `key`. Empty in, empty out. */
function topBy(list, key) {
  if (!list.length) return []
  const best = Math.max(...list.map((x) => x[key]))
  return list.filter((x) => x[key] === best)
}

/**
 * Group the flat rows into weeks, newest first, each knowing who took it.
 *
 * A week counts as played once any game in it has been graded, so the current week
 * appears and moves through the weekend rather than arriving all at once on Monday.
 */
export function weekHistory(rows) {
  const byWeek = new Map()
  for (const r of rows) {
    if (!byWeek.has(r.week_no)) {
      byWeek.set(r.week_no, { week_no: r.week_no, label: r.week_label, entries: [] })
    }
    byWeek.get(r.week_no).entries.push(r)
  }

  return [...byWeek.values()]
    .map((w) => {
      const graded = Math.max(...w.entries.map((e) => Number(e.games) || 0), 0)
      const winners = topBy(
        w.entries.map((e) => ({ ...e, points: Number(e.points) })),
        'points',
      )
      return {
        ...w,
        graded,
        // A week with nothing graded has no leader, only four zeroes.
        winners: graded ? winners.map((e) => ({ id: e.player_id, name: e.player_name })) : [],
        best: graded ? Number(winners[0].points) : 0,
        shared: graded && winners.length > 1,
      }
    })
    .sort((a, b) => b.week_no - a.week_no)
}

/**
 * Season totals per player.
 *
 * `captured` is the season's ranking efficiency: points banked over the sum of each
 * week's ceiling. Summing the weekly ceilings is the only correct way to do this, since
 * a ceiling depends on the shape of one week and cannot be recomputed from season
 * totals. See the note in migrations/010_get_season.sql.
 */
export function seasonTotals(rows, roster) {
  const by = new Map()
  for (const p of roster || []) {
    by.set(p.id, {
      id: p.id,
      name: p.name,
      color: p.color,
      team_id: p.team_id,
      points: 0,
      correct: 0,
      games: 0,
      ceiling: 0,
      weeks: 0,
      best: null,
      worst: null,
      weeksWon: 0,
      byWeek: new Map(),
    })
  }

  for (const r of rows) {
    const s = by.get(r.player_id)
    if (!s) continue
    const points = Number(r.points)
    const correct = Number(r.correct)
    const games = Number(r.games)
    if (!games) continue

    s.points += points
    s.correct += correct
    s.games += games
    s.ceiling += ceiling(correct, games)
    s.weeks += 1
    s.byWeek.set(r.week_no, points)

    const week = { week_no: r.week_no, label: r.week_label, points, correct, games }
    if (!s.best || points > s.best.points) s.best = week
    if (!s.worst || points < s.worst.points) s.worst = week
  }

  for (const w of weekHistory(rows)) {
    for (const win of w.winners) {
      const s = by.get(win.id)
      if (s) s.weeksWon += 1
    }
  }

  const players = [...by.values()]
    .filter((s) => s.weeks > 0)
    .map((s) => ({
      ...s,
      wrong: s.games - s.correct,
      captured: s.ceiling ? Math.round((s.points / s.ceiling) * 100) : 0,
      accuracy: s.games ? Math.round((s.correct / s.games) * 100) : 0,
    }))
    .sort((a, b) => b.points - a.points || b.correct - a.correct)

  let lastPts = null
  let lastPos = 0
  players.forEach((p, i) => {
    if (p.points !== lastPts) {
      lastPos = i + 1
      lastPts = p.points
    }
    p.rank = lastPos
  })
  return players
}

/**
 * The handful of season facts worth printing, each one settled by the numbers.
 *
 * Every entry names who and how much. A superlative nobody holds outright is shared,
 * never broken by a tiebreak that the house rules do not have.
 */
export function seasonRecords(players, weeks) {
  if (!players.length) return []
  const out = []

  const bestWeeks = players.filter((p) => p.best).map((p) => ({ p, w: p.best }))
  if (bestWeeks.length) {
    const top = Math.max(...bestWeeks.map((x) => x.w.points))
    const holders = bestWeeks.filter((x) => x.w.points === top)
    out.push({
      key: 'bestWeek',
      label: 'Best week',
      value: String(top),
      unit: 'pts',
      who: holders.map((x) => `${x.p.name}, ${x.w.label}`).join(' and '),
    })
  }

  const ranked = topBy(players, 'captured')
  out.push({
    key: 'bestRanker',
    label: 'Best ranking',
    value: String(ranked[0].captured),
    unit: '% of ceiling',
    who: ranked.map((p) => p.name).join(' and '),
  })

  const won = topBy(players, 'weeksWon')
  if (won[0].weeksWon > 0) {
    out.push({
      key: 'weeksWon',
      label: 'Weeks won',
      value: String(won[0].weeksWon),
      unit: `of ${weeks.filter((w) => w.graded).length}`,
      who: won.map((p) => p.name).join(' and '),
    })
  }

  const acc = topBy(players, 'accuracy')
  out.push({
    key: 'accuracy',
    label: 'Most accurate',
    value: String(acc[0].accuracy),
    unit: '%',
    who: acc.map((p) => p.name).join(' and '),
  })

  return out
}

/**
 * Points per week per player, shaped for the form chart.
 *
 * Weeks run oldest to newest here, the opposite of the history list, because a chart
 * reads left to right in time and a list reads newest first.
 */
export function seasonForm(players, weeks) {
  const order = [...weeks].filter((w) => w.graded).sort((a, b) => a.week_no - b.week_no)
  const max = Math.max(1, ...players.flatMap((p) => [...p.byWeek.values()]))
  return {
    weeks: order.map((w) => ({ week_no: w.week_no, label: w.label })),
    max,
    series: players.map((p) => ({
      id: p.id,
      name: p.name,
      color: p.color,
      points: order.map((w) => p.byWeek.get(w.week_no) ?? null),
    })),
  }
}

/**
 * Turn the form data into drawable coordinates.
 *
 * Kept out of the screen so the gate can check it. A chart is the one thing on either
 * tab that can look plausible and be wrong: a point off the top of the viewBox, or a
 * gridline labelled with a value the scale never reaches, both render without erroring.
 *
 * The scale starts at zero and ends on the next multiple of 25 above the best week, so
 * every tick is a number the chart actually spans, and a missing week breaks the line
 * rather than drawing through it.
 */
export function formGeometry(form, box = {}) {
  const W = box.W ?? 320
  const H = box.H ?? 132
  const padL = box.padL ?? 26
  const padB = box.padB ?? 18
  const padT = box.padT ?? 8
  const n = form.weeks.length
  const top = Math.max(25, Math.ceil(form.max / 25) * 25)

  const x = (i) => (n <= 1 ? padL + (W - padL) / 2 : padL + (i * (W - padL - 6)) / (n - 1))
  const y = (v) => padT + (1 - v / top) * (H - padT - padB)

  return {
    W,
    H,
    top,
    ticks: [0, top / 2, top].map((v) => ({ value: v, y: y(v) })),
    columns: form.weeks.map((w, i) => ({ ...w, x: x(i) })),
    series: form.series.map((s) => ({
      id: s.id,
      name: s.name,
      color: s.color,
      // Nulls are holes, not zeroes: a week someone has not played yet must not drag
      // their line to the floor.
      points: s.points
        .map((v, i) => (v == null ? null : { x: x(i), y: y(v), value: v }))
        .filter(Boolean),
    })),
  }
}

/** One call for the whole tab. */
export function seasonStats(rows, roster) {
  const weeks = weekHistory(rows || [])
  const players = seasonTotals(rows || [], roster || [])
  return {
    players,
    weeks,
    records: seasonRecords(players, weeks),
    form: seasonForm(players, weeks),
    played: weeks.filter((w) => w.graded).length,
  }
}
