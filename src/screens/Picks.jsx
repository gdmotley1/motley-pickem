import { useCallback, useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import * as api from '../lib/api.js'
import TeamLogo from '../components/TeamLogo.jsx'
import {
  Back,
  Empty,
  IconClock,
  IconGrip,
  Portal,
  Screen,
  Spinner,
  Toast,
} from '../components/ui.jsx'
import { kickoffLabel } from '../lib/format.js'

const DRAFT_KEY = 'pickem.draft.v1'

export default function Picks({ me, weekId }) {
  const [games, setGames] = useState(null)
  const [error, setError] = useState(null)
  const [phase, setPhase] = useState('choose') // choose | rank | done
  const [winners, setWinners] = useState({})
  const [order, setOrder] = useState([])
  const [orderTouched, setOrderTouched] = useState(false)
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
        const saved = (draft?.order || []).filter((id) =>
          editable.some((g) => g.game_id === id),
        )
        const missing = editable
          .map((g) => g.game_id)
          .filter((id) => !saved.includes(id))
        setOrder([...saved, ...missing])
        setOrderTouched(!!draft?.touched)

        const submitted = rows.length > 0 && rows.every((g) => g.my_pick)
        if (submitted && !draft) setPhase('done')
        else if (editable.length && editable.every((g) => w[g.game_id])) setPhase('rank')
      })
      .catch((e) => alive && setError(e.message))
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
    if (games) writeDraft(me.id, { winners, order, touched: orderTouched })
  }, [winners, order, orderTouched, games, me.id])

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
      setPhase('done')
      navigator.vibrate?.([12, 40, 18])
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  /* ---------------------------------------------------------------- render */

  if (error && !games) return <p className="err">{error}</p>
  if (!games) return <Spinner />
  if (!games.length)
    return (
      <Screen eyebrow="Week 2" title="No slate yet">
        <Empty icon={<IconClock />} title="Nothing published">
          Your commissioner has not published this week&apos;s twenty games.
        </Empty>
      </Screen>
    )

  if (phase === 'done')
    return (
      <Done
        games={games}
        winners={winners}
        order={order}
        locked={locked}
        availableValues={availableValues}
        onEdit={() => setPhase('rank')}
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
        setOrder={setOrder}
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
    />
  )
}

/* ================================================================== choose */

/**
 * Twenty games as a scannable list rather than twenty sequential cards.
 *
 * The first build was a one-card-at-a-time swipeable stack. It photographed well and was
 * wrong in the hand: most of the viewport sat empty, you could not see what was coming,
 * and twenty separate screens is slower than one scroll.
 */
function ChoosePhase({ games, locked, winners, chosenCount, allChosen, onChoose, onDone }) {
  const total = games.length

  return (
    <div>
      <div className="choose__top">
        <div className="progress" aria-label={`${chosenCount} of ${total} picked`}>
          <div
            className="progress__fill"
            style={{ width: `${total ? (chosenCount / total) * 100 : 0}%` }}
          />
        </div>
        <span className="choose__count num">
          {chosenCount}/{total}
        </span>
      </div>

      {locked.length > 0 && (
        <p className="notice">
          <IconClock />
          <span>
            {locked.length} game{locked.length > 1 ? 's have' : ' has'} kicked off and can no
            longer be changed.
          </span>
        </p>
      )}

      <ul className="games">
        {games.map((g) => (
          <li key={g.game_id}>
            <GameRow game={g} picked={winners[g.game_id]} onChoose={onChoose} />
          </li>
        ))}
        {locked.map((g) => (
          <li key={g.game_id}>
            <GameRow game={g} picked={g.my_pick} onChoose={() => {}} isLocked />
          </li>
        ))}
      </ul>

      <div className="stickycta">
        <button className="btn" onClick={onDone} disabled={!allChosen}>
          {allChosen ? `Rank my ${total} picks` : `${total - chosenCount} still to pick`}
        </button>
      </div>
    </div>
  )
}

function GameRow({ game, picked, onChoose, isLocked = false }) {
  return (
    <div className={`grow${picked ? ' is-done' : ''}${isLocked ? ' is-locked' : ''}`}>
      <div className="grow__meta">
        <span>{kickoffLabel(game.kickoff)}</span>
        <span className="grow__dot">·</span>
        <span className="grow__spread num">{api.spreadLabel(game)}</span>
        {isLocked && <span className="chip chip--red">locked</span>}
        {game.tv && <span className="grow__tv">{game.tv}</span>}
      </div>

      <div className="grow__teams">
        <TeamPick
          game={game}
          side="away"
          selected={picked === game.away_abbr}
          disabled={isLocked}
          onClick={() => onChoose(game, game.away_abbr)}
        />
        <span className="grow__at">{game.neutral_site ? 'vs' : '@'}</span>
        <TeamPick
          game={game}
          side="home"
          selected={picked === game.home_abbr}
          disabled={isLocked}
          onClick={() => onChoose(game, game.home_abbr)}
        />
      </div>
    </div>
  )
}

