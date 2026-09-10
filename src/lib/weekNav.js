/**
 * Which weeks the Week tab can step to, and what each one is called.
 *
 * Kept out of the screen so the gate can check the edges, which is where this kind of
 * control goes wrong: an arrow that stays live at week 1, or one that walks off the end
 * of the season into a week nobody has played.
 */

/**
 * You may look back at any week, and never forward past the one in progress.
 *
 * Stepping into an unplayed future week would show four zeroes and read as a bug, and it
 * would also quietly reveal which games Dad has lined up for a slate he has not published.
 * The current week is the far edge in both senses.
 */
export function visitableWeeks(weeks, currentWeekNo) {
  const rows = (weeks || []).slice().sort((a, b) => a.week_no - b.week_no)
  if (currentWeekNo == null) return rows
  return rows.filter((w) => w.week_no <= currentWeekNo)
}

/**
 * What each week's row should say when it is not a result: an unpublished week, a
 * published one nobody has played yet, or one mid-flight.
 *
 * Returns null when the week has finished and a real result belongs there instead.
 */
export function weekStatus(week) {
  if (!week) return 'unknown'
  const size = Number(week.slate_size) || 0
  const graded = Number(week.graded) || 0
  if (!week.published) return 'not published'
  if (!size) return 'no slate yet'
  if (!graded) return 'not started'
  if (graded < size) return 'in progress'
  return null
}

/** True once every game in the week has a result. */
export const isComplete = (week) =>
  !!week && Number(week.slate_size) > 0 && Number(week.graded) === Number(week.slate_size)

/**
 * The pager's state for one viewed week: where the arrows go, and whether they are live.
 *
 * `prev` and `next` are the week rows to move to, or null at an edge. Nulls are what the
 * screen disables on, so an edge is a fact here rather than a condition restated in JSX.
 */
export function weekNav(weeks, currentWeekNo, viewId) {
  const list = visitableWeeks(weeks, currentWeekNo)
  const at = list.findIndex((w) => w.id === viewId)
  const current = at === -1 ? null : list[at]
  return {
    list,
    current,
    // Ordered oldest to newest, so "previous" is the lower index.
    prev: at > 0 ? list[at - 1] : null,
    next: at !== -1 && at < list.length - 1 ? list[at + 1] : null,
    isCurrent: !!current && current.week_no === currentWeekNo,
  }
}

/**
 * Who won each finished week, keyed by week number, from get_season's rows.
 *
 * Ties stand, so this is a list of names per week rather than one name. Used only by the
 * jump sheet, which is why it takes the rows rather than fetching: the sheet loads them
 * on first open and the pager never needs them.
 */
export function winnersByWeek(seasonRows) {
  const by = new Map()
  for (const r of seasonRows || []) {
    const points = Number(r.points)
    if (!Number(r.games)) continue
    const e = by.get(r.week_no) || { points: -1, names: [] }
    if (points > e.points) by.set(r.week_no, { points, names: [r.player_name] })
    else if (points === e.points) e.names.push(r.player_name)
  }
  return by
}
