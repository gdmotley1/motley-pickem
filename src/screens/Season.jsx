import { useEffect, useMemo, useState } from 'react'
import * as api from '../lib/api.js'
import { friendly } from '../lib/errors.js'
import { Avatar, Empty, IconTrophy, Screen, Spinner } from '../components/ui.jsx'
import { formGeometry, seasonStats } from '../lib/seasonStats.js'
import { onDark } from '../lib/onDark.js'
import { GROUPS, seasonRecords } from '../lib/seasonRecords.js'
import TeamLogo from '../components/TeamLogo.jsx'

/**
 * The whole year: totals, who took each week, form, and the records so far.
 *
 * Split out of Standings when the week moved to its own screen. Cumulative numbers only
 * live here now, which is what stops the two tabs from being three copies of one table.
 *
 * Thin early and honest about it. After one week the totals are the week, the form chart
 * has nothing to draw, and saying so is better than drawing a chart of one point.
 */
export default function Season() {
  const [rows, setRows] = useState(null)
  const [roster, setRoster] = useState(null)
  const [picks, setPicks] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let alive = true
    /* The picks fetch fails SOFT, and this is not defensive habit, it is a real state
       the family will be in. get_season_picks arrives in migration 015, which is a paste
       into a web console, so between a deploy and that paste the function does not exist.
       Inside the Promise.all it took the whole tab down with it: standings, form, weeks
       and ranking all replaced by an error, because a record book nobody has yet is
       apparently worth losing the leaderboard over.
       The book is additive. It may never be a reason the rest of the screen is missing. */
    Promise.all([
      api.getSeason(),
      api.listSeats(),
      api.getSeasonPicks().catch(() => null),
    ])
      .then(([s, seats, pk]) => {
        if (!alive) return
        setRows(s)
        setRoster(seats.filter((x) => x.claimed))
        setPicks(pk)
      })
      .catch((e) => alive && setError(friendly(e)))
    return () => {
      alive = false
    }
  }, [])

  const stats = useMemo(
    () => (rows && roster ? seasonStats(rows, roster) : null),
    [rows, roster],
  )

  /* The record book is the whole reason 015 exists. It is derived from the picks, not
     from the aggregates above, so it is computed separately and joined only on screen. */
  const book = useMemo(
    () => (picks && roster ? seasonRecords(picks, roster) : null),
    [picks, roster],
  )

  if (error) return <p className="err">{error}</p>
  if (!stats) return <Spinner />

  if (!stats.players.length)
    return (
      <Screen eyebrow="Season 2026" title="Season">
        <Empty icon={<IconTrophy />} title="No weeks finished yet">
          Totals, weeks won and form all fill in here as the season goes. Come back once
          the first week has been graded.
        </Empty>
      </Screen>
    )

  return (
    <Screen
      eyebrow="Season 2026"
      title="Season"
      sub={`${stats.played} ${stats.played === 1 ? 'week' : 'weeks'} in the books. Ties stand, so a week can be shared.`}
    >
      <div className="stand">
        {stats.players.map((p) => (
          <div key={p.id} className={`srow${p.rank === 1 ? ' is-leader' : ''}`}>
            <span className="srow__pos num">{p.rank}</span>
            <Avatar name={p.name} color={p.color} teamId={p.team_id} size={36} />
            <span className="srow__body">
              <span className="srow__name">{p.name}</span>
              <span className="srow__meta num">
                {p.correct}-{p.wrong} · {p.accuracy}%
                {p.weeksWon > 0 &&
                  ` · ${p.weeksWon} ${p.weeksWon === 1 ? 'week' : 'weeks'} won`}
              </span>
            </span>
            <span>
              <span className="srow__pts num">{p.points}</span>
              <span className="srow__ptslabel">pts</span>
            </span>
          </div>
        ))}
      </div>

      <Form form={stats.form} played={stats.played} />
      <Weeks weeks={stats.weeks} />
      <Ranking players={stats.players} />
      <Book book={book} />
    </Screen>
  )
}

const list = (xs) =>
  xs.length <= 1 ? xs[0] || '' : `${xs.slice(0, -1).join(', ')} and ${xs[xs.length - 1]}`

