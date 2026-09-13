import { useCallback, useEffect, useMemo, useState } from 'react'
import * as api from '../lib/api.js'
import { friendly } from '../lib/errors.js'
import { Avatar, Chevron, Empty, IconTrophy, Screen, Sheet, Spinner } from '../components/ui.jsx'
import { headToHead, stakes, weekRecap } from '../lib/weekRecap.js'
import { weekScore } from '../lib/weekScore.js'
import { weekNav, weekStatus, winnersByWeek } from '../lib/weekNav.js'
import { useTeams } from '../lib/teams.js'
import { schoolField, schoolPanel } from '../lib/schoolField.js'
import { onDark } from '../lib/onDark.js'
import Led from '../components/Led.jsx'
import Mark from '../components/Mark.jsx'

/**
 * The recap of a finished week. Never the week being played.
 *
 * Grant, 2026-09-12: "show nothing for week two and just have it be whatever the most
 * recent published week is. So always have it lag a week." The live week is the Board's.
 * This tab opens on the newest FINISHED week, and its arrows step between finished weeks
 * only; see recapWeeks in src/lib/weekNav.js for what finished means.
 *
 * The look is the one he picked the same night from two boards: option 2, "Winner's
 * colors", with that week's winner's school color carried down every section through
 * `onSkin`, so stepping from one week to another repaints it. Its top became the
 * jumbotron final on 2026-09-13 (see Hero). Under it, the sections he chose by number, in
 * his order: what decided it, upsets, how it unfolded, your week, when you all agreed,
 * went it alone, by the numbers.
 *
 * Nothing here characterises anybody. Every line is a count over the picks or a what-if
 * that weekRecap actually recomputed; see the note at the top of src/lib/weekRecap.js.
 */
