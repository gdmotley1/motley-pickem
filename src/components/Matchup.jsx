import { useEffect, useState } from 'react'
import * as api from '../lib/api.js'
import { fetchMatchup } from '../lib/matchup.js'
import TeamLogo from '../components/TeamLogo.jsx'
import { Spinner } from './ui.jsx'
import { kickoffLabel } from '../lib/format.js'

/**
 * What a game looks like before you pick it.
 *
 * Built for one question only: how confident should I be? That is why ESPN's Matchup
 * Predictor is the top item and the biggest thing on the screen. In a confidence pool
 * "ESPN says 98%" decides whether a game is your 20 or your 14, which is more use than
 * any single team statistic.
 *
 * Everything here is display. None of it reaches Postgres, none of it grades a pick, and
 * if ESPN is unreachable the sheet says so and the pick flow carries on unaffected.
 *
 * Deliberately absent: player leaders. ESPN's `leaders` block on a game summary is empty
 * until the game has been played, at which point it holds that game's box score rather
 * than season form, so it is worthless as a preview. Season leaders live on a different
 * endpoint that needs a reference hop per athlete, which belongs in the sync job rather
 * than on a phone. Checked 2026-09-04.
 */
export default function Matchup({ game, ranks, picked }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let alive = true
    setData(null)
    setError(null)
    fetchMatchup(game.game_id, game.home_id, game.away_id)
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e.message))
    return () => {
      alive = false
    }
  }, [game.game_id, game.home_id, game.away_id])

  const total = api.totalLabel(game)

  return (
    <div className="mu">
      <div className="mu__head">
        <Side game={game} side="away" ranks={ranks} data={data} picked={picked} />
        <span className="mu__at">{game.neutral_site ? 'vs' : '@'}</span>
        <Side game={game} side="home" ranks={ranks} data={data} picked={picked} />
      </div>

      <p className="mu__when">
        {kickoffLabel(game.kickoff)}
        {game.tv ? ` · ${game.tv}` : ''}
        {' · '}
        <span className="num">{api.spreadLabel(game)}</span>
        {total ? <span className="num">{` · ${total}`}</span> : null}
      </p>

      {error && (
        <p className="mu__msg">
          Could not reach ESPN for this one. The line above still stands.
        </p>
      )}

      {!data && !error && (
        <div className="mu__loading">
          <Spinner />
        </div>
      )}

      {data && (
        <>
          {data.winProb ? (
            <section className="mu__sec">
              <h4 className="mu__h">ESPN win probability</h4>
              <ProbBar
                abbr={game.away_abbr}
                pct={data.winProb.away}
                mine={picked === game.away_abbr}
              />
              <ProbBar
                abbr={game.home_abbr}
                pct={data.winProb.home}
                mine={picked === game.home_abbr}
              />
            </section>
          ) : (
            <section className="mu__sec">
              <h4 className="mu__h">ESPN win probability</h4>
              {/* Not an error. ESPN stops publishing a projection once a game is final,
                  the same way it drops the odds block. */}
              <p className="mu__msg">No projection for this game.</p>
            </section>
          )}

          {(data.lastFive.away.length > 0 || data.lastFive.home.length > 0) && (
            <section className="mu__sec">
              <h4 className="mu__h">Last 5</h4>
              <Form abbr={game.away_abbr} games={data.lastFive.away} />
              <Form abbr={game.home_abbr} games={data.lastFive.home} />
            </section>
          )}

          {(data.venue || data.weather) && (
            <section className="mu__sec">
              <h4 className="mu__h">Where</h4>
              <p className="mu__where">
                {data.venue}
                {data.weather ? (
                  <span className="mu__wx num">
                    {`${Math.round(data.weather.temp)}°`}
                    {Number.isFinite(data.weather.precip)
                      ? ` · ${Math.round(data.weather.precip)}% rain`
                      : ''}
                  </span>
                ) : null}
              </p>
            </section>
          )}
        </>
      )}
    </div>
  )
}

/** One team in the header: logo, AP rank, school, record. */
function Side({ game, side, ranks, data, picked }) {
  const abbr = game[`${side}_abbr`]
  const rank = ranks?.get(String(game[`${side}_id`]))
  const record = data?.records?.[side]

  return (
    <div className={`mu__team${picked === abbr ? ' is-mine' : ''}`}>
      <TeamLogo teamId={game[`${side}_id`]} abbr={abbr} size={44} />
      <span className="mu__name">
        {rank ? <span className="mu__rank num">{rank}</span> : null}
        {game[`${side}_school`] || abbr}
      </span>
      {/* Reserved whether or not a record has loaded, so the header does not jump when
          the fetch lands. Week 1 records are legitimately "0-0". */}
      <span className="mu__rec num">{record || ' '}</span>
    </div>
  )
}

function ProbBar({ abbr, pct, mine }) {
  const n = Math.max(0, Math.min(100, pct))
  return (
    <div className={`pbar${mine ? ' is-mine' : ''}`}>
      {/* The marker rides in the label rather than on a line of its own. As its own grid
          row it pushed the second bar down, which left the two bars unevenly spaced and
          read as though it belonged to the team below it. */}
      <span className="pbar__abbr">
        {abbr}
        {mine && (
          <span className="pbar__mine" role="img" aria-label="your pick">
            &#10003;
          </span>
        )}
      </span>
      <span className="pbar__track">
        {/* Width only, no opacity: a backgrounded tab pauses animations and a bar that
            faded in from 0 would strand itself invisible. */}
        <span className="pbar__fill" style={{ width: `${n}%` }} />
      </span>
      <span className="pbar__pct num">{n >= 10 ? Math.round(n) : n.toFixed(1)}%</span>
    </div>
  )
}

/** Five tiles, oldest on the left, so a streak reads left to right like a sentence. */
function Form({ abbr, games }) {
  if (!games.length) return null
  return (
    <div className="form">
      <span className="form__abbr">{abbr}</span>
      <div className="form__tiles">
        {games.map((g, i) => (
          <div key={i} className="form__tile">
            <span className={`form__res form__res--${g.result === 'W' ? 'w' : 'l'}`}>
              {g.result}
            </span>
            <span className="form__opp">
              {g.away ? '@' : ''}
              {g.opponent || '—'}
            </span>
            <span className="form__score num">{g.score || ''}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
