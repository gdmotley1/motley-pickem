import { useCallback, useEffect, useMemo, useState } from 'react'
import * as api from '../lib/api.js'
import { friendly } from '../lib/errors.js'
import { Avatar, Chevron, Empty, IconTrophy, Screen, Sheet, Spinner } from '../components/ui.jsx'
import { withLive } from '../lib/espn.js'
import { useLiveScores } from '../lib/useLiveScores.js'
import { headToHead, stakes, weekRecap } from '../lib/weekRecap.js'
import { weekScore } from '../lib/weekScore.js'
import { WeekScore } from '../components/WeekScore.jsx'
import { isComplete, weekNav, weekStatus, winnersByWeek } from '../lib/weekNav.js'
import { useTeams } from '../lib/teams.js'
import { schoolField } from '../lib/schoolField.js'
import { onDark } from '../lib/onDark.js'

/**
 * One week: live while it is being played, a recap once it is over.
 *
 * WHILE GAMES ARE ON the tab carries the Board's scorebug, byte for byte, because Grant
 * asked on 2026-09-11 for one scoreboard in the app and not two.
 *
 * ONCE EVERY GAME IS FINAL it becomes the recap Grant picked on 2026-09-12 from two
 * boards: option 2, "Winner's colors", the FINAL graphic an athletic department posts,
 * painted in the winner's school colors (the header too, through `onSkin`). Under it, the
 * sections he chose by number, in his order: what decided it, upsets, how it unfolded,
 * your week, when you all agreed, went it alone, and by the numbers. He cut the ranking
 * bars and the ceiling stat that replaced them on the board, and two per-player ladders.
 *
 * Nothing here characterises anybody. Every line is a count over the picks or a what-if
 * that weekRecap actually recomputed; see the note at the top of src/lib/weekRecap.js.
 */
