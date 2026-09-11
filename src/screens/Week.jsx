import { useCallback, useEffect, useMemo, useState } from 'react'
import * as api from '../lib/api.js'
import { friendly } from '../lib/errors.js'
import { Avatar, Chevron, Empty, IconTrophy, Screen, Sheet, Spinner } from '../components/ui.jsx'
import { withLive } from '../lib/espn.js'
import { useLiveScores } from '../lib/useLiveScores.js'
import { weekRecap } from '../lib/weekRecap.js'
import { weekScore } from '../lib/weekScore.js'
import { WeekScore } from '../components/WeekScore.jsx'
import { isComplete, weekNav, weekStatus, winnersByWeek } from '../lib/weekNav.js'

/**
 * One week, settled: who won it, and what the numbers say about how.
 *
 * This replaced a season-only Standings screen that printed the same two figures three
 * times, in a table and then again as two bar charts. Season totals moved to their own
 * tab; what is left here is the week, which is the thing anyone actually opens this for.
 *
 * The recap below the table only renders once every game has a winner. That is a
 * deliberate choice rather than a safety rule: a locked game's picks are already public,
 * so a running recap would be legal, but a stat that moves while somebody is reading it
 * is worse than one that arrives late. Until then the table stands on its own.
 *
 * Nothing here characterises anybody. Every line is a count over the picks or a what-if
 * that weekRecap actually recomputed. See the note at the top of src/lib/weekRecap.js
 * for the claim that got cut and why.
 */
export default function Week({ me, weekId, week }) {
  const [slate, setSlate] = useState(null)
  const [rows, setRows] = useState(null)
  const [roster, setRoster] = useState(null)
  const [weeks, setWeeks] = useState(null)
  const [error, setError] = useState(null)

  /* Which week this screen is looking at.

     Local on purpose. `weekId` is one setting shared by every tab, so stepping it here
     would drag Picks and Board back with it: you would flip to Week 1 to settle an
     argument, open Picks, and find the whole slate locked. This resets on its own when
     the tab changes, because App unmounts the screen. */
  const [viewId, setViewId] = useState(weekId)

  /* Follow the app when it resolves the real current week, which arrives after first
     paint. Once the user has stepped somewhere themselves that only happens on a week
     rollover, which should pull them forward anyway. */
  useEffect(() => setViewId(weekId), [weekId])

  useEffect(() => {
    let alive = true
    api
      .listWeeks()
      .then((w) => alive && setWeeks(w))
      .catch((e) => alive && setError(friendly(e)))
    return () => {
      alive = false
    }
  }, [])

  useEffect(() => {
    let alive = true
    setSlate(null)
    setRows(null)
    Promise.all([api.getSlate(viewId), api.getBoard(viewId), api.listSeats()])
      .then(([s, b, seats]) => {
        if (!alive) return
        setSlate(s)
        setRows(b)
        setRoster(seats.filter((x) => x.claimed))
      })
      .catch((e) => alive && setError(friendly(e)))
    return () => {
      alive = false
    }
  }, [viewId])

  const live = useLiveScores(slate)

  /* Same overlay the Board uses, so a final counts here the moment ESPN reports it
     rather than whenever the sync job next runs. withLive defers to a database winner
     wherever there is one, so the two can never disagree. */
  const games = useMemo(() => {
    if (!slate) return null
    return live ? slate.map((g) => withLive(g, live)) : slate
  }, [slate, live])

  const recap = useMemo(
    () => (games && rows && roster ? weekRecap(games, rows, roster) : null),
    [games, rows, roster],
  )

  /* The same object the Board's scorebug reads, so the two screens can never disagree
     about who is where. Grant asked on 2026-09-10 for this tab to carry the bug rather
     than its own light table. */
  const score = useMemo(
    () => (games && rows && roster ? weekScore(games, rows, roster) : null),
    [games, rows, roster],
  )

  if (error) return <p className="err">{error}</p>

  const nav = weekNav(weeks, week?.week_no, viewId)
  const viewing = nav.current
  const label = viewing?.label || week?.label || 'This week'
  const pager = (
    <Pager nav={nav} onGo={setViewId} weeks={weeks} currentWeekNo={week?.week_no} />
  )

  if (!recap)
    return (
      <>
        {pager}
        <Spinner />
      </>
    )

  const played = recap.players.filter((p) => p.games > 0)

  /* An empty week is now a place you can deliberately arrive at, so it has to say which
     kind of empty it is. Before the arrows existed you could only ever be on the current
     week and "nothing yet" was the only possibility. */
  if (!played.length) {
    const status = weekStatus(viewing)

    /* A published week with a slate that simply has not started is not "nothing to
       show": the players are known, the twenty games are known, and only the numbers are
       missing. Drawing the real scorebug with no numbers in it says that, where the old
       empty state said the tab was broken. The other two statuses genuinely have nothing
       to frame, so they keep their message. */
    if (status === 'no results yet' && score) {
      /* Nothing is final either way, so the numbers stay blank. The heading is the part
         that has to tell the truth: the bug is already showing a red "20 live" chip. */
      const underway = score.playing > 0
      return (
        <>
          {pager}
          <Screen eyebrow={label} title={underway ? 'Underway' : 'Not started yet'}>
            <WeekScore
              score={score}
              me={me}
              label={label}
              skeleton
              record
              light
              note={`0 of ${score.slateSize}`}
              foot={`Out of ${score.total}. Points appear here as games go final.`}
            />
          </Screen>
        </>
      )
    }

    return (
      <>
        {pager}
        <Screen eyebrow={label} title="Nothing to show">
          <Empty icon={<IconTrophy />} title={emptyTitle(status)}>
            {emptyBody(status)}
          </Empty>
        </Screen>
      </>
    )
  }

  const mine = recap.players.find((p) => p.id === me?.id)

  return (
    <>
      {pager}
      <Screen
        eyebrow={recap.complete ? 'Final' : 'In progress'}
        title={recap.complete ? headline(recap) : label}
        sub={
          recap.complete
            ? undefined
            : 'Ties stand. The write-up lands once every game has finished.'
        }
      >
        <WeekScore score={score} me={me} label={label} record light />

        {recap.complete && mine && <YourWeek p={mine} />}
        {recap.complete && <Ranking players={recap.players} />}
        {recap.complete && <Decisive recap={recap} />}
        {recap.complete && <Upsets list={recap.upsets} />}
        {recap.complete && <InNumbers recap={recap} />}
      </Screen>
    </>
  )
}

