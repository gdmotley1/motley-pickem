import { useEffect, useMemo, useState } from 'react'
import * as api from '../lib/api.js'
import { friendly } from '../lib/errors.js'
import { Avatar, Empty, IconTrophy, Screen, Spinner } from '../components/ui.jsx'
import { formGeometry, seasonStats } from '../lib/seasonStats.js'
import { onDark } from '../lib/onDark.js'
import { GROUPS, seasonRecords } from '../lib/seasonRecords.js'

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
  /* Eight of the twelve records come from the same rows the standings do, so the book
     needs `picks` only for the last four and renders without them. That is what keeps it
     from being empty before migration 015 is pasted. */
  const book = useMemo(
    () => (rows && roster ? seasonRecords(rows, picks, roster) : null),
    [rows, picks, roster],
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
 * Twelve squares in three groups. A square is the label, the number, and who holds it.
 * Nothing else, because the version before this had seventeen invented statistics and
 * Grant's verdict was "literally none of these stats makes sense at all".
 *
 * Groups are mapped from GROUPS rather than written out, and a group with nothing in it
 * draws nothing: before migration 015 the last four records do not exist and "Single
 * games" must not appear as an empty heading.
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
    </>
  )
}

/** Who holds it, in the width a square has. */
function holderLine(r) {
  /* Nobody has set it. "0, all four" reads as a statistic and is really an absence. */
  if (r.unclaimed) return 'not yet'
  // Spelled out: "all four" is how anyone says it, and this is a family app.
  if (r.holders.length >= r.rows.length) {
    return `all ${{ 2: 'two', 3: 'three', 4: 'four' }[r.rows.length] || r.rows.length}`
  }
  return list(r.holders)
}

/** One record: label, number, who. */
function Plate({ r }) {
  const [held] = r.rows
  return (
    <div className={`rec${r.unclaimed ? ' is-open' : ''}`}>
      <p className="rec__k">{r.label}</p>
      <p className="rec__v num">{r.unclaimed ? '—' : held.display}</p>
      <p className="rec__who">
        <span className="rec__wn">{holderLine(r)}</span>
      </p>
    </div>
  )
}