export default function Week({ me, weekId, week, onSkin }) {
  const [slate, setSlate] = useState(null)
  const [rows, setRows] = useState(null)
  const [roster, setRoster] = useState(null)
  const [weeks, setWeeks] = useState(null)
  const [error, setError] = useState(null)
  const teams = useTeams()

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
     about who is where. The finished week's table reads it too. */
  const score = useMemo(
    () => (games && rows && roster ? weekScore(games, rows, roster) : null),
    [games, rows, roster],
  )

  /* The winner's colors, for the hero and for the header App draws. A shared week takes
     the first co-champion's school for the header; the hero splits between both. */
  const colors = useMemo(() => {
    if (!recap?.complete || !recap.leaders.length) return null
    return recap.leaders.map((p) => schoolField(teams?.find((t) => t.id === p.team_id), p.color))
  }, [recap, teams])

  const skinKey = colors ? `${colors[0].field}${colors[0].ink}` : ''
  useEffect(() => {
    onSkin?.(colors ? colors[0] : null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [skinKey, onSkin])
  useEffect(() => () => onSkin?.(null), [onSkin])

  if (error) return <p className="err">{error}</p>

  const nav = weekNav(weeks, week?.week_no, viewId)
  const viewing = nav.current
  const label = viewing?.label || week?.label || 'This week'
  const pagerProps = { nav, onGo: setViewId, weeks, currentWeekNo: week?.week_no }

  if (!recap)
    return (
      <>
        <Pager {...pagerProps} />
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
          <Pager {...pagerProps} />
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
        <Pager {...pagerProps} />
        <Screen eyebrow={label} title="Nothing to show">
          <Empty icon={<IconTrophy />} title={emptyTitle(status)}>
            {emptyBody(status)}
          </Empty>
        </Screen>
      </>
    )
  }

  if (!recap.complete)
    return (
      <>
        <Pager {...pagerProps} />
        <Screen
          eyebrow="In progress"
          title={label}
          sub="Ties stand. The recap lands here once every game has finished."
        >
          <WeekScore score={score} me={me} label={label} record light />
        </Screen>
      </>
    )

  const byId = new Map(games.map((g) => [g.game_id, g]))
  const teamOf = (id) => teams?.find((t) => t.id === id)

  return (
    <div className="wf">
      <Hero recap={recap} label={label} colors={colors} teamOf={teamOf} pager={<Pager {...pagerProps} hero />} />
      <FinalTable score={score} me={me} teamOf={teamOf} />
      <Decided recap={recap} byId={byId} rows={rows} />
      <Upsets recap={recap} byId={byId} rows={rows} />
      <Unfolded race={recap.race} players={recap.players} />
      <YourWeek recap={recap} games={games} rows={rows} me={me} byId={byId} />
      <Agreed list={recap.unanimous} byId={byId} />
      <Alone list={recap.alone} byId={byId} />
      <InNumbers recap={recap} />
    </div>
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
  'Once games start going final, the table fills in here. The full recap lands when the last game of the week ends.'

const list = (xs) =>
  xs.length <= 1 ? xs[0] || '' : `${xs.slice(0, -1).join(', ')} and ${xs[xs.length - 1]}`

const ordinal = (n) => `${n}${{ 1: 'st', 2: 'nd', 3: 'rd' }[n] || 'th'}`

/**
 * A school's mark on the dark ground. Tries the drawing made for a dark background first,
 * which every FBS school has, then the plain one, then the abbreviation.
 */
function Mark({ id, abbr, size = 34 }) {
  const [step, setStep] = useState(0)
  const base = `${import.meta.env.BASE_URL}logos/`
  if (!id || step > 1) {
    return (
      <span className="wf-mark wf-mark--text" style={{ width: size, height: size }} aria-hidden="true">
        {(abbr || '?').slice(0, 4)}
      </span>
    )
  }
  return (
    <img
      className="wf-mark"
      src={`${base}${id}${step === 0 ? '-dark' : ''}.png`}
      width={size}
      height={size}
      alt=""
      loading="lazy"
      decoding="async"
      onError={() => setStep((s) => s + 1)}
    />
  )
}

const sideOf = (g, abbr) => (g.home_abbr === abbr ? g.home_id : g.away_id)

/* ------------------------------------------------------------------ the hero */

function nameSize(name) {
  const n = name.length
  return n <= 6 ? 118 : n <= 8 ? 90 : 68
}

function Hero({ recap, label, colors, teamOf, pager }) {
  const leaders = recap.leaders
  const shared = leaders.length > 1
  const first = colors[0]
  const runner = recap.players.find((p) => p.rank !== 1)
  const team = teamOf(leaders[0].team_id)
  const field = shared && colors[1]
    ? `linear-gradient(160deg, ${colors[0].field} 0 50%, ${colors[1].field} 50% 100%)`
    : first.field
  const names = shared ? leaders.map((p) => p.name).join(' & ') : leaders[0].name
  return (
    <section
      className={`wf-hero${shared ? ' is-shared' : ''}`}
      style={{
        '--wf-hero': field,
        '--wf-hero-ink': first.ink,
        '--wf-mark-invert': first.ink === '#ffffff' ? 1 : 0,
        '--wf-name': `${shared ? 60 : nameSize(names)}px`,
      }}
    >
      {team && !shared && (
        <i
          className="wf-hero__mark"
          style={{ backgroundImage: `url(${import.meta.env.BASE_URL}logos/${team.id}.png)` }}
          aria-hidden="true"
        />
      )}
      {pager}
      <p className="wf-kick">
        <span>{label}</span>
        <span className="wf-kick__final">Final</span>
      </p>
      <h2 className="wf-name">{names}</h2>
      <p className="wf-wins">{shared ? 'share the week' : 'wins the week'}</p>
      <p className="wf-score">
        <strong className="num">{leaders[0].points}</strong>
        <span>{shared ? `${leaders.length} tied at the top` : `by ${recap.margin} over ${runner?.name}`}</span>
      </p>
    </section>
  )
}

/** The final table, read from the same weekScore object the live scorebug draws. */
function FinalTable({ score, me, teamOf }) {
  return (
    <section className="wf-sec wf-sec--table" aria-label="Final standings">
      <div className="wf-table">
        {score.players.map((p) => (
          <div className={`wf-row${p.rank === 1 ? ' is-lead' : ''}`} key={p.id}>
            <span className="wf-rank num" style={{ background: teamOf(p.team_id)?.alt || p.color }}>
              {p.rank}
            </span>
            <Avatar name={p.name} color={p.color} teamId={p.team_id} size={34} />
            <span className="wf-who">
              <b>{p.name}</b>
              <span className="num">
                {p.correct}-{p.played - p.correct}
                {p.id === me?.id ? ' · you' : ''}
              </span>
            </span>
            <strong className="num">{p.points}</strong>
          </div>
        ))}
      </div>
    </section>
  )
}

function Title({ children, help }) {
  return (
    <>
      <h3 className="wf-title">{children}</h3>
      {help && <p className="wf-help">{help}</p>}
    </>
  )
}

/** Everyone's wager on one game, grouped by the side they took, the side that won first. */
function Stakes({ game, rows, only }) {
  const all = stakes(game, rows).filter((s) => !only || only(s))
  const sides = [...new Set(all.map((s) => s.pick))].sort(
    (a, b) => Number(b === game.winner_abbr) - Number(a === game.winner_abbr),
  )
  return sides.map((pick) => (
    <div className="wf-stake" key={pick}>
      <span>Had {pick}</span>
      {all
        .filter((s) => s.pick === pick)
        .map((s) => {
          const seat = rows.find((r) => r.player_id === s.player_id)
          return (
            <span className={`wf-chip${s.won ? '' : ' is-lost'}`} key={s.player_id}>
              <Avatar name={s.name} color={seat?.player_color} teamId={seat?.player_team} size={24} />
              <b className="num">{s.confidence}</b>
            </span>
          )
        })}
    </div>
  ))
}

function Plate({ game }) {
  const half = (side) => {
    const abbr = game[`${side}_abbr`]
    return (
      <span className={`wf-half${abbr === game.winner_abbr ? '' : ' is-loser'}`}>
        <Mark id={game[`${side}_id`]} abbr={abbr} size={40} />
        <b>{abbr}</b>
        <strong className="num">{game[`${side}_score`] ?? ''}</strong>
      </span>
    )
  }
  return (
    <div className="wf-plate">
      {half('away')}
      <span className="wf-plate__final">Final</span>
      {half('home')}
    </div>
  )
}

/* ---------------------------------------------------------------- the sections */

/**
 * The results the week actually turned on. Each was found by flipping that one result
 * and re-running the standings, so a game is here because the winner genuinely changes.
 * An empty list is a real answer and gets said out loud.
 */
function Decided({ recap, byId, rows }) {
  const { decisive } = recap
  return (
    <section className="wf-sec">
      <Title>Decided it</Title>
      {decisive.length === 0 && (
        <p className="wf-none">
          Nothing did on its own. Flip any one result and the same {recap.shared ? 'people share' : 'person wins'} the
          week.
        </p>
      )}
      {decisive.map((d) => {
        const g = byId.get(d.game_id)
        return (
          <article className="wf-game" key={d.game_id}>
            <Plate game={g} />
            <p className="wf-if">If {d.instead} wins</p>
            <p className="wf-then">
              {d.shared
                ? `${list(d.leaders)} tie on ${d.points}`
                : d.next
                  ? `${d.leaders[0]} takes it, ${d.points}–${d.next.points}`
                  : `${d.leaders[0]} takes it on ${d.points}`}
            </p>
            <Stakes game={g} rows={rows} />
          </article>
        )
      })}
    </section>
  )
}

function Upsets({ recap, byId, rows }) {
  if (!recap.upsets.length) return null
  return (
    <section className="wf-sec">
      <Title>Upsets</Title>
      {recap.upsets.map((u) => {
        const g = byId.get(u.game_id)
        const winnerSide = g.home_abbr === u.winner ? 'home' : 'away'
        const loserSide = winnerSide === 'home' ? 'away' : 'home'
        return (
          <article className="wf-upset" key={u.game_id}>
            <Mark id={g[`${winnerSide}_id`]} abbr={u.winner} size={54} />
            <div>
              <p className="wf-upset__hd">
                <b>{u.winner}</b>
                {u.line != null && <span className="wf-line num">+{u.line}</span>}
              </p>
              <p className="wf-upset__sub num">
                beat {g[`${loserSide}_abbr`]} {g[`${winnerSide}_score`]}–{g[`${loserSide}_score`]}
              </p>
              {u.calledBy.length ? (
                <Stakes game={g} rows={rows} only={(s) => s.won} />
              ) : (
                <p className="wf-none">Nobody had {u.winner}</p>
              )}
            </div>
          </article>
        )
      })}
    </section>
  )
}

/**
 * Where everyone stood after each game, in kickoff order: a line per player that steps
 * between 1st and 4th, so every lead change is a crossing. The chart was first drawn as
 * running points and read as four lines stacked on top of each other, because a week is
 * won inside a few points and the scale runs to 200.
 */
function Unfolded({ race, players }) {
  if (!race || race.steps.length < 2) return null
  const { steps } = race
  const W = 366
  const H = 206
  const L = 40
  const R = 92
  const T = 16
  const B = 30
  const rowH = (H - T - B) / Math.max(1, players.length - 1)
  const x = (i) => L + ((W - L - R) * i) / (steps.length - 1)
  const finals = [...players].sort((a, b) => a.rank - b.rank || b.correct - a.correct)
  const order = new Map(finals.map((p, i) => [p.id, i]))
  const y = (s, id) => {
    const tied = finals.filter((p) => s.points[p.id] === s.points[id]).map((p) => p.id)
    const nudge = (tied.indexOf(id) - (tied.length - 1) / 2) * 5
    return T + (s.rank[id] - 1) * rowH + nudge
  }
  const leaders = new Set(steps[steps.length - 1].leaders)
  const nameOf = new Map(players.map((p) => [p.id, p.name]))
  const locked = race.lockedAt ? steps[race.lockedAt - 1] : null
  return (
    <section className="wf-sec">
      <Title help="Where everyone stood after each game, in kickoff order.">How it unfolded</Title>
      <svg className="wf-race" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Standings position after each game">
        <g className="wf-race__grid">
          {finals.map((p, i) => (
            <g key={p.id}>
              <line x1={L} x2={W - R} y1={T + i * rowH} y2={T + i * rowH} />
              <text x={L - 8} y={T + i * rowH + 5}>{ordinal(i + 1)}</text>
            </g>
          ))}
        </g>
        {race.lockedAt && (
          <line className="wf-race__lock" x1={x(race.lockedAt - 1)} x2={x(race.lockedAt - 1)} y1={T - 10} y2={H - B + 8} />
        )}
        <g fill="none" strokeLinejoin="round" strokeLinecap="round">
          {[...finals].reverse().map((p) => {
            const c = onDark(p.color, '#131214')
            const pts = steps.map((s, i) => [x(i), y(s, p.id)])
            const last = pts[pts.length - 1]
            const big = leaders.has(p.id)
            return (
              <g key={p.id}>
                <polyline points={pts.map((q) => q.join(',')).join(' ')} stroke={c} strokeWidth={big ? 4.5 : 2.6} />
                <circle cx={last[0]} cy={last[1]} r={big ? 6 : 4} fill={c} />
                <text className="wf-race__end" x={W - R + 12} y={T + order.get(p.id) * rowH + 5} fill={c}>
                  {p.name} {p.points}
                </text>
              </g>
            )
          })}
        </g>
        <text className="wf-race__x" x={L - 4} y={H - 6}>Game 1</text>
        <text className="wf-race__x" x={W - R + 4} y={H - 6} textAnchor="end">{steps.length}</text>
      </svg>
      <div className="wf-facts">
        <p>
          <strong className="num">{race.changes}</strong>
          <span>{race.changes === 1 ? 'time the lead changed hands' : 'times the lead changed hands'}</span>
        </p>
        {locked && (
          <p>
            <strong className="num">{race.lockedAt}</strong>
            <span>
              {nameOf.get(steps[steps.length - 1].leaders[0])} took the lead for good, at {locked.label}
            </span>
          </p>
        )}
        {race.ledMost.games > 0 && (
          <p>
            <strong className="num">{race.ledMost.games}</strong>
            <span>
              games {list(race.ledMost.ids.map((id) => nameOf.get(id)))} led, the most of anyone
            </span>
          </p>
        )}
      </div>
    </section>
  )
}

/** Just yours: where you gained and gave back against whoever finished next to you. */
function YourWeek({ recap, games, rows, me, byId }) {
  const p = recap.players.find((x) => x.id === me?.id)
  const h = p ? headToHead(games, rows, recap.players, p.id) : null
  if (!p || !h) return null
  const rival = h.rival.name
  const item = (d) => {
    const g = byId.get(d.game_id)
    const mine = d.mine?.won ? `your ${d.mine.confidence}` : 'you missed'
    const theirs = d.theirs?.won ? `${rival} ${d.theirs.confidence}` : `${rival} missed`
    const pick = d.net > 0 ? d.mine.pick : d.theirs.pick
    return (
      <div className="wf-h2h" key={d.game_id}>
        <Mark id={sideOf(g, pick)} abbr={pick} size={30} />
        <span className="wf-who">
          <b>{d.label}</b>
          <span className="num">{mine}, {theirs}</span>
        </span>
        <strong className="num">+{Math.abs(d.net)}</strong>
      </div>
    )
  }
  const standing =
    h.gap > 0 ? `${h.gap} ahead of ${rival}` : h.gap < 0 ? `${-h.gap} behind ${rival}` : `level with ${rival}`
  return (
    <section className="wf-sec">
      <Title help={`It compares you with ${rival}, who finished next to you.`}>Your week</Title>
      <div className="wf-you">
        <Avatar name={p.name} color={p.color} teamId={p.team_id} size={56} />
        <div>
          <p className="wf-you__k">You finished</p>
          <p className="wf-you__v">
            {ordinal(p.rank)} of {recap.players.length}
          </p>
          <p className="wf-you__s num">
            {p.correct}-{p.wrong} · {p.points} points · {standing}
          </p>
        </div>
      </div>
      {h.gained.length > 0 && <p className="wf-sub">Where you gained on {rival}</p>}
      {h.gained.slice(0, 2).map(item)}
      {h.lost.length > 0 && <p className="wf-sub">Where {rival} gained on you</p>}
      {h.lost.slice(0, 2).map(item)}
    </section>
  )
}

function Agreed({ list: agreed, byId }) {
  if (!agreed.length) return null
  const held = agreed.filter((a) => a.won)
  const burned = agreed.filter((a) => !a.won)
  return (
    <section className="wf-sec">
      <Title>When you all agreed</Title>
      <div className="wf-facts">
        <p>
          <strong className="num">{agreed.length}</strong>
          <span>{agreed.length === 1 ? 'game all four of you picked the same team' : 'games all four of you picked the same team'}</span>
        </p>
      </div>
      {held.length > 0 && (
        <>
          <p className="wf-sub">{held.length} held</p>
          <div className="wf-held">
            {held.map((a) => (
              <span className="wf-held__i" key={a.game_id}>
                <Mark id={sideOf(byId.get(a.game_id), a.pick)} abbr={a.pick} size={28} />
                <b>{a.pick}</b>
              </span>
            ))}
          </div>
        </>
      )}
      {burned.length > 0 && <p className="wf-sub">{burned.length} didn&rsquo;t</p>}
      {burned.map((a) => (
        <div className="wf-h2h wf-h2h--two" key={a.game_id}>
          <Mark id={sideOf(byId.get(a.game_id), a.pick)} abbr={a.pick} size={34} />
          <span className="wf-who">
            <b>{a.pick} lost</b>
            <span className="num">{a.total} points between you, all gone</span>
          </span>
        </div>
      ))}
    </section>
  )
}

function Alone({ list: players, byId }) {
  if (!players.some((p) => p.picks.length)) return null
  const sorted = [...players].sort((a, b) => b.picks.length - a.picks.length || b.right - a.right)
  return (
    <section className="wf-sec">
      <Title help="Picks nobody else in the family made, and how they went.">Went it alone</Title>
      {sorted.map((p) => (
        <div className="wf-alone" key={p.id}>
          <div className="wf-alone__hd">
            <Avatar name={p.name} color={p.color} teamId={p.team_id} size={34} />
            <span className="wf-who">
              <b>{p.name}</b>
              <span>{p.picks.length ? `${p.right} right` : 'Went with somebody every time'}</span>
            </span>
            <strong className="num">{p.picks.length}</strong>
          </div>
          {p.picks.length > 0 && (
            <div className="wf-picks">
              {p.picks.map((x) => (
                <span className={`wf-pick${x.won ? '' : ' is-lost'}`} key={x.game_id}>
                  <Mark id={sideOf(byId.get(x.game_id), x.pick)} abbr={x.pick} size={22} />
                  <b>{x.pick}</b>
                  <em className="num">{x.confidence}</em>
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </section>
  )
}

function InNumbers({ recap }) {
  const called = recap.upsets.filter((u) => u.calledBy.length)
  const callers = [...new Set(called.flatMap((u) => u.calledBy))]
  const rows = [
    [recap.chalk.won, 'Favorites won', `of ${recap.chalk.of} games with a line`],
    [
      recap.upsets.length,
      recap.upsets.length === 1 ? 'Upset' : 'Upsets',
      called.length ? `${list(callers)} called ${list(called.map((u) => u.winner))}` : 'Nobody called one',
    ],
    [recap.sweeps, 'All four got it right', recap.sweepGames.map((g) => g.winner).join(', ') || 'None this week'],
    [recap.whiffs.length, 'Nobody got it right', recap.whiffs.map((w) => w.winner).join(', ') || 'None this week'],
  ]
  return (
    <section className="wf-sec">
      <Title>By the numbers</Title>
      {rows.map(([v, k, s]) => (
        <div className="wf-nrow" key={k}>
          <strong className="num">{v}</strong>
          <span className="wf-who">
            <b>{k}</b>
            <span>{s}</span>
          </span>
        </div>
      ))}
    </section>
  )
}

/**
 * The week pager: an arrow either side, and a label that opens a jump list.
 *
 * Option C from the board Grant chose on 2026-09-10. The arrows are the common case,
 * one step back; the sheet is what stops week 3 being eleven taps away in November.
 * `hero` draws it inside the finished week's colour field instead of on its own bar.
 *
 * An edge is a null in `nav`, so a disabled arrow is a fact from weekNav rather than a
 * condition restated here.
 */
function Pager({ nav, onGo, weeks, currentWeekNo, hero = false }) {
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
      <div className={`wknav${hero ? ' wknav--hero' : ''}`}>
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
          {!hero && <i>{sub}</i>}
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
          className={`wknav__back${hero ? ' wknav__back--hero' : ''}`}
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
