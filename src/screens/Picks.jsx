import { useCallback, useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  TouchSensor,
  closestCenter,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { restrictToParentElement, restrictToVerticalAxis } from '@dnd-kit/modifiers'
import { CSS } from '@dnd-kit/utilities'
import * as api from '../lib/api.js'
import TeamLogo from '../components/TeamLogo.jsx'
import {
  Back,
  Empty,
  IconClock,
  IconGrip,
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
    if (games) writeDraft(me.id, { winners, order })
  }, [winners, order, games, me.id])

  /* --------------------------------------------------------------- actions */

  const choose = useCallback((game, abbr) => {
    setWinners((w) => ({ ...w, [game.game_id]: abbr }))
    navigator.vibrate?.(8)
  }, [])

  const autoRank = useCallback(() => {
    // Order by how sure Vegas is, most certain first. The whole point is that you move
    // only the handful you disagree with instead of sorting twenty games by hand.
    const score = (g) => {
      const line = g.spread_line == null ? 0 : Number(g.spread_line)
      return winners[g.game_id] === g.favorite_abbr ? line : -line
    }
    setOrder((cur) =>
      [...cur].sort((a, b) => {
        const ga = editable.find((g) => g.game_id === a)
        const gb = editable.find((g) => g.game_id === b)
        if (!ga || !gb) return 0
        return score(gb) - score(ga)
      }),
    )
    navigator.vibrate?.(14)
    setToast('Ranked by the spread. Drag anything you disagree with.')
  }, [editable, winners])

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
        editable={editable}
        locked={locked}
        winners={winners}
        order={order}
        setOrder={setOrder}
        availableValues={availableValues}
        onAutoRank={autoRank}
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

function RankPhase({
  editable,
  locked,
  winners,
  order,
  setOrder,
  availableValues,
  onAutoRank,
  onBack,
  onSubmit,
  saving,
  error,
  toast,
}) {
  const byId = useMemo(
    () => Object.fromEntries(editable.map((g) => [g.game_id, g])),
    [editable],
  )
  const sensors = useSensors(
    // The delay lets a vertical scroll win, so the list does not grab every touch.
    useSensor(TouchSensor, { activationConstraint: { delay: 150, tolerance: 8 } }),
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const top = availableValues[0]
  const bottom = availableValues[availableValues.length - 1]

  return (
    <div>
      <div className="rank__head">
        <Back onClick={onBack} label="Winners" />
        <button className="pill" onClick={onAutoRank}>
          Auto-rank by spread
        </button>
      </div>

      <div className="rank__intro">
        <h2 className="h2">Most sure at the top</h2>
        <p className="sub">
          The top game is worth <strong>{top}</strong> points, the bottom one{' '}
          <strong>{bottom}</strong>. Press and hold a row to move it.
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

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={({ active, over }) => {
          if (!over || active.id === over.id) return
          setOrder((cur) => arrayMove(cur, cur.indexOf(active.id), cur.indexOf(over.id)))
          navigator.vibrate?.(8)
        }}
        modifiers={[restrictToVerticalAxis, restrictToParentElement]}
      >
        <SortableContext items={order} strategy={verticalListSortingStrategy}>
          <ul className="rank__list">
            {order.map((id, i) => (
              <RankRow
                key={id}
                id={id}
                game={byId[id]}
                pick={winners[id]}
                points={availableValues[i]}
              />
            ))}
          </ul>
        </SortableContext>
      </DndContext>

      {error && <p className="err">{error}</p>}

      <div className="stickycta">
        <button className="btn" onClick={onSubmit} disabled={saving}>
          {saving ? 'Saving…' : 'Lock in my picks'}
        </button>
      </div>

      <Toast message={toast} onDone={() => setToast(null)} />
    </div>
  )
}

function RankRow({ id, game, pick, points }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id })
  if (!game) return null
  const opp = pick === game.home_abbr ? game.away_abbr : game.home_abbr
  const logoId = pick === game.home_abbr ? game.home_id : game.away_id

  return (
    <li
      ref={setNodeRef}
      className={`rankrow${isDragging ? ' is-dragging' : ''}`}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      {...attributes}
      {...listeners}
    >
      <span className="rankrow__pts num">{points}</span>
      <TeamLogo teamId={logoId} abbr={pick} size={26} />
      <span className="rankrow__team">
        {pick}
        <span className="rankrow__opp">over {opp}</span>
      </span>
      <span className="rankrow__grip">
        <IconGrip />
      </span>
    </li>
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
