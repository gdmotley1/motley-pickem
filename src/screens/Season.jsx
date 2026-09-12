import { useEffect, useMemo, useState } from 'react'
import * as api from '../lib/api.js'
import { friendly } from '../lib/errors.js'
import { Avatar, Empty, IconTrophy, Screen, Spinner } from '../components/ui.jsx'
import { formGeometry, seasonStats } from '../lib/seasonStats.js'
import { onDark } from '../lib/onDark.js'
import { GROUPS, seasonRecords } from '../lib/seasonRecords.js'
import { ICONS, ICON_CREDIT, TIER } from '../lib/badgeIcons.js'

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
            {/* Rank, name, points. The record and the weeks won used to sit here too
                and are now the "Best overall record" and "Most weeks won" badges, so the
                same number is not printed twice on one screen. */}
            <span className="srow__body">
              <span className="srow__name">{p.name}</span>
            </span>
            <span>
              <span className="srow__pts num">{p.points}</span>
              <span className="srow__ptslabel">pts</span>
            </span>
          </div>
        ))}
      </div>

      <Form form={stats.form} played={stats.played} />
      <Book book={book} />

      {/* CC BY 3.0 requires this. It is a condition of using the artwork, not a
          courtesy, and tests/test_records.py fails if it disappears. */}
      {book?.records.length > 0 && <p className="credit">{ICON_CREDIT}</p>}
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

/**
 * One record, as an enamel pin.
 *
 * A hard enamel pin is three things and nothing else: a die-struck metal rim, flat enamel
 * poured inside it, and one hard crescent where the light catches the polish. The enamel
 * has no gradient of its own; all of it lives in the rim, which is a conic gradient rather
 * than a linear one because that is the difference between metal that looks painted and
 * metal that looks turned.
 *
 * The glyph is not ours. See src/lib/badgeIcons.js: three passes of hand-drawn SVG were
 * rejected, and these are by four illustrators off game-icons.net under CC BY 3.0.
 * dangerouslySetInnerHTML is safe here because the strings are build-time constants from
 * a vendored file, never anything a player can reach.
 *
 * Plating is the difficulty tier. An unclaimed record is not a dim pin, it is the empty
 * socket the pin would go in, so you can see what is missing.
 */
function Plate({ r }) {
  const [held] = r.rows
  const tier = TIER[r.key] || 1
  return (
    <div className={`pin pin--t${tier}${r.unclaimed ? ' is-open' : ''}`}>
      <span className="pin__disc">
        <span className="pin__field">
          <svg className="pin__ico" viewBox="0 0 512 512" aria-hidden="true"
               dangerouslySetInnerHTML={{ __html: ICONS[r.key] || '' }} />
        </span>
      </span>
      <p className="pin__k">{r.label}</p>
      <p className="pin__v num">{r.unclaimed ? '—' : held.display}</p>
      <p className="pin__who">{holderLine(r)}</p>
    </div>
  )
}
