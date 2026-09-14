import { useEffect, useMemo, useState } from 'react'
import * as api from '../lib/api.js'
import { friendly } from '../lib/errors.js'
import { Avatar, Empty, IconTrophy, Screen, Spinner } from '../components/ui.jsx'
import Led from '../components/Led.jsx'
import { seasonStats } from '../lib/seasonStats.js'
import { seasonRecords } from '../lib/seasonRecords.js'
import { badgeUrl } from '../lib/badges.js'

/**
 * The whole year: the standings, form once there is any, and the record book.
 *
 * Top to bottom, as Grant picked it by number on 2026-09-12: standings, the Hall of fame as
 * the trophy room (7), the Hall of shame as the red panel (10), and everyone's numbers as
 * ranked ladders (4, off a second board the same night, replacing headlines he found hard to
 * read). The standings became trading cards on the jumbotron on 2026-09-13, under the same
 * black header as every tab, and the form chart that sat under them went the same night:
 * "take the form away dont like it".
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
          The standings and the record book fill in here as the season goes. Come
          back once the first game has a result.
        </Empty>
      </Screen>
    )

  const sub = stats.played
    ? `${stats.played} ${stats.played === 1 ? 'week' : 'weeks'} in the books. Ties stand, so a week can be shared.`
    : 'The first week is still being played. Ties stand, so a week can be shared.'

  return (
    <Screen eyebrow="Season 2026" title="Season" sub={sub}>
      <Standings players={stats.players} />

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
 * The standings, as a trading card per player: rank badge and logo on a lit stage, the name
 * on a bar, the season's points in LED, and the record and the points back from first along
 * the foot. First place is the gold card; a tie for first is two gold cards.
 *
 * Grant's pick on 2026-09-13, from four standings and then four variants of the podium:
 * "ship the trading card one from before i liked that better". The rows it replaced were
 * "dinky compared to everything else". Two across, so four players are two rows.
 */
function Standings({ players }) {
  const lead = players[0]?.points || 0
  return (
    <div className="jb standings">
      <div className="scards">
        {players.map((p) => (
          <div key={p.id} className={`scard${p.points === lead ? ' is-lead' : ''}`}>
            <span className="scard__stage">
              <span className="scard__rank num">{p.rank}</span>
              <Avatar name={p.name} color={p.color} teamId={p.team_id} size={64} />
            </span>
            <span className="scard__name">{p.name}</span>
            <span className="scard__pts">
              <Led>{p.points}</Led>
            </span>
            <span className="scard__foot">
              <span>
                <i className="scard__k">Record</i>
                <b className="num">
                  {p.correct}-{p.games - p.correct}
                </b>
              </span>
              <span>
                <i className="scard__k">Back</i>
                {/* A dash for whoever is in first, never a zero: first is not zero behind
                    anyone, it is the one everyone else is measured from. */}
                <b className="num">{p.points === lead ? '-' : lead - p.points}</b>
              </span>
            </span>
          </div>
        ))}
      </div>
    </div>
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
 * Everyone's numbers, as ranked ladders: each record's name as a heading, then all four of
 * you first to last, the holder's row drawn biggest. A record nobody can hold yet says
 * when it starts instead.
 */
function Numbers({ records }) {
  if (!records.length) return null
  return (
    <section aria-labelledby="numbers-title">
      <div className="book-head">
        <h3 id="numbers-title">Everyone&rsquo;s numbers</h3>
      </div>
      <div className="ladders">
        {records.map((r) => (
          <Ladder key={r.key} r={r} />
        ))}
      </div>
    </section>
  )
}

function Ladder({ r }) {
  return (
    <section className={`ladder${r.bad ? ' is-bad' : ''}`} aria-label={r.label}>
      <header className="ladder__hd">
        <Medal id={r.key} size={38} open={!!r.open} />
        <h4>{r.label}</h4>
      </header>
      {r.open ? (
        <p className="ladder__wait">{r.open}</p>
      ) : (
        <ol className="ladder__list">
          {/* Every row is the same four columns: rank, logo, name with at most one line
              under it, and the number alone in its own right-hand column, so the numbers
              line up down the card whatever a row has to say. */}
          {r.rows.map((row) => (
            <li key={row.id}
                className={`rung${row.lead ? ' is-lead' : ''}${row.empty ? ' is-none' : ''}`}>
              <span className="rung__rank num">{row.rank || '–'}</span>
              <Avatar name={row.name} color={row.color} teamId={row.team_id}
                      size={row.lead ? 34 : 28} />
              <span className="rung__who">
                <span className="rung__name">{row.name}</span>
                {(row.note || row.empty) && (
                  <span className="rung__note">{row.note || row.empty}</span>
                )}
              </span>
              <b className="rung__val num">{row.empty ? '–' : row.display}</b>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