const emptyTitle = (status) =>
  ({
    'not published': 'Not published yet',
    'no slate yet': 'No slate yet',
    'no results yet': 'No games finished',
  })[status] || 'Nothing to show yet'

const emptyBody = (status) =>
  ({
    'not published': 'Your commissioner has not published this week’s twenty games.',
    'no slate yet': 'The twenty games for this week have not been chosen.',
    'no results yet': 'The table fills in here as games go final.',
  })[status] ||
  'Once games start going final, the table fills in here. The full write-up lands when the last game of the week ends.'

/** "Grant takes it by 7", or the shared version. Both are statements of the score. */
function headline(recap) {
  const names = recap.leaders.map((p) => p.name)
  if (names.length > 1) return `${list(names)} share it`
  return recap.margin > 0 ? `${names[0]} takes it by ${recap.margin}` : `${names[0]} takes it`
}

const list = (xs) =>
  xs.length <= 1 ? xs[0] || '' : `${xs.slice(0, -1).join(', ')} and ${xs[xs.length - 1]}`

/**
 * The signed-in player's own week.
 *
 * "Against the field" rather than "your best pick", because a player's biggest correct
 * pick is nearly always just whatever they put 20 on, which tells them nothing. The game
 * where they took the most points out of everyone else is a real edge, and the same
 * arithmetic run the other way finds where the week got away from them.
 */
function YourWeek({ p }) {
  return (
    <>
      <div className="screen">
        <h3 className="h2">Your week</h3>
      </div>
      <div className="stand">
        <div className="yw">
          <div className="yw__top">
            <Avatar name={p.name} color={p.color} teamId={p.team_id} size={30} />
            <span className="yw__line num">
              {p.correct}-{p.wrong}, {p.points} points, {p.captured}% of your ceiling
            </span>
          </div>
          {p.best && (
            <p className="yw__row">
              <span className="yw__k">Gained most</span>
              <span className="yw__v">
                {p.best.pick} at {p.best.confidence} in {p.best.label}
                <b className="num"> +{p.best.edge}</b> on the field
              </span>
            </p>
          )}
          {p.worst && (
            <p className="yw__row">
              <span className="yw__k">Lost most</span>
              <span className="yw__v">
                {p.worst.pick} at {p.worst.confidence} in {p.worst.label}
                <b className="num is-bad"> {p.worst.edge}</b> on the field
              </span>
            </p>
          )}
          {p.soloRight > 0 && (
            <p className="yw__row">
              <span className="yw__k">On your own</span>
              <span className="yw__v">
                {p.soloRight} {p.soloRight === 1 ? 'game' : 'games'} nobody else called
                right
              </span>
            </p>
          )}
        </div>
      </div>
    </>
  )
}

