/** Display helpers. Everything is shown in the viewer's own timezone. */

const DAY = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

/** "Sat 3:30 PM" — day plus local time, which is all a picker needs. */
export function kickoffLabel(iso) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const time = d
    .toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
    .replace(/\s?([AP])M/i, ' $1M')
  return `${DAY[d.getDay()]} ${time}`
}

/**
 * "Saturday, Sep 5" — the heading over a day's games on the Setup screen.
 *
 * Local, like every other label here, so it agrees with the kickoff times underneath it
 * rather than with ESPN's Eastern filing date.
 */
export function dayLabel(iso) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' })
}

/** Sort/group key for dayLabel: the local calendar date, as "2026-09-05". */
export function dayKey(iso) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString('en-CA')
}

/** "in 3h", "in 24m", "kicked off" — used on the countdown chip. */
export function untilLabel(iso) {
  const ms = new Date(iso).getTime() - Date.now()
  if (Number.isNaN(ms)) return ''
  if (ms <= 0) return 'kicked off'
  const mins = Math.round(ms / 60000)
  if (mins < 60) return `in ${mins}m`
  const hrs = Math.round(mins / 60)
  if (hrs < 24) return `in ${hrs}h`
  return `in ${Math.round(hrs / 24)}d`
}

export const ordinal = (n) => {
  const s = ['th', 'st', 'nd', 'rd']
  const v = n % 100
  return n + (s[(v - 20) % 10] || s[v] || s[0])
}
