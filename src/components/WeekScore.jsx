/**
 * The week's score as a broadcast scorebug, shown twice on the board: full width at the
 * top, and as a strip pinned under the header once that card has scrolled away.
 *
 * Both read the same object from `weekScore`, so the two can never disagree.
 *
 * Option S2 from outputs/scorebug-board.html, chosen by Grant on 2026-09-10: dark chrome,
 * a solid block of the player's school colour carrying their seed and mark, condensed
 * caps for the name, and the score set large in tabular figures. The condensed cut is
 * Archivo's `wdth` axis, which index.html now asks Google Fonts for; it is the same
 * family the app already loaded, so it costs no extra request.
 */
import { useEffect, useState } from 'react'
import { Portal } from './ui.jsx'
import { teamById, markUrl } from '../lib/teams.js'

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
 * The block that carries a player's seed and mark.
 *
 * Its colour is the school's OTHER colour, not the disc's. Grant asked for "the secondary
 * colour of each school" and taken as ESPN's `alt_color` that collapses immediately:
 * Wyoming's alternate IS the disc, so the mark would sit on a block of its own background
 * and the disc would stop existing. `alt` in teams.json is therefore whichever school
 * colour the disc did not take, which is the same idea and cannot collide. A seat with no
 * school falls back to the player's own colour, exactly as the avatar does.
 */
function Block({ p, size = 24, skeleton }) {
  const team = teamById(p.team_id)
  const bg = team?.alt || p.color
  return (
    <span className="bugrow__block" style={{ background: bg }}>
      {/* Nothing to rank before anyone has scored: everyone ties on zero, so a real
          rank would print "1" four times down the block. */}
      {!skeleton && <span className="bugrow__seed num">{p.rank}</span>}
      {team ? (
        <span
          className="avatar avatar--team bugrow__mark"
          style={{ width: size, height: size, background: team.bg }}
        >
          <img src={markUrl(team)} alt="" width={Math.round(size * 0.72)}
               height={Math.round(size * 0.72)} loading="lazy" decoding="async" />
        </span>
      ) : (
        <span
          className="avatar bugrow__mark"
          style={{ width: size, height: size, background: p.color,
                   fontSize: size * 0.42 }}
          aria-hidden="true"
        >
          {(p.name || '?').slice(0, 1).toUpperCase()}
        </span>
      )}
    </span>
  )
}

/**
 * One row: colour block, name in condensed caps, score, and the gap to the lead.
 *
 * The 2px strip along the bottom is where a real bug draws timeouts, and here it is
 * banked against the most you can still finish on. It is deliberately the only place the
 * old bar survives: a full-width track was four near-identical bars, because everyone is
 * within a few points of everyone else on a 210 scale.
 */
function Row({ p, best, total, mine, record, skeleton }) {
  const gap = best - p.points
  /* `best > 0` matters at the first kickoff, when nobody has scored: without it all four
     rows go gold for a lead nobody holds. A skeleton is that case by definition. */
  const leader = !skeleton && best > 0 && gap === 0
  return (
    <div className={`bugrow${leader ? ' is-leader' : ''}${skeleton ? ' is-skeleton' : ''}`}>
      <Block p={p} skeleton={skeleton} />
      <span className="bugrow__name">
        {p.name}
        {mine && <span className="bugrow__you">You</span>}
      </span>
      {/* The Week tab wants a record beside the score; the Board does not have room and
          does not need one, because the game cards underneath are the record. */}
      {record && !skeleton && (
        <span className="bugrow__rec num">
          {p.correct}-{p.played - p.correct}
        </span>
      )}
      <span className="bugrow__pts num">{skeleton ? '—' : p.points}</span>
      <span className="bugrow__gap num">
        {skeleton ? '' : gap === 0 ? '—' : `-${gap}`}
      </span>
      <span className="bugrule">
        {!skeleton && p.live > 0 && (
          <i className="is-live"
             style={{ width: `${((p.points + p.live) / total) * 100}%`, background: p.color }} />
        )}
        {!skeleton && (
          <i style={{ width: `${(p.points / total) * 100}%`, background: p.color }} />
        )}
      </span>
    </div>
  )
}

/** The header strip: which week, how many games are on, how far through the slate. */
function Top({ score, label, note }) {
  return (
    <div className="bug__top">
      <span className="bug__wk">{label}</span>
      {score.playing > 0 && (
        <span className="bug__live">
          <i />
          {score.playing} live
        </span>
      )}
      <span className="bug__of num">
        {note || `${score.graded} of ${score.slateSize}`}
      </span>
    </div>
  )
}

/** "Out of 210. You are 7 back, with 84 still to play for." */
function footline(score, mine) {
  const { total, best } = score
  if (!mine) return `Out of ${total}.`
  const where = mine.points === best
    ? (best === 0 ? 'nobody has scored yet' : mine.shared ? 'you share the lead' : 'you lead')
    : `you are ${best - mine.points} back`
  const left = mine.live > 0 ? `, with ${mine.live} still to play for` : ''
  return `Out of ${total}. ${where[0].toUpperCase()}${where.slice(1)}${left}.`
}

/**
 * @param skeleton  Draw the frame with no numbers in it. Used for a published week
 *                  nobody has played yet, where the alternative was an empty state that
 *                  said nothing and looked like the feature was missing.
 * @param record    Show each player's correct-wrong beside the score. The Week tab wants
 *                  it; the Board does not have the room.
 */
export function WeekScore({
  score, cardRef, me, label = 'This week', skeleton = false, record = false, note, foot,
}) {
  const { best, players, total } = score
  const mine = players.find((p) => p.id === me?.id)
  return (
    <div className={`bug bug--dark${record ? ' bug--rec' : ''}`} ref={cardRef}>
      <Top score={score} label={label} note={note} />
      {players.map((p) => (
        <Row key={p.id} p={p} best={best} total={total} mine={p.id === me?.id}
             record={record} skeleton={skeleton} />
      ))}
      {/* Built as one sentence rather than three appended fragments. The first cut
          appended ", shared" and then " with N still to play for", which ran together
          into "you lead, shared with 210 still to play for": read as being shared with
          the 210 rather than with the other players. */}
      <p className="bug__foot">{foot || footline(score, mine)}</p>
    </div>
  )
}

/**
 * The same numbers welded under the header once the card has scrolled away.
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
          {players.map((p) => {
            const team = teamById(p.team_id)
            return (
              <span
                className={`wkbug__p${p.points === best ? ' is-leader' : ''}`}
                key={p.id}
              >
                <i style={{ background: team?.alt || p.color }} />
                <span className="wkbug__who">{p.name}</span>
                <b className="num">{p.points}</b>
              </span>
            )
          })}
        </div>
      </div>
    </Portal>
  )
}
