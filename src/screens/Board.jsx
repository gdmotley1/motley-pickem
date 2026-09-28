import { useEffect, useMemo, useRef, useState } from 'react'
import * as api from '../lib/api.js'
import { friendly } from '../lib/errors.js'
import PickNudge from '../components/PickNudge.jsx'
import Led from '../components/Led.jsx'
import Mark from '../components/Mark.jsx'
import WeekPager from '../components/WeekPager.jsx'
import { Avatar, IconLock, Rank, Spinner } from '../components/ui.jsx'
import { ScoreBug, useHeaderOffset } from '../components/WeekScore.jsx'
import { withLive } from '../lib/espn.js'
import { weekScore } from '../lib/weekScore.js'
import { useLiveScores } from '../lib/useLiveScores.js'
import { rankOf, useRanks } from '../lib/useRanks.js'
import { boardNav, isComplete } from '../lib/weekNav.js'
import { dateRangeLabel, kickoffLabel } from '../lib/format.js'
import { useTeams } from '../lib/teams.js'
import { schoolPanel } from '../lib/schoolField.js'

/**
 * Everyone's picks, revealed game by game as each one kicks off, on the jumbotron.
 *
 * The look is direction 1 of the six Grant was shown on 2026-09-12 ("its phenomenal"): a
 * stadium LED wall, with a glowing leaderboard, every game as a tile lit in the schools'
 * colors, big numbers made of LED dots, and a crawl of the finals along the bottom. His one
 * change: each pick shows the logo of the team picked, not the player's own avatar.
 *
 * The server decides what is visible: get_board only returns rows for games where
 * kickoff has passed. Nothing here filters for secrecy, so there is no way for the
 * client to leak an unplayed pick.
 *
 * Since 2026-09-28 it steps back through the weeks that have been played, which Grant
 * asked for. The week being viewed is local to this screen, never App's `weekId`: that one
 * is shared with Picks and Setup, and dragging them back a week would mean settling an
 * argument on the Board and then finding the whole slate locked on Picks. It resets on its
 * own when the tab changes, because App unmounts the screen.
 */
