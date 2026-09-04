import { useEffect, useMemo, useState } from 'react'
import * as api from '../lib/api.js'
import TeamLogo from '../components/TeamLogo.jsx'
import { Avatar, IconLock, Screen, Spinner } from '../components/ui.jsx'
import { fetchLiveScores } from '../lib/espn.js'
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
  const [live, setLive] = useState(null)
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

  /**
   * Poll ESPN while the board is open.
   *
   * The database only moves when the sync job runs, and that schedule slips by an hour
   * or more, so without this a game can sit at 0-0 through an entire half. Every 45
   * seconds while something is actually being played, every 5 minutes otherwise so a
   * kickoff that happens with the board already open still gets picked up, and not at
   * all once every game has been graded.
   */
  useEffect(() => {
    if (!slate?.length) return undefined
    if (slate.every((g) => g.winner_abbr)) return undefined

    let alive = true
    let timer = null

    const tick = async () => {
      if (!alive) return
      // A hidden tab is not being watched, and its timers are throttled anyway.
      if (document.visibilityState === 'visible') {
        try {
          const m = await fetchLiveScores(slate)
          if (alive) setLive(m)
        } catch {
          /* Keep whatever the database gave us. A missing live score is not an error
             worth putting on screen. */
        }
      }
      if (!alive) return
      const playing = slate.some((g) => g.locked && !g.winner_abbr)
      timer = setTimeout(tick, playing ? 45000 : 300000)
    }

    // Coming back to the app is the moment the score matters most. Waiting out the
    // rest of the interval would show a stale number on the screen you just unlocked.
    const onVisible = () => {
      if (document.visibilityState !== 'visible') return
      clearTimeout(timer)
      tick()
    }
    document.addEventListener('visibilitychange', onVisible)

    tick()
    return () => {
      alive = false
      clearTimeout(timer)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [slate])

  /* ESPN wins on the numbers, the database keeps the winner. Grading and the standings
     stay with the sync job, so the board can never show a result the standings do not
     already agree with. */
  const games = useMemo(() => {
    if (!slate) return null
    if (!live) return slate
    return slate.map((g) => {
      const l = live.get(String(g.game_id))
      return l ? { ...g, ...l } : g
    })
  }, [slate, live])

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
  if (!games || !rows || !roster) return <Spinner />

  const open = games.filter((g) => g.locked)
  const upcoming = games.filter((g) => !g.locked)

  return (
    <Screen
      eyebrow={week?.label || 'This week'}
      title="The Board"
      sub={
        upcoming.length === 0
          ? `All ${games.length} games are open.`
          : `${open.length} of ${games.length} open. The rest unlock as they kick off.`
      }
    >
      {/* Every game is listed, not just the ones that have started. An unplayed game
          shows locked with your own pick visible, so you can check your card against
          the board without waiting for kickoff. */}
      <div style={{ paddingTop: 4 }}>
        {games.map((g) =>
          g.locked ? (
            <BoardGame
              key={g.game_id}
              game={g}
              picks={byGame.get(g.game_id) || []}
              roster={roster}
              me={me}
            />
          ) : (
            <LockedGame key={g.game_id} game={g} roster={roster} me={me} />
          ),
        )}
      </div>
    </Screen>
  )
}

/** A game that has not kicked off: your pick is shown, everyone else's is hidden. */
function LockedGame({ game, roster, me }) {
  return (
    <div className="bgame bgame--locked">
      <div className="bgame__head">
        <div className="bgame__score">
          <span className="bgame__side">
            <TeamLogo teamId={game.away_id} abbr={game.away_abbr} size={22} />
            {game.away_abbr}
          </span>
          <span className="bgame__sep">{game.neutral_site ? 'vs' : '@'}</span>
          <span className="bgame__side">
            <TeamLogo teamId={game.home_id} abbr={game.home_abbr} size={22} />
            {game.home_abbr}
          </span>
        </div>
        <span className="chip">
          <IconLock />
          {kickoffLabel(game.kickoff)}
        </span>
      </div>

      <div className="bpicks">
        {roster.map((player) => {
          const mine = player.id === me.id
          return (
            <div className={`bpick${mine ? '' : ' bpick--hidden'}`} key={player.id}>
              <Avatar name={player.name} color={player.color} size={22} />
              <span className="bpick__who">
                {player.name}
                {mine ? ' (you)' : ''}
              </span>
              {mine ? (
                <>
                  <span className="bpick__team">{game.my_pick || 'no pick yet'}</span>
                  <span className="bpick__pts num">{game.my_confidence ?? '—'}</span>
                </>
              ) : (
                <>
                  <span className="bpick__team bpick__masked">
                    <IconLock />
                    hidden
                  </span>
                  <span className="bpick__pts num">–</span>
                </>
              )}
            </div>
          )
        })}
      </div>
    </div>
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
