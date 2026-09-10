/**
 * "You have games to pick, and here is when they lock."
 *
 * Option A2 from outputs/feature-board.html, chosen by Grant on 2026-09-10. The app had
 * never asked anyone to do anything: no badge, no deadline, no reminder. The state that
 * made the case was live at the time, with Week 2 published, the first kickoff 24.8 hours
 * away and 0 of 80 picks submitted.
 *
 * Two things it deliberately does NOT do. It never counts a game that has already kicked
 * off, because that one is gone and telling you about it is only a reproach. And it never
 * appears once you are done, so finishing your card is what makes it disappear.
 */
import { useEffect, useRef, useState } from 'react'
import { IconClock } from './ui.jsx'
import { kickoffLabel, untilLabel } from '../lib/format.js'

/* Dismissal is remembered against the DEADLINE, not the week. Saying "not now" to a
   Thursday game should not also silence Saturday morning: the next kickoff is a new
   deadline and re-arms the nudge on its own. Per device, like every other preference
   here. */
const SNOOZE_KEY = 'pickem.nudge.snoozed'

/* Under this the nudge switches to the urgent treatment and counts in minutes. Two hours
   is roughly "you could still be doing something else"; below it, you cannot. */
const URGENT_MS = 2 * 60 * 60 * 1000

/* Long enough to read as a collapse rather than a disappearance, short enough that
   nobody waits for it. Must match .nudge.is-going in app.css. */
const EXIT_MS = 260

const read = () => {
  try {
    return localStorage.getItem(SNOOZE_KEY)
  } catch {
    return null // private mode: the nudge simply always shows, which is the safe way round
  }
}

const write = (v) => {
  try {
    localStorage.setItem(SNOOZE_KEY, v)
  } catch {
    /* nothing to do; it reappears next launch, which is better than swallowing the tap */
  }
}

/**
 * The soonest kickoff among games you can still pick, and how many there are.
 *
 * Locked games are excluded on both counts. `my_pick` comes straight off get_slate, so
 * this is the server's view of what you have done rather than anything the client
 * inferred.
 */
export function pendingPicks(games) {
  const all = games || []
  const open = all.filter((g) => !g.locked && !g.my_pick)
  if (!open.length) return null
  const deadline = open.reduce(
    (min, g) => (min === null || g.kickoff < min ? g.kickoff : min),
    null,
  )
  /* Whether the week is under way at all, which is only ever used to choose a word:
     "first kickoff" is wrong once Thursday night has been and gone. */
  return { count: open.length, deadline, started: all.some((g) => g.locked) }
}

export default function PickNudge({ games, onGo }) {
  const pending = pendingPicks(games)
  const deadline = pending?.deadline ?? null

  const [snoozed, setSnoozed] = useState(read)
  const [going, setGoing] = useState(false)
  const timer = useRef(null)

  /* Re-render on a timer so the countdown is alive rather than fixed at whatever it said
     when the screen mounted. Thirty seconds is under the resolution of every label it can
     produce, so the text is never more than a moment stale, and it costs nothing. */
  const [, tick] = useState(0)
  useEffect(() => {
    if (!deadline) return undefined
    const id = setInterval(() => tick((n) => n + 1), 30000)
    return () => clearInterval(id)
  }, [deadline])

  useEffect(() => () => clearTimeout(timer.current), [])

  if (!pending || going === 'gone') return null
  if (snoozed === deadline) return null

  const left = new Date(deadline).getTime() - Date.now()
  const urgent = left <= URGENT_MS

  function dismiss() {
    setGoing(true)
    write(deadline)
    /* Unmounted on a timeout rather than on transitionend. A backgrounded tab pauses
       transitions, and an element waiting on an event that never fires would sit there
       half-collapsed forever. The timer fires either way. */
    timer.current = setTimeout(() => {
      setSnoozed(deadline)
      setGoing('gone')
    }, EXIT_MS)
  }

  return (
    <div
      className={`nudge${urgent ? ' nudge--urgent' : ''}${going === true ? ' is-going' : ''}`}
      role="status"
    >
      <span className="nudge__icon" aria-hidden="true">
        <IconClock />
      </span>

      <span className="nudge__text">
        <span className="nudge__head">
          {pending.count} {pending.count === 1 ? 'game' : 'games'} to pick
        </span>
        <span className="nudge__sub num">
          {urgent ? 'Locks' : pending.started ? 'Next kickoff' : 'First kickoff'}{' '}
          {kickoffLabel(deadline)}
          <span className="nudge__dot">·</span>
          <b>{untilLabel(deadline)}</b>
        </span>
      </span>

      <button className="nudge__go" onClick={onGo}>
        Pick
      </button>
      <button className="nudge__x" onClick={dismiss} aria-label="Hide until the next kickoff">
        <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">
          <path
            d="M7 7l10 10M17 7L7 17"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
          />
        </svg>
      </button>
    </div>
  )
}