export default function Board({ me, weekId, week, onNavigate, onWeek }) {
  const [slate, setSlate] = useState(null)
  const [rows, setRows] = useState(null)
  const [roster, setRoster] = useState(null)
  const [weeks, setWeeks] = useState(null)
  const [error, setError] = useState(null)
  const teams = useTeams()

  /* Null until somebody steps, so the current week keeps flowing down from App until then.
     It has to: App opens on a remembered week id and replaces it once get_current_week
     answers, and a viewId seeded from the first render would pin the Board to the stale
     one. */
  const [viewId, setViewId] = useState(null)
  const view = viewId ?? weekId

  /* The week list is the pager's and nothing else's, so a failure leaves the Board itself
     working with both arrows dead rather than putting an error over the home screen. */
  useEffect(() => {
    let alive = true
    api
      .listWeeks()
      .then((w) => alive && setWeeks(w))
      .catch(() => alive && setWeeks([]))
    return () => {
      alive = false
    }
  }, [])

  useEffect(() => {
    let alive = true
    setSlate(null)
    setRows(null)
    Promise.all([api.getSlate(view), api.getBoard(view), api.listSeats()])
      .then(([s, b, seats]) => {
        if (!alive) return
        setSlate(s)
        setRows(b)
        setRoster(seats.filter((x) => x.claimed))
      })
      .catch((e) => alive && setError(friendly(e)))
    return () => {
      alive = false
    }
  }, [view])

  const live = useLiveScores(slate)
  const ranks = useRanks()

  const nav = useMemo(() => boardNav(weeks, weekId, view), [weeks, weekId, view])

  /* Tell App which week is on screen, so its header cannot say Week 4 over a board
     showing Week 3. Reported rather than read, because the week being viewed is this
     screen's and App's `weekId` has to go on meaning the week being played: Picks and
     Setup are still on it. Cleared when the tab changes and this unmounts. */
  const viewedId = nav.current?.id ?? null
  useEffect(() => {
    onWeek?.(nav.current || null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [viewedId, onWeek])
  useEffect(() => () => onWeek?.(null), [onWeek])

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
    return m
  }, [rows])

  const score = useMemo(
    () => (games && rows && roster ? weekScore(games, rows, roster) : null),
    [games, rows, roster],
  )

  /* Nothing to rank before the first kickoff: four players level on zero says less than
     the game tiles underneath, which already show your own picks. */
  const showScore = !!score && games.some((g) => g.locked)

  /* The pinned strip takes over the moment the leaderboard has scrolled away, so the score
     is never more than a glance away twelve games down. The header is sticky and covers
     the top of the page, so the margin below takes it off. */
  const headerH = useHeaderOffset()
  const cardRef = useRef(null)
  const [pinned, setPinned] = useState(false)
  useEffect(() => {
    const el = cardRef.current
    /* Stepping to another week unmounts the leaderboard while the new one loads. Without
       this the strip would come back pinned over the top of a board scrolled to its
       first tile, until the observer's first callback corrected it a frame later. */
    if (!el) setPinned(false)
    if (!el || typeof IntersectionObserver === 'undefined') return undefined
    const io = new IntersectionObserver(([e]) => setPinned(!e.isIntersecting), {
      rootMargin: `-${headerH}px 0px 0px 0px`,
    })
    io.observe(el)
    return () => io.disconnect()
  }, [showScore, headerH])

  if (error) return <p className="err">{error}</p>

  const label = nav.current?.label || week?.label || 'This week'

  /* Rendered above everything the week itself draws, so stepping from a full board to a
     loading one does not take the control you just used off the screen. `finished` is what
     stops the jump list naming a leader as if they had won; see WeekPager. */
  const pager = (
    <WeekPager
      nav={nav}
      onGo={setViewId}
      noNext="This is the week being played"
      finished={new Set(nav.list.filter(isComplete).map((w) => w.id))}
    />
  )

  if (!games || !rows || !roster)
    return (
      <div className="jb">
        {pager}
        <Spinner />
      </div>
    )

  const teamOf = (id) => teams?.find((t) => t.id === id)

  /* This is the screen the app opens on, so a week with nothing published has to say so.
     get_slate joins on weeks.published and returns no rows until Dad hits Publish. */
  if (!games.length)
    return (
      <div className="jb">
        {pager}
        <div className="jb-wall">
          <div className="jb-strip"><span>{label}</span></div>
          <section className="jb-empty">
            <h2>No slate yet</h2>
            <p>Your commissioner has not published this week&apos;s twenty games.</p>
          </section>
        </div>
      </div>
    )

  const finals = games.filter((g) => g.winner_abbr)
  const dates = dateRangeLabel(games.map((g) => g.kickoff))

  return (
    <div className="jb">
      {/* Above the score on purpose. Whatever this week has already become, the thing
          you can still do about it comes first. A week already played has no pending
          picks, so this draws nothing there. */}
      <PickNudge games={games} onGo={() => onNavigate?.('picks')} />

      {pager}

      <div className="jb-wall">
        <div className="jb-strip">
          {/* The days the week ran, not its name: the pager right above already says
              Week 3. Grant's call for the Week tab's strip on 2026-09-25, and the same
              repetition would be here. */}
          <span>{dates || label}</span>
          {score.playing > 0 && (
            <span className="jb-onair">
              <i />
              {score.playing} live
            </span>
          )}
          <span className="num">
            {score.graded}/{score.slateSize} final
          </span>
        </div>

        {showScore && <Leaderboard score={score} me={me} teamOf={teamOf} cardRef={cardRef} />}

        {/* Every game is listed, not just the ones that have started. An unplayed game
            shows your own pick, so you can check your card against the board before
            kickoff. */}
        <section className="jb-games" aria-label="Games">
          {games.map((g) => (
            <GameTile
              key={g.game_id}
              game={g}
              picks={byGame.get(g.game_id) || []}
              roster={roster}
              me={me}
              ranks={ranks}
              teamOf={teamOf}
            />
          ))}
        </section>
      </div>

      {finals.length > 0 && <Crawl games={finals} />}
      {showScore && <ScoreBug score={score} pinned={pinned} top={headerH} />}
    </div>
  )
}

