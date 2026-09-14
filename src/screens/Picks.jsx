import { useCallback, useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import * as api from '../lib/api.js'
import { friendly } from '../lib/errors.js'
import Led from '../components/Led.jsx'
import Mark from '../components/Mark.jsx'
import {
  Chevron,
  IconClock,
  IconGrip,
  IconLock,
  Portal,
  Rank,
  Sheet,
  Spinner,
  Toast,
} from '../components/ui.jsx'
import Matchup from '../components/Matchup.jsx'
import { dayKey, kickoffLabel, tvLabel, weekdayLabel } from '../lib/format.js'
import { schoolPanel } from '../lib/schoolField.js'
import { useTeams } from '../lib/teams.js'
import { rankOf, useRanks } from '../lib/useRanks.js'

/**
 * Your card for the week, on the jumbotron.
 *
 * The look is direction 1 of the six Grant was shown on 2026-09-13 ("lets do 1, build it"):
 * the Board's LED wall carried onto Picks, so the two tabs are one stadium. Every team is a
 * lit panel in its school's colors, a pick lights gold, points are LED numbers on the
 * Board's leaderboard rows, and locking in gets the marquee and a crawl.
 *
 * What did not change is everything that already worked: a list for winners, tap to lift
 * and place for points, the spread sort on arrival, the loud Matchup pill.
 */

const DRAFT_KEY = 'pickem.draft.v1'
const PANEL = '#2a2f37' // a school with no colors in the library, lit the Board's grey

export default function Picks({ me, weekId, week, onNavigate }) {
  const [games, setGames] = useState(null)
  const [error, setError] = useState(null)
  const [phase, setPhase] = useState('choose') // choose | rank | locked | done
  const [winners, setWinners] = useState({})
  const [order, setOrder] = useState([])
  const [orderTouched, setOrderTouched] = useState(false)
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState(null)

  /* ------------------------------------------------------------------ load */

  useEffect(() => {
    let alive = true
    api
      .getSlate(weekId)
      .then((rows) => {
        if (!alive) return
        setGames(rows)
        const draft = readDraft(me.id)
        const seeded = {}
        for (const g of rows) if (g.my_pick) seeded[g.game_id] = g.my_pick
        const w = { ...(draft?.winners || {}), ...seeded }
        setWinners(w)

        const editable = rows.filter((g) => !g.locked)

        // The ranking is rebuilt from the server first, then a local draft on top.
        //
        // This used to read the draft alone, and submitting clears the draft, so
        // reopening the app fell back to spread order and every point value looked
        // wrong. The confidence numbers were saved correctly the whole time; the
        // client was throwing them away on load.
        const fromServer = editable
          .filter((g) => g.my_confidence != null)
          .sort((a, b) => b.my_confidence - a.my_confidence)
          .map((g) => g.game_id)
        const fromDraft = (draft?.order || []).filter((id) =>
          editable.some((g) => g.game_id === id),
        )
        // Once you have submitted, the server is the only version that counts. Letting a
        // leftover draft win here dropped you back into a freely movable list with no sign
        // of what was actually saved, which is the opposite of locked in.
        //
        // The exception is a card you deliberately reopened with Change. That flag is what
        // keeps a half-finished edit alive across a tab switch, without the list quietly
        // unlocking itself every time you come back to it.
        const submitted = rows.length > 0 && rows.every((g) => g.my_pick)
        const resuming = submitted && !!draft?.editing
        setEditing(resuming)
        const base =
          submitted && !resuming ? fromServer : fromDraft.length ? fromDraft : fromServer
        const missing = editable
          .map((g) => g.game_id)
          .filter((id) => !base.includes(id))
        setOrder([...base, ...missing])
        // A saved ranking counts as deliberate, so the spread sort must not stomp it.
        setOrderTouched(!!draft?.touched || fromServer.length > 0)

        if (submitted && !resuming) setPhase('locked')
        else if (editable.length && editable.every((g) => w[g.game_id])) setPhase('rank')
      })
      .catch((e) => alive && setError(friendly(e)))
    return () => {
      alive = false
    }
  }, [me.id, weekId])

  const editable = useMemo(() => (games || []).filter((g) => !g.locked), [games])
  const locked = useMemo(() => (games || []).filter((g) => g.locked), [games])

  /* Confidence values already spent by locked games cannot be reused. */
  const availableValues = useMemo(() => {
    if (!games) return []
    const used = new Set(locked.map((g) => g.my_confidence).filter(Boolean))
    const out = []
    for (let v = games.length; v >= 1; v -= 1) if (!used.has(v)) out.push(v)
    return out // descending: the top of the ranked list gets the biggest number
  }, [games, locked])

  const chosenCount = editable.filter((g) => winners[g.game_id]).length
  const allChosen = editable.length > 0 && chosenCount === editable.length

  useEffect(() => {
    if (games) writeDraft(me.id, { winners, order, touched: orderTouched, editing })
  }, [winners, order, orderTouched, editing, games, me.id])

  /* --------------------------------------------------------------- actions */

  const choose = useCallback((game, abbr) => {
    setWinners((w) => ({ ...w, [game.game_id]: abbr }))
    navigator.vibrate?.(8)
  }, [])

  /**
   * How sure Vegas is about the pick you made: the line if you took the favourite,
   * the negative of it if you took the dog. Biggest number is the safest pick.
   */
  const spreadOrder = useCallback(
    (ids) => {
      const score = (id) => {
        const g = editable.find((x) => x.game_id === id)
        if (!g) return 0
        const line = g.spread_line == null ? 0 : Number(g.spread_line)
        return winners[g.game_id] === g.favorite_abbr ? line : -line
      }
      return [...ids].sort((a, b) => score(b) - score(a))
    },
    [editable, winners],
  )

  // Land on the ranking screen already sorted. You only fix what you disagree with,
  // which for this pool is two or three games.
  useEffect(() => {
    if (phase !== 'rank' || orderTouched || !order.length) return
    setOrder((cur) => {
      const next = spreadOrder(cur)
      return next.every((id, i) => id === cur[i]) ? cur : next
    })
  }, [phase, orderTouched, order.length, spreadOrder])

  const resetOrder = useCallback(() => {
    setOrder((cur) => spreadOrder(cur))
    setOrderTouched(false)
    navigator.vibrate?.(14)
    setToast('Back to spread order.')
  }, [spreadOrder])

  /* Reopening a submitted card. Nothing is saved again until Lock in my picks. */
  const reopen = useCallback(() => {
    setEditing(true)
    setPhase('rank')
    navigator.vibrate?.(10)
  }, [])

  const moveTo = useCallback((id, index) => {
    setOrder((cur) => {
      const from = cur.indexOf(id)
      if (from === -1 || from === index) return cur
      const next = [...cur]
      next.splice(from, 1)
      next.splice(index, 0, id)
      return next
    })
    setOrderTouched(true)
    navigator.vibrate?.(12)
  }, [])

  async function submit() {
    setSaving(true)
    setError(null)
    try {
      const conf = {}
      order.forEach((id, i) => {
        conf[id] = availableValues[i]
      })
      const payload = [
        ...locked.map((g) => ({
          game_id: g.game_id,
          pick: g.my_pick,
          confidence: g.my_confidence,
        })),
        ...order.map((id) => ({ game_id: id, pick: winners[id], confidence: conf[id] })),
      ]
      await api.savePicks(weekId, payload)
      clearDraft(me.id)
      setEditing(false)
      setPhase('done')
      navigator.vibrate?.([12, 40, 18])
    } catch (e) {
      setError(friendly(e))
    } finally {
      setSaving(false)
    }
  }

  /* ---------------------------------------------------------------- render */

  if (error && !games) return <p className="err">{error}</p>
  if (!games) return <Spinner />
  if (!games.length)
    return (
      <div className="jb picks">
        <div className="jb-wall">
          <div className="jb-strip">
            <span>{week?.label || 'This week'}</span>
          </div>
          <section className="jb-empty">
            <h2>No slate yet</h2>
            <p>Your commissioner has not published this week&apos;s twenty games.</p>
          </section>
        </div>
      </div>
    )

  /* Locked in, whether you just pressed the button or came back to a card you sent days
     ago. They were two screens, a confirmation and a read-only ranking, saying the same
     thing in two layouts; on the jumbotron both are the marquee, and only the one you just
     earned plays the lock dropping shut. */
  if (phase === 'done' || phase === 'locked')
    return (
      <LockedIn
        me={me}
        fresh={phase === 'done'}
        games={games}
        winners={winners}
        order={order}
        locked={locked}
        availableValues={availableValues}
        onEdit={reopen}
        onSeeBoard={() => onNavigate?.('board')}
      />
    )

  if (phase === 'rank')
    return (
      <RankPhase
        setToast={setToast}
        editable={editable}
        locked={locked}
        winners={winners}
        order={order}
        availableValues={availableValues}
        onReset={resetOrder}
        onMove={moveTo}
        onBack={() => setPhase('choose')}
        onSubmit={submit}
        saving={saving}
        error={error}
        toast={toast}
      />
    )

  return (
    <ChoosePhase
      games={editable}
      locked={locked}
      winners={winners}
      onChoose={choose}
      chosenCount={chosenCount}
      allChosen={allChosen}
      onDone={() => setPhase('rank')}
      onSeeBoard={() => onNavigate?.('board')}
    />
  )
}

/** The school behind an id, once the team library has landed. */
function useTeamOf() {
  const teams = useTeams()
  return useCallback((id) => teams?.find((t) => t.id === id), [teams])
}

/** The slate split by local kickoff day, in slate order: [{ key, label, games }]. */
function byDay(list) {
  const out = []
  const at = new Map()
  for (const g of list) {
    const key = dayKey(g.kickoff)
    if (!at.has(key)) {
      at.set(key, out.length)
      out.push({ key, label: weekdayLabel(g.kickoff), games: [] })
    }
    out[at.get(key)].games.push(g)
  }
  return out
}

const Check = () => (
  <svg viewBox="0 0 24 24" width="15" height="15" fill="none" aria-hidden="true">
    <path d="m5 12.5 4.2 4.2L19 7" stroke="currentColor" strokeWidth="3" strokeLinecap="round"
          strokeLinejoin="round" />
  </svg>
)

/* ================================================================== choose */

/**
 * Twenty games as a scannable list rather than twenty sequential cards.
 *
 * The first build was a one-card-at-a-time swipeable stack. It photographed well and was
 * wrong in the hand: most of the viewport sat empty, you could not see what was coming,
 * and twenty separate screens is slower than one scroll.
 *
 * On the jumbotron the list is grouped under each kickoff day, the way the week is
 * actually played, and the games that have already kicked off sit last under their own
 * heading.
 */
function ChoosePhase({
  games, locked, winners, chosenCount, allChosen, onChoose, onDone, onSeeBoard,
}) {
  const total = games.length
  /* Every game has kicked off. Reachable in the ordinary way: open Picks on a Sunday.
     The screen used to draw a progress bar at 0%, a counter reading "0/0" and a disabled
     button saying "0 still to pick", which is three ways of saying nothing while
     implying there is work to do. */
  const closed = total === 0
  const [preview, setPreview] = useState(null)
  /* AP ranks from one cached ESPN call, shared with the Board and the matchup sheet. A
     failure is silent by design; a missing rank is not worth an error message. */
  const ranks = useRanks()
  const teamOf = useTeamOf()

  return (
    <div className="jb picks">
      {!closed && (
        <div className="choose__top" aria-label={`${chosenCount} of ${total} picked`}>
          <span className="choose__count">
            <Led>{chosenCount}</Led>
            <span className="choose__of" aria-hidden="true">
              of {total}
              <br />
              picked
            </span>
          </span>
          {/* One lamp per game still to pick, lit as the count climbs. */}
          <span className="choose__meter" style={{ '--choose-lamps': total }} aria-hidden="true">
            {games.map((g, i) => (
              <i key={g.game_id} className={i < chosenCount ? 'is-on' : undefined} />
            ))}
          </span>
        </div>
      )}

      {locked.length > 0 && (
        <p className="notice">
          <IconClock />
          <span>
            {closed
              ? 'Every game has kicked off. This week is settled.'
              : `${locked.length} game${locked.length > 1 ? 's have' : ' has'} kicked off and can no longer be changed.`}
          </span>
        </p>
      )}

      <div className="jb-wall games">
        {byDay(games).map((day) => (
          <section className="games__day" key={day.key} aria-label={day.label}>
            <h3 className="games__dayname">{day.label}</h3>
            {day.games.map((g) => (
              <GameRow
                key={g.game_id}
                game={g}
                picked={winners[g.game_id]}
                onChoose={onChoose}
                ranks={ranks}
                teamOf={teamOf}
                onPreview={setPreview}
              />
            ))}
          </section>
        ))}
        {locked.length > 0 && (
          <section className="games__day" aria-label="Kicked off">
            <h3 className="games__dayname">Kicked off</h3>
            {locked.map((g) => (
              <GameRow
                key={g.game_id}
                game={g}
                picked={g.my_pick}
                onChoose={() => {}}
                isLocked
                ranks={ranks}
                teamOf={teamOf}
                onPreview={setPreview}
              />
            ))}
          </section>
        )}
      </div>

      <div className="stickycta">
        {closed ? (
          <button className="btn btn--led" onClick={onSeeBoard}>
            See the Board
          </button>
        ) : (
          <button className="btn btn--led" onClick={onDone} disabled={!allChosen}>
            {allChosen ? `Rank my ${total} picks` : `${total - chosenCount} still to pick`}
          </button>
        )}
      </div>

      {/* Keyed on the game so switching previews refetches, rather than showing the last
          one's numbers under the new one's teams. */}
      <Sheet open={!!preview} onClose={() => setPreview(null)} label="Matchup preview" flush>
        {preview && (
          <Matchup
            key={preview.game_id}
            game={preview}
            ranks={ranks}
            picked={winners[preview.game_id] || preview.my_pick}
          />
        )}
      </Sheet>
    </div>
  )
}

function GameRow({ game, picked, onChoose, isLocked = false, ranks, teamOf, onPreview }) {
  return (
    <article className={`grow${picked ? ' is-done' : ''}${isLocked ? ' is-locked' : ''}`}>
      <div className="grow__meta">
        <span className="grow__when">
          {isLocked && <IconLock size={14} />}
          {kickoffLabel(game.kickoff)}
        </span>
        {game.tv && <span className="grow__tv">{tvLabel(game.tv)}</span>}
        <span className="grow__spread num">{api.spreadLabel(game)}</span>
        {/* The way in to the matchup sheet, and the loudest thing on the tile. It was a
            quiet outlined "PREVIEW" pill once and nobody tapped it. The 32px pill gets its
            44px tap target from a pseudo-element rather than by growing the line. */}
        <button
          className="grow__preview"
          onClick={() => onPreview(game)}
          aria-label={`Matchup preview: ${game.away_abbr} at ${game.home_abbr}`}
        >
          <span className="grow__shine" aria-hidden="true" />
          Matchup
          <b aria-hidden="true">&rsaquo;</b>
        </button>
      </div>

      {/* Away on top, home below, the way a scoreboard stacks them. */}
      <div className="grow__teams">
        <TeamPick
          game={game}
          side="away"
          selected={picked === game.away_abbr}
          dimmed={!!picked && picked !== game.away_abbr}
          disabled={isLocked}
          onClick={() => onChoose(game, game.away_abbr)}
          ranks={ranks}
          teamOf={teamOf}
        />
        <TeamPick
          game={game}
          side="home"
          selected={picked === game.home_abbr}
          dimmed={!!picked && picked !== game.home_abbr}
          disabled={isLocked}
          onClick={() => onChoose(game, game.home_abbr)}
          ranks={ranks}
          teamOf={teamOf}
        />
      </div>
    </article>
  )
}

function TeamPick({ game, side, selected, dimmed, disabled, onClick, ranks, teamOf }) {
  const abbr = game[`${side}_abbr`]
  const id = game[`${side}_id`]
  const team = teamOf(id)
  const school = team?.school || game[`${side}_school`] || abbr
  // The live AP poll first. game[side_rank] only ever exists in the offline demo data,
  // because get_slate has never returned a rank column.
  const rank = rankOf(ranks, id) ?? game[`${side}_rank`]

  return (
    <button
      className={`tpick${selected ? ' is-picked' : ''}${dimmed ? ' is-other' : ''}`}
      style={{ '--jb-team': schoolPanel(team, PANEL) }}
      onClick={onClick}
      disabled={disabled}
      aria-pressed={selected}
      aria-label={`Pick ${school}`}
    >
      <Mark id={id} abbr={abbr} size={36} />
      <span className="tpick__name">
        <Rank n={rank} />
        <span className="tpick__label">{school}</span>
      </span>
      {selected ? (
        <motion.span
          className="tpick__lamp"
          layoutId={`lamp-${game.game_id}`}
          transition={{ type: 'spring', damping: 26, stiffness: 400 }}
        >
          <Check />
          Pick
        </motion.span>
      ) : (
        <span className="tpick__slot" aria-hidden="true" />
      )}
    </button>
  )
}

/* ==================================================================== rank */

/**
 * Assigning the confidence points.
 *
 * The first build was drag-to-reorder and it was unusable on a phone: the whole row was
 * the drag handle so every touch fought the page scroll, a 150ms press-and-hold felt
 * like nothing happening, and the dragged row was pinned inside a list twice the height
 * of the screen, which made moving a game from 20th to 1st effectively impossible.
 *
 * This replaces it with tap to lift, tap to place. The trick is that the left column
 * already shows the points, so while a game is lifted, tapping any row reads as "give my
 * game that many points" rather than "move to that position". People think in points.
 */
function RankPhase({
  editable,
  locked,
  winners,
  order,
  availableValues,
  onReset,
  onMove,
  onBack,
  onSubmit,
  saving,
  error,
  toast,
  setToast,
}) {
  const [lifted, setLifted] = useState(null)
  const teamOf = useTeamOf()
  const byId = useMemo(
    () => Object.fromEntries(editable.map((g) => [g.game_id, g])),
    [editable],
  )

  const top = availableValues[0]
  const bottom = availableValues[availableValues.length - 1]
  const liftedGame = lifted ? byId[lifted] : null
  const liftedPick = lifted ? winners[lifted] : null
  const sideOf = (game, abbr) => (abbr === game.home_abbr ? 'home' : 'away')
  /* The lift bar names the school, "Moving Notre Dame", where the row itself says ND. */
  const liftedName =
    (liftedGame && teamOf(liftedGame[`${sideOf(liftedGame, liftedPick)}_id`])?.school) || liftedPick

  function onRowTap(id, index) {
    if (!lifted) {
      setLifted(id)
      navigator.vibrate?.(10)
      return
    }
    if (lifted === id) {
      setLifted(null) // tapping the lifted game again puts it back down
      return
    }
    onMove(lifted, index)
    setLifted(null)
  }

  return (
    <div className="jb picks">
      <div className="rank__head">
        <button className="rank__chip" onClick={onBack}>
          <Chevron />
          Winners
        </button>
        <button className="rank__chip" onClick={onReset}>
          Reset to spread
        </button>
      </div>

      <div className="rank__intro">
        <h2 className="rank__title">Most sure at the top</h2>
        <p className="rank__sub">
          Already sorted by the spread, so the top game is worth <b>{top}</b> and the bottom{' '}
          <b>{bottom}</b>. Tap a game to move it.
        </p>
      </div>

      <div className="jb-wall rank__wall">
        {locked.length > 0 && (
          <div className="rank__list rank__list--locked">
            {locked.map((g) => {
              const side = g.my_pick ? sideOf(g, g.my_pick) : 'home'
              return (
                <div
                  className="rankrow rankrow--locked"
                  key={g.game_id}
                  style={{ '--jb-team': schoolPanel(teamOf(g[`${side}_id`]), PANEL) }}
                >
                  <Led className="rankrow__pts">{g.my_confidence ?? '–'}</Led>
                  <Mark id={g.my_pick ? g[`${side}_id`] : null} abbr={g.my_pick || '–'} size={30} />
                  {/* "No pick" has nothing to be over. Until apply_auto_picks() runs, up
                      to five minutes after kickoff, a locked game can genuinely have no
                      pick, and this read "no pick over MIZ". */}
                  <span className="rankrow__team">
                    {g.my_pick || 'No pick'}
                    {g.my_pick && (
                      <span className="rankrow__opp">
                        over {g.my_pick === g.home_abbr ? g.away_abbr : g.home_abbr}
                      </span>
                    )}
                    {!g.my_pick && (
                      <span className="rankrow__opp">
                        {g.away_abbr} at {g.home_abbr}
                      </span>
                    )}
                  </span>
                  <span className="rankrow__cue">
                    <IconLock size={15} />
                    Locked
                  </span>
                </div>
              )
            })}
          </div>
        )}

        <ul className={`rank__list${lifted ? ' is-moving' : ''}`}>
          {order.map((id, i) => {
            const game = byId[id]
            if (!game) return null
            const pick = winners[id]
            const opp = pick === game.home_abbr ? game.away_abbr : game.home_abbr
            const logoId = pick === game.home_abbr ? game.home_id : game.away_id
            const isLifted = lifted === id
            const isTarget = !!lifted && !isLifted

            return (
              <motion.li
                key={id}
                layout
                transition={{ type: 'spring', damping: 30, stiffness: 420 }}
                className={`rankrow${isLifted ? ' is-lifted' : ''}${isTarget ? ' is-target' : ''}`}
                style={{ '--jb-team': schoolPanel(teamOf(logoId), PANEL) }}
              >
                <button
                  className="rankrow__hit"
                  onClick={() => onRowTap(id, i)}
                  aria-label={
                    isLifted
                      ? `${pick} is selected. Tap another game to place it, or tap again to cancel.`
                      : lifted
                        ? `Give ${liftedPick} ${availableValues[i]} points`
                        : `Move ${pick}, currently ${availableValues[i]} points. ${api.spreadLabel(game)}`
                  }
                >
                  <Led className="rankrow__pts">{availableValues[i]}</Led>
                  <Mark id={logoId} abbr={pick} size={30} />
                  <span className="rankrow__team">
                    {pick}
                    <span className="rankrow__opp num">
                      over {opp} · {api.spreadLabel(game)}
                    </span>
                  </span>
                  <span className="rankrow__cue">
                    {isLifted ? 'Moving' : isTarget ? 'Here' : <IconGrip />}
                  </span>
                </button>
              </motion.li>
            )
          })}
        </ul>
      </div>

      {error && <p className="err">{error}</p>}

      {!lifted && (
        <div className="stickycta">
          <button className="btn btn--led" onClick={onSubmit} disabled={saving}>
            {saving ? 'Saving…' : 'Lock in my picks'}
          </button>
        </div>
      )}

      {/* Fixed, not sticky: with twenty rows a sticky bar sits at the end of the list and
          is off-screen exactly when you lift something near the top. */}
      {lifted && (
        <Portal>
          <div className="liftbar">
            <span className="liftbar__text">
              Moving <strong>{liftedName}</strong>. Tap a row to give it those points.
            </span>
            <button className="liftbar__cancel" onClick={() => setLifted(null)}>
              Cancel
            </button>
          </div>
        </Portal>
      )}

      <Toast message={toast} onDone={() => setToast(null)} />
    </div>
  )
}

/* ============================================================== locked in */

/**
 * The shackle drops into the body, so submitting reads as closing something rather
 * than sending it. Only when you have just done it: coming back to a card you sent on
 * Tuesday shows the lock already shut.
 *
 * Nothing here animates opacity, and nothing starts invisible. A backgrounded tab
 * stops driving animation frames, and an opacity-from-zero version of this stranded
 * an empty green circle on screen with no padlock in it. Frozen mid-spring, a
 * transform-only lock is still a lock, just with the shackle slightly raised.
 */
function LockMark({ animate }) {
  return (
    <motion.div
      className="done__mark"
      initial={animate ? { scale: 0.55 } : false}
      animate={{ scale: 1 }}
      transition={{ type: 'spring', damping: 14, stiffness: 260 }}
    >
      <svg viewBox="0 0 24 24" width="40" height="40" fill="none" aria-hidden="true">
        <motion.path
          d="M8 12.6V7.6a4 4 0 0 1 8 0v5"
          stroke="currentColor"
          strokeWidth="2.3"
          strokeLinecap="round"
          initial={animate ? { y: -4.5 } : false}
          animate={{ y: 0 }}
          transition={{ delay: 0.22, type: 'spring', damping: 9, stiffness: 700 }}
        />
        <rect x="4.4" y="11.4" width="15.2" height="9.8" rx="2.4" fill="currentColor" />
        <path d="M12 15.2v2.4" stroke="#030406" strokeWidth="1.9" strokeLinecap="round" />
      </svg>
    </motion.div>
  )
}

function LockedIn({ me, fresh, games, winners, order, locked, availableValues, onEdit, onSeeBoard }) {
  const teamOf = useTeamOf()
  const byId = Object.fromEntries(games.map((g) => [g.game_id, g]))
  const rows = [
    ...locked.map((g) => ({
      id: g.game_id,
      pick: g.my_pick,
      points: g.my_confidence,
    })),
    ...order.map((id, i) => ({
      id,
      pick: winners[id] ?? byId[id]?.my_pick,
      points: availableValues[i],
    })),
  ]
    .filter((r) => r.pick && byId[r.id])
    .sort((a, b) => (b.points ?? 0) - (a.points ?? 0))

  /* The crawl only counts things anyone can check against the card above it. A game
     with no line has no favourite, so it is neither. */
  const favorites = rows.filter((r) => byId[r.id].favorite_abbr === r.pick).length
  const underdogs = rows.filter((r) => byId[r.id].favorite_abbr && byId[r.id].favorite_abbr !== r.pick).length
  const top = rows[0]
  const crawl = [
    me?.name ? `${me.name} is locked in` : 'Locked in',
    `${favorites} favorite${favorites === 1 ? '' : 's'}`,
    `${underdogs} underdog${underdogs === 1 ? '' : 's'}`,
    top && top.points != null ? `${top.points} on ${top.pick}` : null,
    'Changes allowed until each kickoff',
  ]
    .filter(Boolean)
    .join('   ◆   ')

  return (
    <div className="jb picks done">
      <section className="done__marquee" aria-label="Picks are in">
        <span className="done__bulbs" aria-hidden="true" />
        <div className="done__screen">
          <LockMark animate={fresh} />
          <h2 className="done__headline">
            <Led>Picks</Led>
            <Led>are in</Led>
          </h2>
          <p className="done__sub">Saved. Change any game right up until it kicks off.</p>
          <div className="done__cta">
            <button className="btn btn--led" onClick={onSeeBoard}>
              See the big board
            </button>
            <button className="btn btn--led btn--led-ghost" onClick={onEdit}>
              Change something
            </button>
          </div>
        </div>
      </section>

      {rows.length > 0 && (
        <div className="jb-wall">
          <h3 className="games__dayname">Your card</h3>
          <ul className="done__list">
            {rows.map((r) => {
              const g = byId[r.id]
              const opp = r.pick === g.home_abbr ? g.away_abbr : g.home_abbr
              const logoId = r.pick === g.home_abbr ? g.home_id : g.away_id
              return (
                <li
                  className="done__row"
                  key={r.id}
                  style={{ '--jb-team': schoolPanel(teamOf(logoId), PANEL) }}
                >
                  <Led className="done__pts">{r.points ?? '–'}</Led>
                  <Mark id={logoId} abbr={r.pick} size={26} />
                  <span className="done__who">
                    <b>{r.pick}</b>
                    <span>over {opp}</span>
                  </span>
                  <span className="done__when">
                    {g.locked ? (
                      <>
                        <IconLock size={14} />
                        Locked
                      </>
                    ) : (
                      kickoffLabel(g.kickoff)
                    )}
                  </span>
                </li>
              )
            })}
          </ul>
        </div>
      )}

      <div className="jb-crawl done__crawl" aria-label="Your card">
        <span className="jb-crawl__k">Locked</span>
        <div className="jb-crawl__win">
          <div className="jb-crawl__run">
            <span>{crawl}</span>
            <span aria-hidden="true">{crawl}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

/* =================================================================== draft */

function readDraft(playerId) {
  try {
    return JSON.parse(localStorage.getItem(DRAFT_KEY) || '{}')[playerId] || null
  } catch {
    return null
  }
}
function writeDraft(playerId, draft) {
  try {
    const all = JSON.parse(localStorage.getItem(DRAFT_KEY) || '{}')
    all[playerId] = draft
    localStorage.setItem(DRAFT_KEY, JSON.stringify(all))
  } catch {
    /* nothing lost that matters; the server is the record */
  }
}
function clearDraft(playerId) {
  try {
    const all = JSON.parse(localStorage.getItem(DRAFT_KEY) || '{}')
    delete all[playerId]
    localStorage.setItem(DRAFT_KEY, JSON.stringify(all))
  } catch {
    /* ignore */
  }
}