function TeamPick({ game, side, selected, disabled, onClick }) {
  const abbr = game[`${side}_abbr`]
  const school = game[`${side}_school`] || abbr
  const rank = game[`${side}_rank`]
  const record = game[`${side}_record`]

  return (
    <button
      className={`tpick${selected ? ' is-picked' : ''}`}
      onClick={onClick}
      disabled={disabled}
      aria-pressed={selected}
      aria-label={`Pick ${school}`}
    >
      <TeamLogo teamId={game[`${side}_id`]} abbr={abbr} size={38} />
      <span className="tpick__name">
        {rank ? <span className="tpick__rank num">{rank}</span> : null}
        {school}
      </span>
      {record ? <span className="tpick__rec num">{record}</span> : null}
      {selected && (
        <motion.span
          className="tpick__ring"
          layoutId={`ring-${game.game_id}`}
          transition={{ type: 'spring', damping: 26, stiffness: 400 }}
        />
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
  const byId = useMemo(
    () => Object.fromEntries(editable.map((g) => [g.game_id, g])),
    [editable],
  )

  const top = availableValues[0]
  const bottom = availableValues[availableValues.length - 1]
  const liftedGame = lifted ? byId[lifted] : null
  const liftedPick = lifted ? winners[lifted] : null

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
    <div>
      <div className="rank__head">
        <Back onClick={onBack} label="Winners" />
        <button className="pill pill--quiet" onClick={onReset}>
          Reset to spread
        </button>
      </div>

      <div className="rank__intro">
        <h2 className="h2">Most sure at the top</h2>
        <p className="sub">
          Already sorted by the spread, so the top game is worth <strong>{top}</strong> and
          the bottom <strong>{bottom}</strong>. Tap a game to move it.
        </p>
      </div>

      {locked.length > 0 && (
        <div className="rank__list" style={{ marginBottom: 8 }}>
          {locked.map((g) => (
            <div className="rankrow rankrow--locked" key={g.game_id}>
              <span className="rankrow__pts num">{g.my_confidence ?? '—'}</span>
              <TeamLogo
                teamId={g.my_pick === g.home_abbr ? g.home_id : g.away_id}
                abbr={g.my_pick}
                size={26}
              />
              <span className="rankrow__team">
                {g.my_pick || 'no pick'}
                <span className="rankrow__opp">
                  over {g.my_pick === g.home_abbr ? g.away_abbr : g.home_abbr}
                </span>
              </span>
              <span className="rankrow__lock">locked</span>
            </div>
          ))}
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
              className={`rankrow${isLifted ? ' is-lifted' : ''}${
                isTarget ? ' is-target' : ''
              }`}
            >
              <button
                className="rankrow__hit"
                onClick={() => onRowTap(id, i)}
                aria-label={
                  isLifted
                    ? `${pick} is selected. Tap another game to place it, or tap again to cancel.`
                    : lifted
                      ? `Give ${liftedPick} ${availableValues[i]} points`
                      : `Move ${pick}, currently ${availableValues[i]} points`
                }
              >
                <span className="rankrow__pts num">{availableValues[i]}</span>
                <TeamLogo teamId={logoId} abbr={pick} size={26} />
                <span className="rankrow__team">
                  {pick}
                  <span className="rankrow__opp">over {opp}</span>
                </span>
                <span className="rankrow__cue">
                  {isLifted ? 'moving' : isTarget ? 'here' : <IconGrip />}
                </span>
              </button>
            </motion.li>
          )
        })}
      </ul>

      {error && <p className="err">{error}</p>}

      {!lifted && (
        <div className="stickycta">
          <button className="btn" onClick={onSubmit} disabled={saving}>
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
            Moving <strong>{liftedPick}</strong>. Tap a row to give it those points.
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

/* ==================================================================== done */

function Done({ games, winners, order, locked, availableValues, onEdit }) {
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
    .filter((r) => r.pick)
    .sort((a, b) => (b.points ?? 0) - (a.points ?? 0))

  return (
    <div className="done">
      <motion.div
        className="done__mark"
        initial={{ scale: 0.55, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: 'spring', damping: 14, stiffness: 260 }}
      >
        ✓
      </motion.div>
      <h2 className="h1">You&apos;re in</h2>
      <p className="sub">
        Picks are saved. Change any game right up until it kicks off.
      </p>

      <button className="btn btn--ghost" onClick={onEdit}>
        Change something
      </button>

      {rows.length > 0 && (
        <ul className="done__list">
          {rows.map((r) => {
            const g = byId[r.id]
            if (!g) return null
            const opp = r.pick === g.home_abbr ? g.away_abbr : g.home_abbr
            const logoId = r.pick === g.home_abbr ? g.home_id : g.away_id
            return (
              <li className="done__row" key={r.id}>
                <span className="done__pts num">{r.points}</span>
                <TeamLogo teamId={logoId} abbr={r.pick} size={22} />
                <span style={{ flex: 1, minWidth: 0 }}>
                  {r.pick} <span style={{ color: 'var(--ink-3)' }}>over {opp}</span>
                </span>
                {g.locked && <span className="chip chip--red">locked</span>}
              </li>
            )
          })}
        </ul>
      )}
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
