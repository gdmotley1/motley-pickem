import { useEffect, useMemo, useState } from 'react'
import * as api from '../lib/api.js'
import { Avatar, Empty, IconTrophy, Screen, Spinner } from '../components/ui.jsx'
import { withLive } from '../lib/espn.js'
import { useLiveScores } from '../lib/useLiveScores.js'
import { weekRecap } from '../lib/weekRecap.js'

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
  const [error, setError] = useState(null)

  useEffect(() => {
    let alive = true
    Promise.all([api.getSlate(weekId), api.getBoard(weekId), api.listSeats()])
      .then(([s, b, seats]) => {
        if (!alive) return
        setSlate(s)
        setRows(b)
        setRoster(seats.filter((x) => x.claimed))
      })
      .catch((e) => alive && setError(e.message))
    return () => {
      alive = false
    }
  }, [weekId])

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

  if (error) return <p className="err">{error}</p>
  if (!recap) return <Spinner />

  const label = week?.label || 'This week'
  const played = recap.players.filter((p) => p.games > 0)

  if (!played.length)
    return (
      <Screen eyebrow={label} title="This week">
        <Empty icon={<IconTrophy />} title="Nothing to show yet">
          Once games start going final, the table fills in here. The full write-up lands
          when the last game of the week ends.
        </Empty>
      </Screen>
    )

  const mine = recap.players.find((p) => p.id === me?.id)

  return (
    <Screen
      eyebrow={`${label} · ${recap.complete ? 'final' : 'in progress'}`}
      title={recap.complete ? headline(recap) : 'This week'}
      sub={
        recap.complete
          ? undefined
          : 'Ties stand. The write-up lands once every game has finished.'
      }
    >
      <Standings players={recap.players} />

      {recap.complete && mine && <YourWeek p={mine} />}
      {recap.complete && <Ranking players={recap.players} />}
      {recap.complete && <Decisive recap={recap} />}
      {recap.complete && <Upsets list={recap.upsets} />}
      {recap.complete && <InNumbers recap={recap} />}
    </Screen>
  )
}

/** "Grant takes it by 7", or the shared version. Both are statements of the score. */
function headline(recap) {
  const names = recap.leaders.map((p) => p.name)
  if (names.length > 1) return `${list(names)} share it`
  return recap.margin > 0 ? `${names[0]} takes it by ${recap.margin}` : `${names[0]} takes it`
}

const list = (xs) =>
  xs.length <= 1 ? xs[0] || '' : `${xs.slice(0, -1).join(', ')} and ${xs[xs.length - 1]}`

function Standings({ players }) {
  return (
    <div className="stand">
      {players.map((p) => (
        <div key={p.id} className={`srow${p.rank === 1 ? ' is-leader' : ''}`}>
          <span className="srow__pos num">{p.rank}</span>
          <Avatar name={p.name} color={p.color} teamId={p.team_id} size={36} />
          <span className="srow__body">
            <span className="srow__name">{p.name}</span>
            <span className="srow__meta num">
              {p.correct}-{p.wrong}
              {p.autos > 0 && ` · ${p.autos} auto`}
            </span>
          </span>
          <span>
            <span className="srow__pts num">{p.points}</span>
            <span className="srow__ptslabel">pts</span>
          </span>
        </div>
      ))}
    </div>
  )
}

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