/**
 * Points per week, one line per player.
 *
 * Drawn to a single scale that starts at zero and ends on a round number above the best
 * week, so every gridline is a value the chart actually reaches. Below two graded weeks
 * there is no shape to show, and a chart of one point is worse than a sentence.
 */
function Form({ form, played }) {
  if (played < 2)
    return (
      <>
        <div className="screen">
          <h3 className="h2">Form</h3>
          <p className="sub">
            A line per player once there are two weeks to compare. Nothing to plot yet.
          </p>
        </div>
      </>
    )

  const g = formGeometry(form)

  return (
    <>
      <div className="screen">
        <h3 className="h2">Form</h3>
        <p className="sub">Points scored each week.</p>
      </div>
      <div className="chartwrap">
        <svg className="chart" viewBox={`0 0 ${g.W} ${g.H}`} role="img"
             aria-label="Points scored by each player, week by week">
          {g.ticks.map((t) => (
            <g key={t.value}>
              <line x1={26} y1={t.y} x2={g.W - 2} y2={t.y} className="chart__grid" />
              <text x={21} y={t.y + 3} className="chart__tick" textAnchor="end">
                {t.value}
              </text>
            </g>
          ))}
          {g.columns.map((c) => (
            <text key={c.week_no} x={c.x} y={g.H - 5} className="chart__tick"
                  textAnchor="middle">
              {c.week_no}
            </text>
          ))}
          {g.series.map((s) => {
            /* The chart sits in a felt well now. Every seat colour was picked against
               Slate's white card and three of the four fail the 3:1 graphics floor down
               here; James, dark green on dark green, all but vanishes. onDark raises
               lightness only, so the line is still recognisably his. */
            const c = onDark(s.color)
            return s.points.length ? (
              <g key={s.id}>
                <polyline points={s.points.map((p) => `${p.x},${p.y}`).join(' ')}
                          fill="none" stroke={c} strokeWidth="2"
                          strokeLinejoin="round" strokeLinecap="round" />
                {s.points.map((p) => (
                  <circle key={p.x} cx={p.x} cy={p.y} r="2.6" fill={c} />
                ))}
              </g>
            ) : null
          })}
        </svg>
      </div>
      <div className="legend">
        {form.series.map((s) => (
          <span className="legend__i" key={s.id}>
            <span className="legend__dot" style={{ background: onDark(s.color) }} />
            {s.name}
          </span>
        ))}
      </div>
    </>
  )
}

function Weeks({ weeks }) {
  const graded = weeks.filter((w) => w.graded)
  if (!graded.length) return null
  return (
    <>
      <div className="screen">
        <h3 className="h2">Week by week</h3>
        <p className="sub">Who took each week, and on what.</p>
      </div>
      <div className="wks">
        {graded.map((w) => (
          <div className="wk" key={w.week_no}>
            <span className="wk__n">{w.label}</span>
            <span className="wk__w">
              {list(w.winners.map((x) => x.name))}
              {w.shared && <span className="chip chip--accent">shared</span>}
            </span>
            <span className="wk__p num">{w.best}</span>
          </div>
        ))}
      </div>
    </>
  )
}

function Ranking({ players }) {
  const sorted = [...players].sort((a, b) => b.captured - a.captured)
  return (
    <>
      <div className="screen">
        <h3 className="h2">Ranking over the season</h3>
        <p className="sub">
          Points banked against the sum of every week&apos;s ceiling. Who is best at
          ordering their confidence, separately from who is best at picking.
        </p>
      </div>
      <div className="bars">
        {sorted.map((p) => (
          <div className="bar" key={p.id}>
            <span className="bar__name">{p.name}</span>
            <span className="bar__track">
              {/* The track is --well, which in book mode is the deepest wood in the
                  palette. Same lift as the chart, against that ground rather than felt. */}
              <span className="bar__fill"
                    style={{ width: `${p.captured}%`, background: onDark(p.color, '#241409') }} />
            </span>
            <span className="bar__val num">{p.captured}%</span>
          </div>
        ))}
      </div>
    </>
  )
}

