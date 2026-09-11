import { useEffect, useMemo, useState } from 'react'
import * as api from '../lib/api.js'
import { friendly } from '../lib/errors.js'
import { Avatar, Empty, IconTrophy, Screen, Spinner } from '../components/ui.jsx'
import { formGeometry, seasonStats } from '../lib/seasonStats.js'

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
  const [error, setError] = useState(null)

  useEffect(() => {
    let alive = true
    Promise.all([api.getSeason(), api.listSeats()])
      .then(([s, seats]) => {
        if (!alive) return
        setRows(s)
        setRoster(seats.filter((x) => x.claimed))
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
      <Records records={stats.records} />
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
          {g.series.map((s) =>
            s.points.length ? (
              <g key={s.id}>
                <polyline points={s.points.map((p) => `${p.x},${p.y}`).join(' ')}
                          fill="none" stroke={s.color} strokeWidth="2"
                          strokeLinejoin="round" strokeLinecap="round" />
                {s.points.map((p) => (
                  <circle key={p.x} cx={p.x} cy={p.y} r="2.6" fill={s.color} />
                ))}
              </g>
            ) : null,
          )}
        </svg>
      </div>
      <div className="legend">
        {form.series.map((s) => (
          <span className="legend__i" key={s.id}>
            <span className="legend__dot" style={{ background: s.color }} />
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
              <span className="bar__fill"
                    style={{ width: `${p.captured}%`, background: p.color }} />
            </span>
            <span className="bar__val num">{p.captured}%</span>
          </div>
        ))}
      </div>
    </>
  )
}

function Records({ records }) {
  if (!records.length) return null
  return (
    <>
      <div className="screen">
        <h3 className="h2">Records</h3>
      </div>
      <div className="tiles">
        {records.map((r) => (
          <div className="tile" key={r.key}>
            <p className="tile__k">{r.label}</p>
            <p className="tile__v num">
              {r.value}
              <span>{r.unit}</span>
            </p>
            <p className="tile__s">{r.who}</p>
          </div>
        ))}
      </div>
    </>
  )
}