/**
 * Ranking, separated from picking.
 *
 * A week spends 1 to 20 exactly once, so a player who got c games right could at best
 * have put their top c numbers on them. Comparing what they scored against that is the
 * only stat here that can flatter somebody who finished last, and in the first real week
 * it did exactly that.
 */
function Ranking({ players }) {
  const sorted = [...players].filter((p) => p.games > 0).sort((a, b) => b.captured - a.captured)
  return (
    <>
      <div className="screen">
        <h3 className="h2">Ranking</h3>
        <p className="sub">
          Points banked against the most that ranking could have been worth, given the
          games each person got right. This measures the confidence order, not the picks.
        </p>
      </div>
      <div className="bars">
        {sorted.map((p) => (
          <div className="bar" key={p.id}>
            <span className="bar__name">{p.name}</span>
            <span className="bar__track">
              <span
                className="bar__fill"
                style={{ width: `${p.captured}%`, background: p.color }}
              />
            </span>
            <span className="bar__val num">{p.captured}%</span>
          </div>
        ))}
      </div>
      <div className="screen">
        <p className="sub num">
          {sorted[0].name} got the most out of {sorted[0].correct} correct picks:{' '}
          {sorted[0].points} of a possible {sorted[0].ceiling}.
        </p>
      </div>
    </>
  )
}

/**
 * The games the week actually turned on.
 *
 * Each one was found by flipping that single result and re-running the standings, so a
 * game is listed because the winner genuinely changes, not because its swing happened to
 * match the final margin. An empty list is a real answer and gets said out loud.
 */
function Decisive({ recap }) {
  const { decisive } = recap
  return (
    <>
      <div className="screen">
        <h3 className="h2">What would have changed it</h3>
        <p className="sub">
          {decisive.length === 0
            ? 'Nothing. No single result reversed would have changed who won, so this week was taken on the whole slate.'
            : `Flip any one of these and the week ends differently. Every other game could have gone the other way without moving the top.`}
        </p>
      </div>
      {decisive.length > 0 && (
        <div className="stand">
          {decisive.map((d) => (
            <div className="flip" key={d.game_id}>
              <span className="flip__game">{d.label}</span>
              <span className="flip__body">
                <b>{d.instead}</b> instead of {d.actual} and{' '}
                {d.shared ? (
                  <>
                    it is a tie: <b>{list(d.leaders)}</b> on {d.points}
                  </>
                ) : (
                  <>
                    <b>{d.leaders[0]}</b> wins it on {d.points}
                  </>
                )}
              </span>
            </div>
          ))}
        </div>
      )}
    </>
  )
}

function Upsets({ list: ups }) {
  if (!ups.length) return null
  return (
    <>
      <div className="screen">
        <h3 className="h2">Upsets</h3>
        <p className="sub">
          Games the favourite lost, biggest first, and who had the winner.
        </p>
      </div>
      <div className="stand">
        {ups.map((u) => (
          <div className="ups" key={u.game_id}>
            <span className="ups__head">
              <span className="ups__game">{u.label}</span>
              {u.line != null && <span className="chip">+{u.line}</span>}
            </span>
            <span className="ups__body">
              {u.winner} won.{' '}
              {u.calledBy.length ? (
                <>
                  Called by <b>{list(u.calledBy)}</b>
                </>
              ) : (
                <span className="is-muted">Nobody called it</span>
              )}
            </span>
          </div>
        ))}
      </div>
    </>
  )
}

function InNumbers({ recap }) {
  const tiles = [
    {
      k: 'Chalk',
      v: recap.chalk.won,
      u: `of ${recap.chalk.of}`,
      s: 'favourites that held',
    },
    {
      k: 'Upsets',
      v: recap.upsets.length,
      u: `of ${recap.slateSize}`,
      s: `${recap.upsets.filter((u) => u.calledBy.length).length} called`,
    },
    {
      k: 'Whiffs',
      v: recap.whiffs.length,
      u: 'games',
      s: 'nobody got right',
    },
    {
      k: 'Agreed',
      v: recap.sweeps,
      u: 'games',
      s: 'everybody got right',
    },
  ]
  return (
    <>
      <div className="screen">
        <h3 className="h2">The week in numbers</h3>
      </div>
      <div className="tiles">
        {tiles.map((t) => (
          <div className="tile" key={t.k}>
            <p className="tile__k">{t.k}</p>
            <p className="tile__v num">
              {t.v}
              <span>{t.u}</span>
            </p>
            <p className="tile__s">{t.s}</p>
          </div>
        ))}
      </div>
      {recap.whiffs.length > 0 && (
        <div className="screen">
          <p className="sub">
            Nobody in the family called{' '}
            {list(recap.whiffs.map((w) => w.label))}.
          </p>
        </div>
      )}
    </>
  )
}