/**
 * The record book.
 *
 * Every record draws the same way: a brass plate carrying the holder, the number and the
 * moment, then the other three underneath. Grant asked for the chasing pack on 2026-09-11
 * so that everyone sees where THEY are on every record; a plate that only named a winner
 * would tell three of the four people nothing.
 *
 * The groups are mapped from GROUPS rather than written out, so adding a record in
 * seasonRecords.js is the only edit a new record needs.
 */
function Book({ book }) {
  if (!book || !book.records.length) return null
  return (
    <>
      {GROUPS.map(([group, heading]) => {
        const inGroup = book.records.filter((r) => r.group === group)
        if (!inGroup.length) return null
        return (
          <div key={group}>
            <div className="screen">
              <h3 className="h2">{heading}</h3>
            </div>
            <div className="recs">
              {inGroup.map((r) => (
                <Plate key={r.key} r={r} />
              ))}
            </div>
          </div>
        )
      })}
      <Family family={book.family} />
    </>
  )
}

/**
 * One record, as a square.
 *
 * Label, number, who. That is the whole tile.
 *
 * It carried the other three players underneath for about an hour on 2026-09-11, which
 * Grant had asked for and then reversed on sight: "make the record simple, easy to
 * understand. We don't need to see everyone's scores. They should just be basic and
 * little squares, not long old cards." He is right. Seventeen records times four names
 * is sixty-eight numbers, and a record book you have to read is not a record book.
 *
 * seasonRecords still ranks all four, because `holders` and the tie logic need the full
 * standing to know who actually holds a record. Only the rendering dropped.
 */
/**
 * Who holds it, in the width a square has.
 *
 * Measured at 390px: the name line gets 136px next to a team mark, and
 * "Grant, James, Parker and Nicole" wants 168. A tie nobody has broken is also the one
 * case where the names carry no information, since it is everybody, so it collapses.
 */
function holderLine(r) {
  if (!r.holders.length) return '—'
  // Spelled out: "all four" is how anyone says it, and this is a family app.
  if (r.holders.length >= r.rows.length) {
    return `all ${{ 2: 'two', 3: 'three', 4: 'four' }[r.rows.length] || r.rows.length}`
  }
  return list(r.holders)
}

function Plate({ r }) {
  const [held] = r.rows
  return (
    <div className="rec">
      <p className="rec__k">{r.label}</p>
      <p className="rec__v num">{held.display}</p>
      <p className="rec__who">
        {held.teamId && <TeamLogo teamId={held.teamId} size={16} />}
        <span className="rec__wn">{holderLine(r)}</span>
      </p>
    </div>
  )
}

/**
 * The four of you, rather than any one of you.
 *
 * Head to head is the only thing on the tab that is a grid, and it is the one people will
 * actually argue about. Ties count for neither side, because ties stand.
 */
function Family({ family }) {
  if (!family) return null
  return (
    <>
      <div className="screen">
        <h3 className="h2">All four of you</h3>
      </div>
      <div className="fam">
        {family.trap && (
          <div className="fam__trap">
            <p className="fam__k">Trap game</p>
            <p className="fam__v">{family.trap.label}</p>
            <p className="fam__s">
              {family.trap.week} &middot; got {family.trap.missed} of you for{' '}
              {family.trap.cost} points &middot; {family.trap.winner} won
            </p>
          </div>
        )}
        <div className="fam__pair">
          <div className="fam__stat">
            <p className="fam__n num">{family.unanimousRight}</p>
            <p className="fam__l">called by all of you</p>
          </div>
          <div className="fam__stat">
            <p className="fam__n num">{family.unanimousWrong}</p>
            <p className="fam__l">missed by all of you</p>
          </div>
        </div>
        <div className="h2h">
          <p className="fam__k">Head to head, by week</p>
          {family.grid.map((a) => (
            <div className="h2h__row" key={a.id}>
              <span className="h2h__me">{a.name}</span>
              {a.vs.map((v) => (
                <span className="h2h__v" key={v.id}>
                  <span className="h2h__vn">{v.name}</span>
                  <b className="num">
                    {v.w}-{v.l}
                  </b>
                </span>
              ))}
            </div>
          ))}
        </div>
      </div>
    </>
  )
}
