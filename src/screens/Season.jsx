import { useEffect, useMemo, useState } from 'react'
import * as api from '../lib/api.js'
import { friendly } from '../lib/errors.js'
import { Avatar, Empty, IconTrophy, Screen, Spinner } from '../components/ui.jsx'
import { formGeometry, seasonStats } from '../lib/seasonStats.js'
import { onDark } from '../lib/onDark.js'
import { seasonRecords } from '../lib/seasonRecords.js'
import { badgeUrl } from '../lib/badges.js'

/**
 * The whole year: the standings, form once there is any, and the record book.
 *
 * Top to bottom, as Grant picked it by number on 2026-09-12: standings, the form chart
 * (only once two weeks are finished), the Hall of fame as the trophy room (7), the Hall of
 * shame as the red panel (10), and everyone's numbers as headlines (6).
 */
export default function Season() {
  const [rows, setRows] = useState(null)
  const [roster, setRoster] = useState(null)
  const [picks, setPicks] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let alive = true
    /* The picks fetch fails SOFT. The record book is additive: if get_season_picks
       errors, the standings, the form and every record built from get_season must still
       render. It once took the whole tab down from inside the Promise.all. */
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

  const book = useMemo(
    () => (rows && roster ? seasonRecords(rows, picks, roster) : null),
    [rows, picks, roster],
  )

  if (error) return <p className="err">{error}</p>
  if (!stats) return <Spinner />

  if (!stats.players.length)
    return (
      <Screen eyebrow="Season 2026" title="Season">
        <Empty icon={<IconTrophy />} title="Nothing graded yet">
          Standings, form and the record book all fill in here as the season goes. Come
          back once the first game has a result.
        </Empty>
      </Screen>
    )

  const sub = stats.played
    ? `${stats.played} ${stats.played === 1 ? 'week' : 'weeks'} in the books. Ties stand, so a week can be shared.`
    : 'The first week is still being played. Ties stand, so a week can be shared.'

  return (
    <Screen eyebrow="Season 2026" title="Season" sub={sub}>
      <div className="stand">
        {stats.players.map((p) => (
          <div key={p.id} className={`srow${p.rank === 1 ? ' is-leader' : ''}`}>
            <span className="srow__pos num">{p.rank}</span>
            <Avatar name={p.name} color={p.color} teamId={p.team_id} size={36} />
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

      {book && (
        <>
          <HallOfFame awards={book.fame} />
          <HallOfShame awards={book.shame} />
          <Numbers records={book.numbers} />
        </>
      )}
    </Screen>
  )
}

/**
 * Points per week, one line per player.
 *
 * Drawn to a single scale that starts at zero and ends on a round number above the best
 * week. Nothing at all below two finished weeks: a chart of one point is worse than no
 * chart, and a sentence apologising for it was just something to scroll past.
 */
function Form({ form, played }) {
  if (played < 2) return null

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
            /* The chart sits in a dark well. Every seat colour was picked against Slate's
               white card and three of the four fail the 3:1 graphics floor down here.
               onDark raises lightness only, so the line is still recognisably theirs. */
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
 * One of Grant's badges. An unclaimed one is the same art in grey inside a dashed socket,
 * so you can see what is up for grabs rather than an empty hole.
 */
function Medal({ id, size, open = false }) {
  return (
    <span className={`medal${open ? ' is-open' : ''}`} style={{ '--medal-size': `${size}px` }}
          aria-hidden="true">
      <img src={badgeUrl(id)} alt="" width={size} height={size} decoding="async" />
    </span>
  )
}

/** Faces and names of whoever holds an award, with a count for anyone who holds it twice. */
function Holders({ people, size = 22 }) {
  return (
    <span className="hold">
      <span className="hold__faces">
        {people.map((h) => (
          <Avatar key={h.id} name={h.name} color={h.color} teamId={h.team_id} size={size} />
        ))}
      </span>
      <span>{people.map((h) => (h.count > 1 ? `${h.name} ×${h.count}` : h.name)).join(' & ')}</span>
    </span>
  )
}

/**
 * The trophy room. Awards somebody holds are shown big on a lit stage; the rest wait in
 * the up for grabs row, which Grant singled out as the part to keep.
 *
 * The stage fades in out of the page rather than starting on a hard edge. Grant, picking
 * this layout: "the transition from the season standings to the hall of fame is really
 * rough." It was a near-black panel butted straight against the last standings row.
 */
function HallOfFame({ awards }) {
  if (!awards.length) return null
  const won = awards.filter((a) => a.claimed)
  const open = awards.filter((a) => !a.claimed)
  return (
    <section className="fame" aria-labelledby="fame-title">
      <p className="book-kick">The record book</p>
      <h3 className="fame__title" id="fame-title">Hall of fame</h3>
      {won.length > 0 && (
        <div className={`fame__won${won.length % 2 ? ' is-odd' : ''}`}>
          {won.map((a) => (
            <div className="award" key={a.key}>
              <Medal id={a.key} size={104} />
              <p className="award__k">{a.label}</p>
              <Holders people={a.holders} />
              <p className="award__d">{a.detail}</p>
            </div>
          ))}
        </div>
      )}
      {open.length > 0 && (
        <>
          <p className="fame__sub">Up for grabs</p>
          {/* Two across for two or four, so four never leaves one alone on a row. */}
          <div className={`fame__grabs${open.length === 2 || open.length === 4 ? ' is-pairs' : ''}`}>
            {open.map((a) => (
              <div className="grab" key={a.key}>
                <Medal id={a.key} size={62} open />
                <p>{a.label}</p>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  )
}

/** The red panel. */
function HallOfShame({ awards }) {
  if (!awards.length) return null
  return (
    <section className="shame" aria-labelledby="shame-title">
      <h3 className="shame__title" id="shame-title">Hall of shame</h3>
      {awards.map((a) => (
        <div className="shame__row" key={a.key}>
          <Medal id={a.key} size={76} open={!a.claimed} />
          <div className="shame__txt">
            <p className="shame__k">{a.label}</p>
            {a.claimed ? (
              <>
                <Holders people={a.holders} size={24} />
                <p className="shame__d">{a.detail}</p>
              </>
            ) : (
              <p className="shame__d">Nobody yet. Every 20 has won so far.</p>
            )}
          </div>
        </div>
      ))}
    </section>
  )
}

/**
 * Everyone's numbers, as headlines: who holds each record in big type, everyone else in
 * one line underneath. A record nobody can hold yet says when it starts.
 */
function Numbers({ records }) {
  if (!records.length) return null
  return (
    <section aria-labelledby="numbers-title">
      <div className="book-head">
        <p className="book-kick">The record book</p>
        <h3 id="numbers-title">Everyone&rsquo;s numbers</h3>
      </div>
      <div className="heads">
        {records.map((r) => (
          <Headline key={r.key} r={r} />
        ))}
      </div>
    </section>
  )
}

function Headline({ r }) {
  const h = r.headline
  if (!h) {
    return (
      <div className="head is-open">
        <Medal id={r.key} size={54} open />
        <div className="head__body">
          <p className="head__k">{r.label}</p>
          <p className="head__wait">{r.open || 'Nobody yet'}</p>
        </div>
      </div>
    )
  }
  return (
    <div className={`head${r.bad ? ' is-bad' : ''}`}>
      <Medal id={r.key} size={54} />
      <div className="head__body">
        <p className="head__k">{r.label}</p>
        <p className="head__lead">
          <span className="head__faces">
            {h.leaders.map((x) => (
              <Avatar key={x.id} name={x.name} color={x.color} teamId={x.team_id} size={28} />
            ))}
          </span>
          <b>{h.leaders.map((x) => x.name).join(' & ')}</b>
          <span className="head__v num">{h.value}</span>
          {h.detail && <em>{h.detail}</em>}
        </p>
        {h.rest && <p className="head__rest">{h.rest}</p>}
      </div>
    </div>
  )
}
