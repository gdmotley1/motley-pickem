import { useEffect, useMemo, useRef, useState } from 'react'
import * as api from '../lib/api.js'
import TeamLogo from '../components/TeamLogo.jsx'
import { Avatar, Empty, IconClock, IconLock, Screen, Spinner } from '../components/ui.jsx'
import { WeekScore, ScoreBug, useHeaderOffset } from '../components/WeekScore.jsx'
import { withLive } from '../lib/espn.js'
import { weekScore } from '../lib/weekScore.js'
import { useLiveScores } from '../lib/useLiveScores.js'
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

  const live = useLiveScores(slate)

  /* Score, status and winner all come from ESPN once a game is under way, so a final
     marks the loser and fills in everyone's points the moment it happens rather than
     whenever the sync job next runs. `withLive` still defers to a database winner
     wherever there is one, so the two can never disagree. */
  const games = useMemo(() => {
    if (!slate) return null
    if (!live) return slate
    return slate.map((g) => withLive(g, live))
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

  const score = useMemo(
    () => (games && rows && roster ? weekScore(games, rows, roster) : null),
    [games, rows, roster],
  )

  /* Nothing to show before the first kickoff: four empty bars say less than the
     "unlock as they kick off" line already above them. */
  const showScore = !!score && games.some((g) => g.locked)

  /* The pinned strip takes over the moment the card itself has scrolled away, so the
     score is never more than a glance away twelve games down the board. Watching the card
     beats watching the scroll offset: no listener, and nothing to keep in step with the
     card's height. The header is sticky and covers the top of the page, so the top of the
     viewport is not the top of what can be read, and the margin below takes it off. */
  const headerH = useHeaderOffset()
  const cardRef = useRef(null)
  const [pinned, setPinned] = useState(false)
  useEffect(() => {
    const el = cardRef.current
    if (!el || typeof IntersectionObserver === 'undefined') return undefined
    const io = new IntersectionObserver(([e]) => setPinned(!e.isIntersecting), {
      rootMargin: `-${headerH}px 0px 0px 0px`,
    })
    io.observe(el)
    return () => io.disconnect()
  }, [showScore, headerH])

  if (error) return <p className="err">{error}</p>
  if (!games || !rows || !roster) return <Spinner />

  /* This is the screen the app opens on now, so a week with nothing published has to say
     so. get_slate joins on weeks.published and returns no rows until Dad hits Publish,
     which otherwise reads as "All 0 games are open." above an empty page. */
  if (!games.length)
    return (
      <Screen eyebrow={week?.label || 'This week'} title="No slate yet">
        <Empty icon={<IconClock />} title="Nothing published">
          Your commissioner has not published this week&apos;s twenty games.
        </Empty>
      </Screen>
    )

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
      {showScore && (
        <>
          <WeekScore score={score} cardRef={cardRef} />
          <ScoreBug score={score} pinned={pinned} top={headerH} />
        </>
      )}

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

/**
 * Fill in correct and points from whatever winner the card has.
 *
 * get_board leaves both null until the database has graded the game, which waits on the
 * sync job. When the live score says it is over, the arithmetic is the same one the
 * server does, so do it here and let the card be right immediately. A row the database
 * has already graded is returned untouched.
 */
function graded(pick, winner) {
  if (!pick || !winner || pick.correct !== null) return pick
  const correct = pick.pick_abbr === winner
  return { ...pick, correct, points: correct ? pick.confidence : 0 }
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
          const p = graded(
            picks.find((x) => x.player_id === player.id),
            game.winner_abbr,
          )
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