function Leaderboard({ score, me, teamOf, cardRef }) {
  return (
    <section className="jb-panel" ref={cardRef} aria-label="Leaderboard">
      <h2 className="jb-title">Leaderboard</h2>
      {score.players.map((p) => (
        <div
          key={p.id}
          className={`jb-row${p.rank === 1 && score.best > 0 ? ' is-lead' : ''}`}
          style={{ '--jb-team': schoolPanel(teamOf(p.team_id), p.color) }}
        >
          <span className="jb-rank num">{p.rank}</span>
          <Avatar name={p.name} color={p.color} teamId={p.team_id} size={40} />
          <span className="jb-who">
            <b>
              {p.name}
              {p.id === me?.id && <i className="jb-you">You</i>}
            </b>
            <span className="num">
              {p.correct}-{p.played - p.correct} · {p.live} in play
            </span>
          </span>
          <Led className="jb-pts">{p.points}</Led>
        </div>
      ))}
    </section>
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

/** The side a pick is on, by abbreviation, so its chip can carry that school's mark. */
const idFor = (game, abbr) => (abbr === game.home_abbr ? game.home_id : abbr === game.away_abbr ? game.away_id : null)

function Odds({ game }) {
  const spread = game.spread_line == null ? null : api.spreadLabel(game)
  const total = api.totalLabel(game)
  if (!spread && !total) return <span className="jb-line" />
  return (
    <span className="jb-line num">
      {spread}
      {spread && total ? ' · ' : ''}
      {total}
    </span>
  )
}

function GameTile({ game, picks, roster, me, ranks, teamOf }) {
  const done = !!game.winner_abbr
  const started = !!game.locked
  const scored = game.home_score != null && game.away_score != null
  const state = done ? 'final' : started ? 'live' : 'soon'
  /* Who is ahead right now: the winner once it is final, the team in front while it is on,
     nobody at a tie or before kickoff. */
  const leader = done
    ? game.winner_abbr
    : started && scored && game.home_score !== game.away_score
      ? game.home_score > game.away_score ? game.home_abbr : game.away_abbr
      : null

  const team = (side) => {
    const abbr = game[`${side}_abbr`]
    const id = game[`${side}_id`]
    const t = teamOf(id)
    const lead = leader === abbr
    return (
      <div
        className={`jb-team${lead ? ' is-lead' : ''}${done && !lead ? ' is-loser' : ''}`}
        style={{ '--jb-team': schoolPanel(t, '#2a2f37') }}
      >
        <Mark id={id} abbr={abbr} size={38} />
        <span className="jb-school">
          <Rank n={rankOf(ranks, id)} />
          {t?.school || game[`${side}_school`] || abbr}
        </span>
        <span className="jb-arrow" aria-hidden="true" />
        {scored && started ? <Led className="jb-score">{game[`${side}_score`]}</Led> : <span />}
      </div>
    )
  }

  return (
    <article className={`jb-game is-${state}`}>
      <header className="jb-game__hd">
        {state === 'final' && <span className="jb-pill is-final">Final</span>}
        {state === 'live' && (
          <span className="jb-pill is-live">
            <i />
            {game.status_detail || 'Live'}
          </span>
        )}
        {state === 'soon' && (
          <span className="jb-pill is-soon">
            <IconLock />
            {kickoffLabel(game.kickoff)}
          </span>
        )}
        <Odds game={game} />
      </header>
      {team('away')}
      {team('home')}

      {/* Every claimed player gets a chip whether or not they picked, so each tile is the
          same height and a missing pick is visible rather than absent. The chip carries
          the logo of the team picked, per Grant: the player's own avatar is also a school
          logo, and next to "GT" it read as the pick. */}
      <div className="jb-picks">
        {roster.map((player) => {
          const mine = player.id === me?.id
          if (!started) {
            if (!mine) return <Chip key={player.id} name={player.name} state="hidden" />
            return (
              <Chip key={player.id} name={player.name} state="open" abbr={game.my_pick}
                    teamId={idFor(game, game.my_pick)} value={game.my_confidence ?? '–'} />
            )
          }
          const p = graded(picks.find((x) => x.player_id === player.id), game.winner_abbr)
          if (!p) return <Chip key={player.id} name={player.name} state="none" />
          const result = done
            ? p.correct ? 'won' : 'lost'
            : leader ? (p.pick_abbr === leader ? 'ahead' : 'behind') : 'open'
          return (
            <Chip key={player.id} name={player.name} state={result} abbr={p.pick_abbr} auto={p.auto}
                  teamId={idFor(game, p.pick_abbr)} value={result === 'won' ? `+${p.points}` : p.confidence} />
          )
        })}
      </div>
    </article>
  )
}

/**
 * One player's pick on one game: the picked school's mark, whose pick it is, and the
 * points. A win shows what it banked; everything else shows the wager, never a minus.
 */
function Chip({ name, state, abbr, teamId, value, auto }) {
  if (state === 'hidden')
    return (
      <span className="jb-pick is-hidden">
        <span className="jb-lock"><IconLock /></span>
        <span className="jb-pick__who">{name}</span>
        <b>Locked</b>
      </span>
    )
  if (state === 'none' || (state === 'open' && !abbr))
    return (
      <span className="jb-pick is-none">
        <span className="jb-lock">–</span>
        <span className="jb-pick__who">{name}</span>
        <b>No pick</b>
      </span>
    )
  return (
    <span className={`jb-pick is-${state}`}>
      <Mark id={teamId} abbr={abbr} size={26} />
      <span className="jb-pick__who">
        {name}
        {auto && <i className="jb-auto">auto</i>}
      </span>
      <b className="num">{value}</b>
    </span>
  )
}

/** The finals so far, crawling along the bottom of the wall. */
function Crawl({ games }) {
  const run = games.map((g) => `${g.away_abbr} ${g.away_score ?? ''}  ${g.home_abbr} ${g.home_score ?? ''}`).join('   ◆   ')
  return (
    <div className="jb-crawl" aria-label="Final scores">
      <span className="jb-crawl__k">Final</span>
      <div className="jb-crawl__win">
        <div className="jb-crawl__run">
          <span>{run}</span>
          <span aria-hidden="true">{run}</span>
        </div>
      </div>
    </div>
  )
}
