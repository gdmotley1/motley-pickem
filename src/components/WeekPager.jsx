/**
 * The week pager: an arrow either side, and a label that opens a jump list.
 *
 * Option C from the board Grant chose on 2026-09-10, moved into the winner's color field on
 * 2026-09-12 and onto the jumbotron on 2026-09-13. It lived inside Week.jsx until
 * 2026-09-28, when he asked to see the previous weeks' boards too and the Board grew the
 * same control; one component means the two tabs can never drift into two ways of stepping
 * between weeks.
 *
 * Which weeks the arrows reach is not decided here. It is `nav`, from weekNav.js:
 * `weekNav` for the Week tab's finished weeks, `boardNav` for the Board's published ones.
 * An edge is a null in `nav`, so a disabled arrow is a fact from that module rather than a
 * condition restated in JSX.
 *
 * There is no "Back to Week N" button. Grant had it taken out on 2026-09-13: the arrow and
 * the jump list already get you there.
 */
import { useCallback, useMemo, useState } from 'react'
import * as api from '../lib/api.js'
import { Chevron, Sheet } from './ui.jsx'
import { ampList } from '../lib/format.js'
import { weekStatus, winnersByWeek } from '../lib/weekNav.js'

export default function WeekPager({ nav, onGo, noPrev = 'No earlier week', noNext = 'No later week', finished }) {
  const [open, setOpen] = useState(false)
  const [season, setSeason] = useState(null)
  const viewing = nav.current

  /* The winners are only ever read by the sheet, so they load on first open and stay.
     The pager itself never needs them, and each screen already makes three calls. */
  const openPicker = useCallback(() => {
    setOpen(true)
    setSeason((prev) => {
      if (prev) return prev
      api.getSeason().then(setSeason).catch(() => setSeason([]))
      return prev
    })
  }, [])

  return (
    <>
      <div className="wknav wknav--hero">
        <button
          className="wknav__arrow"
          onClick={() => nav.prev && onGo(nav.prev.id)}
          disabled={!nav.prev}
          aria-label={nav.prev ? `Go to ${nav.prev.label}` : noPrev}
        >
          <Chevron dir="left" size={17} />
        </button>

        <button className="wknav__mid" onClick={openPicker} aria-label="Choose a week">
          <b>
            {viewing?.label}
            <Chevron dir="down" size={13} />
          </b>
        </button>

        <button
          className="wknav__arrow"
          onClick={() => nav.next && onGo(nav.next.id)}
          disabled={!nav.next}
          aria-label={nav.next ? `Go to ${nav.next.label}` : noNext}
        >
          <Chevron dir="right" size={17} />
        </button>
      </div>

      <Sheet open={open} onClose={() => setOpen(false)} label="Choose a week">
        <div className="screen">
          <h3 className="h2">Jump to a week</h3>
        </div>
        <WeekList
          weeks={nav.list}
          season={season}
          viewId={viewing?.id}
          finished={finished}
          onGo={(id) => {
            onGo(id)
            setOpen(false)
          }}
        />
      </Sheet>
    </>
  )
}

/**
 * The weeks in the list, newest first, each with who took it.
 *
 * `finished` is the set of ids that are actually over, and only those are allowed to name
 * a winner. Without it the Board's list would print the leader of the week being played in
 * the same place and the same words as a week somebody won, which is the one thing a jump
 * list must not say. The Week tab passes nothing, because every week it can reach is over.
 */
function WeekList({ weeks, season, viewId, onGo, finished }) {
  const winners = useMemo(() => winnersByWeek(season), [season])

  return (
    <div className="wklist">
      {[...weeks].reverse().map((w) => {
        const live = finished && !finished.has(w.id) ? weekStatus(w) : null
        const won = winners.get(w.week_no)
        const status = weekStatus(w)
        return (
          <button
            key={w.id}
            className={`wkrow${w.id === viewId ? ' is-on' : ''}${live || status ? ' is-quiet' : ''}`}
            onClick={() => onGo(w.id)}
          >
            <span className="wkrow__n">{w.label}</span>
            <span className="wkrow__v">
              {live ||
                (won ? (
                  <>
                    {ampList(won.names)} <b className="num">{won.points}</b>
                  </>
                ) : (
                  status || (season === null ? '…' : 'no result')
                ))}
            </span>
          </button>
        )
      })}
    </div>
  )
}