/**
 * The week pager: an arrow either side, and a label that opens a jump list.
 *
 * Option C from the board Grant chose on 2026-09-10. The arrows are the common case,
 * one step back; the sheet is what stops week 3 being eleven taps away in November.
 *
 * Both arrows are real 36px targets rather than glyphs on the eyebrow line, which is the
 * whole reason this is its own row and costs 46px. An edge is a null in `nav`, so a
 * disabled arrow is a fact from weekNav rather than a condition restated here.
 */
function Pager({ nav, onGo, weeks, currentWeekNo }) {
  const [open, setOpen] = useState(false)
  const [season, setSeason] = useState(null)
  const viewing = nav.current

  /* The winners are only ever read by the sheet, so they load on first open and stay.
     The pager itself never needs them, and the screen already makes three calls. */
  const openPicker = useCallback(() => {
    setOpen(true)
    setSeason((prev) => {
      if (prev) return prev
      api.getSeason().then(setSeason).catch(() => setSeason([]))
      return prev
    })
  }, [])

  const status = weekStatus(viewing)
  const sub = status || (isComplete(viewing) ? 'final' : dateRange(viewing))

  return (
    <>
      <div className="wknav">
        <button
          className="wknav__arrow"
          onClick={() => nav.prev && onGo(nav.prev.id)}
          disabled={!nav.prev}
          aria-label={nav.prev ? `Go to ${nav.prev.label}` : 'No earlier week'}
        >
          <Chevron dir="left" size={17} />
        </button>

        <button className="wknav__mid" onClick={openPicker} aria-label="Choose a week">
          <b>
            {viewing?.label || 'This week'}
            <Chevron dir="down" size={13} />
          </b>
          <i>{sub}</i>
        </button>

        <button
          className="wknav__arrow"
          onClick={() => nav.next && onGo(nav.next.id)}
          disabled={!nav.next}
          aria-label={nav.next ? `Go to ${nav.next.label}` : 'No later week'}
        >
          <Chevron dir="right" size={17} />
        </button>
      </div>

      {!nav.isCurrent && nav.list.length > 0 && (
        <button
          className="wknav__back"
          onClick={() => onGo(nav.list[nav.list.length - 1].id)}
        >
          Back to this week
        </button>
      )}

      <Sheet open={open} onClose={() => setOpen(false)} label="Choose a week">
        <div className="screen">
          <h3 className="h2">Jump to a week</h3>
        </div>
        <WeekList
          weeks={nav.list}
          season={season}
          viewId={viewing?.id}
          currentWeekNo={currentWeekNo}
          onGo={(id) => {
            onGo(id)
            setOpen(false)
          }}
        />
      </Sheet>
    </>
  )
}

/** "Sep 8 - Sep 14", or nothing when the week has no boundaries stored. */
function dateRange(w) {
  if (!w?.starts_at || !w?.ends_at) return ''
  const f = (iso) =>
    new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  return `${f(w.starts_at)} - ${f(w.ends_at)}`
}

function WeekList({ weeks, season, viewId, currentWeekNo, onGo }) {
  const winners = useMemo(() => winnersByWeek(season), [season])

  return (
    <div className="wklist">
      {weeks.map((w) => {
        const won = winners.get(w.week_no)
        const status = weekStatus(w)
        return (
          <button
            key={w.id}
            className={`wkrow${w.id === viewId ? ' is-on' : ''}${status ? ' is-quiet' : ''}`}
            onClick={() => onGo(w.id)}
          >
            <span className="wkrow__n">{w.label}</span>
            <span className="wkrow__v">
              {won ? (
                <>
                  {won.names.join(' & ')} <b className="num">{won.points}</b>
                </>
              ) : (
                status || (season === null ? '…' : 'no result')
              )}
            </span>
            {w.week_no === currentWeekNo && <span className="chip chip--accent">now</span>}
          </button>
        )
      })}
    </div>
  )
}
