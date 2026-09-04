/**
 * The week's score, shown twice on the board: as a card at the top, and as a strip
 * pinned under the header once that card has scrolled away.
 *
 * Both read the same object from `weekScore`, so the two can never disagree.
 */
import { useEffect, useState } from 'react'
import { Portal } from './ui.jsx'

/**
 * How far down the viewport the readable area actually starts.
 *
 * `.app__body` looks like the scroll container but is not one: `.app` is sized by
 * min-height, so the flex child grows with its content and the document is what scrolls.
 * That makes the sticky header overlap the top of the scroll, and anything else pinned
 * to `top: 0` lands underneath it at a lower z-index and is never seen. Measuring beats
 * hard-coding the height, which is padding plus two lines of type plus the safe-area
 * inset and would silently drift the first time any of them changes.
 */
export function useHeaderOffset() {
  const [h, setH] = useState(0)

  useEffect(() => {
    const el = document.querySelector('.apphdr')
    if (!el) return undefined
    const read = () => setH(Math.round(el.getBoundingClientRect().height))
    read()
    if (typeof ResizeObserver === 'undefined') return undefined
    const ro = new ResizeObserver(read)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  return h
}

/**
 * The race. Solid bar is banked, the pale one behind it is where you can still finish.
 * Both are drawn out of the same weekly total, so the four bars share one scale and the
 * gap between two players is a distance instead of a subtraction.
 */
export function WeekScore({ score, cardRef }) {
  const { total, best, players } = score
  return (
    <div className="wkbars" ref={cardRef}>
      <div className="wkbars__head">
        <span className="wkbars__ttl">This week</span>
        <span className="wkbars__key">
          <i className="is-banked" />
          banked
          <i className="is-live" />
          still live
        </span>
      </div>

      <div className="wkbars__rows">
        {players.map((p) => (
          <div className="wkbar" key={p.id}>
            <span className="wkbar__name">{p.name}</span>
            <span className="wkbar__track">
              <span
                className="wkbar__live"
                style={{
                  width: `${((p.points + p.live) / total) * 100}%`,
                  background: p.color,
                }}
              />
              <span
                className="wkbar__fill"
                style={{ width: `${(p.points / total) * 100}%`, background: p.color }}
              />
            </span>
            <span
              className={`wkbar__val num${best > 0 && p.points === best ? ' is-leader' : ''}`}
            >
              {p.points}
            </span>
          </div>
        ))}
      </div>

      <p className="wkbars__foot">
        Out of {total}. The pale bar is the most you can still finish the week on.
      </p>
    </div>
  )
}

/**
 * The same four numbers, welded under the header once the card has scrolled away.
 *
 * Fixed and portalled, exactly like the tab bar, and for two reasons. `position: sticky`
 * cannot work here at all: `.app__body` is `overflow-y: auto`, so it owns the sticky
 * scrollport, but it never actually scrolls because `.app` is sized by min-height and the
 * document is what moves. A sticky strip inside it just scrolls away. And a fixed strip
 * left in place would resolve against the screen wrapper's transform rather than the
 * viewport, which is the bug the Portal helper exists for.
 *
 * Being out of flow also means showing and hiding it can never shift the game cards. It
 * slides on a transform rather than fading in, because a backgrounded tab pauses opacity
 * work and has left an overlay stuck half-transparent here before.
 */
export function ScoreBug({ score, pinned, top }) {
  const { best, players } = score
  return (
    <Portal>
      <div className={`wkbug${pinned ? ' is-on' : ''}`} style={{ top }}>
        <div className="wkbug__bar">
          {players.map((p) => (
            <span
              className={`wkbug__p${best > 0 && p.points === best ? ' is-leader' : ''}`}
              key={p.id}
            >
              <i style={{ background: p.color }} />
              <span className="wkbug__who">{p.name}</span>
              <b className="num">{p.points}</b>
            </span>
          ))}
        </div>
      </div>
    </Portal>
  )
}
