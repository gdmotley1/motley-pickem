import { useEffect, useMemo, useState } from 'react'
import * as api from '../lib/api.js'
import TeamLogo from '../components/TeamLogo.jsx'
import { Avatar, Empty, IconClock, Screen, Spinner } from '../components/ui.jsx'
import { kickoffLabel } from '../lib/format.js'

/**
 * Everyone's picks, revealed game by game as each one kicks off.
 *
 * The server decides what is visible: get_board only returns rows for games where
 * kickoff has passed. Nothing here filters for secrecy, so there is no way for the
 * client to leak an unplayed pick.
 */
export default function Board({ me, weekId, week }) {
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

  const byGame = useMemo(() => {
    const m = new Map()
    for (const r of rows || []) {
      if (!m.has(r.game_id)) m.set(r.game_id, [])
      m.get(r.game_id).push(r)
    }
    for (const list of m.values()) list.sort((a, b) => b.confidence - a.confidence)
    return m
  }, [rows])

  if (error) return <p className="err">{error}</p>
  if (!slate || !rows || !roster) return <Spinner />

  const open = slate.filter((g) => g.locked)
  const upcoming = slate.filter((g) => !g.locked)

  return (
    <Screen
      eyebrow={week?.label || "This week"}
      title="The Board"
      sub={
        upcoming.length === 0 && open.length
          ? `All ${slate.length} games are open.`
          : open.length
            ? `${open.length} of ${slate.length} games open. The other ${upcoming.length} unlock at kickoff.`
            : 'Everyone’s picks stay hidden until each game kicks off.'
      }
    >
      {open.length === 0 ? (
        <Empty icon={<IconClock />} title="Nothing has kicked off yet">
          The moment the first game starts, everyone&apos;s pick for it appears here.
          {upcoming.length > 0 && (
            <>
              <br />
              First up: {upcoming[0].away_abbr} at {upcoming[0].home_abbr},{' '}
              {kickoffLabel(upcoming[0].kickoff)}.
            </>
          )}
        </Empty>
      ) : (
        <div style={{ paddingTop: 4 }}>
          {open.map((g) => (
            <BoardGame
              key={g.game_id}
              game={g}
              picks={byGame.get(g.game_id) || []}
              roster={roster}
              me={me}
            />
          ))}
        </div>
      )}

      {open.length > 0 && upcoming.length > 0 && (
        <p className="sub" style={{ padding: '6px 16px 0', textAlign: 'center' }}>
          {upcoming.length} more game{upcoming.length > 1 ? 's' : ''} unlock at kickoff.
        </p>
      )}
    </Screen>
  )
}

function BoardGame({ game, picks, roster, me }) {
  const done = !!game.winner_abbr
  const homeWon = done && game.winner_abbr === game.home_abbr
  const awayWon = done && game.winner_abbr === game.away_abbr

  return (
    <div className="bgame">
      <div className="bgame__head">
        <div className="bgame__score">
          <span className={`bgame__side${done && !awayWon ? ' is-loser' : ''}`}>
            <TeamLogo teamId={game.away_id} abbr={game.away_abbr} size={22} />
            {game.away_abbr}
            {game.away_score != null && (
              <span className="bgame__pts num">{game.away_score}</span>
            )}
          </span>
          <span className="bgame__sep">{game.neutral_site ? 'vs' : '@'}</span>
          <span className={`bgame__side${done && !homeWon ? ' is-loser' : ''}`}>
            <TeamLogo teamId={game.home_id} abbr={game.home_abbr} size={22} />
            {game.home_abbr}
            {game.home_score != null && (
              <span className="bgame__pts num">{game.home_score}</span>
            )}
          </span>
        </div>
        <span className={`chip${done ? '' : ' chip--live'}`}>
          {done ? 'Final' : game.status_detail || 'Live'}
        </span>
      </div>

      {/* Every claimed player gets a row whether or not they picked, so each game card
          is exactly the same height and a missing pick is visible rather than absent. */}
      <div className="bpicks">
        {roster.map((player) => {
          const p = picks.find((x) => x.player_id === player.id)
          const mine = player.id === me.id
          if (!p)
            return (
              <div className="bpick bpick--none" key={player.id}>
                <Avatar name={player.name} color={player.color} size={22} />
                <span className="bpick__who">
                  {player.name}
                  {mine ? ' (you)' : ''}
                </span>
                <span className="bpick__team">no pick</span>
                <span className="bpick__pts num">—</span>
              </div>
            )
          return (
            <div
              key={player.id}
              className={`bpick${p.correct === true ? ' is-right' : ''}${
                p.correct === false ? ' is-wrong' : ''
              }`}
            >
              <Avatar name={p.player_name} color={p.player_color} size={22} />
              <span className="bpick__who">
                {p.player_name}
                {mine ? ' (you)' : ''}
              </span>
              <span className="bpick__team">{p.pick_abbr}</span>
              {p.auto && <span className="bpick__auto">auto</span>}
              <span className="bpick__pts num">
                {p.points === null ? p.confidence : `+${p.points}`}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