export default function Week({ me, onSkin }) {
  const [slate, setSlate] = useState(null)
  const [rows, setRows] = useState(null)
  const [roster, setRoster] = useState(null)
  const [weeks, setWeeks] = useState(null)
  const [error, setError] = useState(null)
  const teams = useTeams()

  /* Which week this screen is looking at: null until the week list arrives, then the newest
     finished week. Local on purpose, so stepping back here never drags Picks or the Board
     with it, and it resets when the tab changes because App unmounts the screen. */
  const [viewId, setViewId] = useState(null)

  useEffect(() => {
    let alive = true
    api
      .listWeeks()
      .then((w) => {
        if (!alive) return
        setWeeks(w)
        const { latest } = weekNav(w, null)
        setViewId((prev) => prev ?? latest?.id ?? null)
      })
      .catch((e) => alive && setError(friendly(e)))
    return () => {
      alive = false
    }
  }, [])

  useEffect(() => {
    if (viewId == null) return undefined
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

  /* Only graded games, and only the picks on them. Every game is graded in all but one
     case: a week counted as finished because a later week has started, with a result that
     never came. The recap then covers the games that have one, rather than scoring a pick
     on an unplayed game as a miss. */
  const graded = useMemo(() => {
    if (!slate || !rows) return null
    const games = slate.filter((g) => g.winner_abbr)
    const ids = new Set(games.map((g) => g.game_id))
    return { games, rows: rows.filter((r) => ids.has(r.game_id)) }
  }, [slate, rows])

  const recap = useMemo(
    () => (graded && roster && graded.games.length ? weekRecap(graded.games, graded.rows, roster) : null),
    [graded, roster],
  )

  /* The same object the Board's scorebug reads, so the two screens can never disagree
     about who is where. */
  const score = useMemo(
    () => (graded && roster && graded.games.length ? weekScore(graded.games, graded.rows, roster) : null),
    [graded, roster],
  )

  /* That week's winner's colors, for the hero and for the header App draws. A shared week
     takes the first co-champion's school for the header; the hero splits between both. */
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
  if (!weeks) return <Spinner />

  const nav = weekNav(weeks, viewId)

  if (!nav.latest)
    return (
      <Screen eyebrow="Week" title="No finished weeks yet">
        <Empty icon={<IconTrophy />} title="The first recap is on its way">
          Each week lands here once its last game is final. Follow this week on the Board.
        </Empty>
      </Screen>
    )

  if (!recap || !recap.complete || !nav.current) return <Spinner />

  const byId = new Map(graded.games.map((g) => [g.game_id, g]))
  const teamOf = (id) => teams?.find((t) => t.id === id)

  return (
    <div className="wf">
      <Hero recap={recap} label={nav.current.label} finals={graded.games.length} slateSize={slate.length}
            teamOf={teamOf} pager={<Pager nav={nav} onGo={setViewId} />} />
      <FinalTable score={score} me={me} teamOf={teamOf} />
      <Decided recap={recap} byId={byId} rows={graded.rows} />
      <Upsets recap={recap} byId={byId} rows={graded.rows} />
      <Unfolded race={recap.race} players={recap.players} />
      <YourWeek recap={recap} games={graded.games} rows={graded.rows} me={me} byId={byId} />
      <Agreed list={recap.unanimous} byId={byId} />
      <Alone list={recap.alone} byId={byId} />
      <InNumbers recap={recap} />
    </div>
  )
}

const list = (xs) =>
  xs.length <= 1 ? xs[0] || '' : `${xs.slice(0, -1).join(', ')} and ${xs[xs.length - 1]}`

const ordinal = (n) => `${n}${{ 1: 'st', 2: 'nd', 3: 'rd' }[n] || 'th'}`

const sideOf = (g, abbr) => (g.home_abbr === abbr ? g.home_id : g.away_id)

/* ------------------------------------------------------------------ the hero */

/* LED lettering is condensed, so a name gets the biggest size its length allows. */
const ledNameSize = (chars) => (chars <= 6 ? 96 : chars <= 8 ? 72 : chars <= 11 ? 56 : 44)

/**
 * The top of a finished week: the jumbotron final.
 *
 * Direction 1 of four Grant was shown on 2026-09-13, with his one change: "take out the
 * over james by 7". The result is lit on the Board's LED wall, so the Board, Picks and
 * this top are one stadium, and the winner's panel is in their school's colors. A shared
 * week splits the panel between both schools and names both.
 */
function Hero({ recap, label, finals, slateSize, teamOf, pager }) {
  const leaders = recap.leaders
  const shared = leaders.length > 1
  const lead = leaders[0]
  const team = teamOf(lead.team_id)
  const panel = (p) => schoolPanel(teamOf(p.team_id), p.color)
  const names = shared ? leaders.map((p) => p.name).join(' & ') : lead.name
  const size = shared
    ? Math.min(64, ledNameSize(Math.max(...leaders.map((p) => p.name.length))))
    : ledNameSize(names.length)
  return (
    <section className="jb wf-top" aria-label={`${label} final`}>
      {pager}
      <div className="jb-wall wf-top__wall">
        <div className="jb-strip">
          <span>{label}</span>
          <span className="wf-top__final">Final</span>
          <span className="num">
            {finals}/{slateSize}
          </span>
        </div>
        <div
          className={`wf-top__panel${shared ? ' is-shared' : ''}`}
          style={{
            '--jb-team': panel(lead),
            '--wf-top-team2': shared ? panel(leaders[1]) : undefined,
            '--wf-top-name': `${size}px`,
          }}
        >
          {team && !shared && <Mark id={team.id} abbr={team.abbr} size={76} className="wf-top__mark" />}
          <span className="wf-top__lamp">{shared ? 'Co-winners' : 'Winner'}</span>
          <h2 className="wf-top__name">
            <Led>{names}</Led>
          </h2>
          <p className="wf-top__pts">
            <Led>{lead.points}</Led>
          </p>
        </div>
      </div>
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
 * The week pager, inside the hero: an arrow either side, and a label that opens a jump
 * list of every finished week.
 *
 * Option C from the board Grant chose on 2026-09-10, moved into the winner's color field
 * on 2026-09-12 and onto the jumbotron on 2026-09-13. The arrows only ever step between
 * finished weeks, so the week being played is never one tap away. An edge is a null in
 * `nav`, so a disabled arrow is a fact from weekNav rather than a condition restated here.
 *
 * There is no "Back to Week N" button under it any more. Grant had it taken out on
 * 2026-09-13: the right arrow and the jump list already get you there.
 */
function Pager({ nav, onGo }) {
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

  return (
    <>
      <div className="wknav wknav--hero">
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
            {viewing?.label}
            <Chevron dir="down" size={13} />
          </b>
        </button>

        <button
          className="wknav__arrow"
          onClick={() => nav.next && onGo(nav.next.id)}
          disabled={!nav.next}
          aria-label={nav.next ? `Go to ${nav.next.label}` : 'No later finished week'}
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
          onGo={(id) => {
            onGo(id)
            setOpen(false)
          }}
        />
      </Sheet>
    </>
  )
}

/** Finished weeks, newest first, each with who took it. */
function WeekList({ weeks, season, viewId, onGo }) {
  const winners = useMemo(() => winnersByWeek(season), [season])

  return (
    <div className="wklist">
      {[...weeks].reverse().map((w) => {
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
          </button>
        )
      })}
    </div>
  )
}
