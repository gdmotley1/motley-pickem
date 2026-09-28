/**
 * Which weeks a pager can step to, and what each one is called.
 *
 * Kept out of the screens so the gate can check the edges, which is where this kind of
 * control goes wrong: an arrow that stays live at week 1, or one that walks into a week
 * that is not over.
 *
 * Two lists, because the two tabs are for different things. `recapWeeks` is the Week
 * tab's: finished weeks only, because it lags a week on purpose. `boardWeeks` is the
 * Board's: every published week up to and including the one being played.
 */

/**
 * The weeks the Week tab shows: finished ones only, oldest first.
 *
 * Grant, 2026-09-12: "show nothing for week two and just have it be whatever the most
 * recent published week is. So always have it lag a week." The week being played lives on
 * the Board. The Week tab is the recap, and a recap of half a week is half built.
 *
 * Finished means published, with a slate, and every game graded, OR a later week already
 * has a graded game. That second half is the rule seasonStats.finishedWeeks uses, so a game
 * postponed for good cannot hide a week that is plainly over.
 */
export function recapWeeks(weeks) {
  const rows = (weeks || [])
    .filter((w) => w.published && Number(w.slate_size) > 0)
    .sort((a, b) => a.week_no - b.week_no)
  return rows.filter((w, i) => isComplete(w) || rows.slice(i + 1).some((later) => Number(later.graded) > 0))
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
  // "no results yet", not "not started": this row carries slate_size and graded and
  // nothing about kickoffs, so it cannot tell an untouched week from one where all
  // twenty games are live and none has gone final.
  if (!graded) return 'no results yet'
  if (graded < size) return 'in progress'
  return null
}

/** True once every game in the week has a result. */
export const isComplete = (week) =>
  !!week && Number(week.slate_size) > 0 && Number(week.graded) === Number(week.slate_size)

/**
 * The weeks the Board can step back through: published weeks with a slate, up to and
 * including the week being played.
 *
 * Grant asked for the previous weeks' boards on 2026-09-28. Deliberately a different rule
 * from recapWeeks. The Week tab lags a week because a recap of half a week is half built;
 * the Board IS the scoreboard, so a week mid-flight is exactly what it is for, and the
 * newest entry is always the one being played.
 *
 * Nothing past the current week. A week the sync job published early on its T-18h net
 * would otherwise sit one tap forward with every pick hidden and no score, which reads as
 * a broken screen rather than as a week that has not started.
 *
 * The current week is in the list whether or not it is published, because it is the screen
 * the app opens on and it has its own "No slate yet" state to show.
 */
export function boardWeeks(weeks, currentId) {
  const all = weeks || []
  const current = all.find((w) => w.id === currentId) || null
  const upto = current ? Number(current.week_no) : Infinity
  return all
    .filter(
      (w) =>
        w.id === currentId ||
        (w.published && Number(w.slate_size) > 0 && Number(w.week_no) <= upto),
    )
    .sort((a, b) => a.week_no - b.week_no)
}

/**
 * The pager's state for one viewed week: where the arrows go, and whether they are live.
 *
 * `prev` and `next` are the week rows to move to, or null at an edge. Nulls are what the
 * screen disables on, so an edge is a fact here rather than a condition restated in JSX.
 * `latest` is the newest week in the list, which is where the tab opens.
 */
function navIn(list, viewId) {
  const latest = list.length ? list[list.length - 1] : null
  const at = list.findIndex((w) => w.id === viewId)
  const current = at === -1 ? null : list[at]
  return {
    list,
    latest,
    current,
    // Ordered oldest to newest, so "previous" is the lower index.
    prev: at > 0 ? list[at - 1] : null,
    next: at !== -1 && at < list.length - 1 ? list[at + 1] : null,
    isLatest: !!current && current.id === latest.id,
  }
}

/** The Week tab's pager: finished weeks only. */
export function weekNav(weeks, viewId) {
  return navIn(recapWeeks(weeks), viewId)
}

/**
 * The Board's pager. Falls back to the week being played, so a screen that has not been
 * stepped anywhere is sitting on the current week rather than nowhere.
 */
export function boardNav(weeks, currentId, viewId) {
  return navIn(boardWeeks(weeks, currentId), viewId ?? currentId)
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
