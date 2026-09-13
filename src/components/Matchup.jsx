import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import * as api from '../lib/api.js'
import { fetchMatchup } from '../lib/matchup.js'
import Led from './Led.jsx'
import Mark from './Mark.jsx'
import { Rank, Spinner } from './ui.jsx'
import { kickoffLabel, tvLabel } from '../lib/format.js'
import { schoolPanel } from '../lib/schoolField.js'
import { useTeams } from '../lib/teams.js'
import { rankOf } from '../lib/useRanks.js'

/**
 * What a game looks like before you pick it, on the jumbotron.
 *
 * Built for one question only: how confident should I be? That is why ESPN's Matchup
 * Predictor is the biggest number on the sheet. In a confidence pool "ESPN says 98%"
 * decides whether a game is your 20 or your 14, which is more use than any single team
 * statistic.
 *
 * The look is Grant's, picked over three rounds on 2026-09-13: the Board's jumbotron, the
 * two teams as trading cards (option 8 of 10), TV, spread and O/U as three labelled tiles,
 * then the win probability as two big LED numbers and this season as a column of chips
 * per team (option 1 of 2). School colors stay on the probability bar only: he called the
 * first version's team boxes, lit in school colors, weird.
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

const PANEL = '#2a2f37' // a school with no colors in the library, lit the Board's grey

const pctLabel = (pct) => {
  const n = Math.max(0, Math.min(100, pct))
  return `${n >= 10 ? Math.round(n) : n.toFixed(1)}%`
}

const Check = () => (
  <svg viewBox="0 0 24 24" width="15" height="15" fill="none" aria-hidden="true">
    <path d="m5 12.5 4.2 4.2L19 7" stroke="currentColor" strokeWidth="3" strokeLinecap="round"
          strokeLinejoin="round" />
  </svg>
)

export default function Matchup({ game, ranks, picked }) {
  const [data, setData] = useState(null)
  // Only ever a yes/no: the render below says one fixed sentence, so keeping the
  // exception's text here just looked like something that reaches the screen.
  const [failed, setFailed] = useState(false)
  const teams = useTeams()
  const panel = (side) => schoolPanel(teams?.find((t) => t.id === game[`${side}_id`]), PANEL)

  useEffect(() => {
    let alive = true
    setData(null)
    setFailed(false)
    fetchMatchup(game.game_id, game.home_id, game.away_id)
      .then((d) => alive && setData(d))
      .catch(() => alive && setFailed(true))
    return () => {
      alive = false
    }
  }, [game.game_id, game.home_id, game.away_id])

  const total = api.totalLabel(game)

  return (
    <div className="mu jb">
      <div className="mu__strip">
        <h2 className="mu__title">Matchup</h2>
        <span className="mu__kick">{kickoffLabel(game.kickoff)}</span>
      </div>

      <div className="jb-wall">
        <Cards game={game} ranks={ranks} data={data} failed={failed} picked={picked} teams={teams} />

        {/* The three things you check before a pick, each labelled, each the same size. */}
        <div className="mu__stats">
          <div className="mu__stat">
            <span className="mu__statk">TV</span>
            <b className="mu__statv">{game.tv ? tvLabel(game.tv) : '-'}</b>
          </div>
          <div className="mu__stat">
            <span className="mu__statk">Spread</span>
            <b className="mu__statv num">{api.spreadLabel(game)}</b>
          </div>
          <div className="mu__stat">
            <span className="mu__statk">O/U</span>
            <b className="mu__statv num">{total ? total.replace('O/U ', '') : '-'}</b>
          </div>
        </div>

        {failed && (
          <section className="mu__sec">
            <p className="mu__msg">Could not reach ESPN for this one. The line above still stands.</p>
          </section>
        )}

        {!data && !failed && (
          <div className="mu__loading">
            <Spinner />
          </div>
        )}

        {data && (
          <>
            <section className="mu__sec">
              <h4 className="mu__h">ESPN win probability</h4>
              {data.winProb ? (
                <>
                  <div className="mu__odds">
                    {['away', 'home'].map((side) => (
                      <div
                        key={side}
                        className={`mu__pct mu__pct--${side}${picked === game[`${side}_abbr`] ? ' is-mine' : ''}`}
                      >
                        <span className="mu__abbr">
                          {game[`${side}_abbr`]}
                          {picked === game[`${side}_abbr`] && <Check />}
                        </span>
                        <Led>{pctLabel(data.winProb[side])}</Led>
                      </div>
                    ))}
                  </div>
                  <div className="mu__split" aria-hidden="true">
                    {['away', 'home'].map((side) => (
                      <i
                        key={side}
                        style={{
                          flexGrow: Math.max(0.5, data.winProb[side]),
                          '--jb-team': panel(side),
                        }}
                      />
                    ))}
                  </div>
                </>
              ) : (
                /* Not an error. ESPN stops publishing a projection once a game is final,
                   the same way it drops the odds block. */
                <p className="mu__msg">No projection for this game.</p>
              )}
            </section>

            {(data.lastFive.away.length > 0 || data.lastFive.home.length > 0) && (
              <section className="mu__sec">
                {/* Not "Last 5" any more. It only ever shows this season now, so in
                    September it is legitimately one or two games and a heading promising
                    five would be the thing that is wrong. */}
                <h4 className="mu__h">This season</h4>
                <div className="mu__tape">
                  <Form abbr={game.away_abbr} games={data.lastFive.away} />
                  <Form abbr={game.home_abbr} games={data.lastFive.home} />
                </div>
              </section>
            )}

            {/* Sits below the form and above the venue so the sheet runs numbers, then
                form, then words, then where. Hidden entirely when ESPN wrote nothing,
                which is most games that are not on a network. */}
            {data.story && (
              <section className="mu__sec">
                <h4 className="mu__h">ESPN preview</h4>
                <p className="mu__story">{data.story}</p>
              </section>
            )}

            {(data.venue || data.weather) && (
              <section className="mu__sec">
                <h4 className="mu__h">Where</h4>
                <p className="mu__where">
                  <span>{data.venue}</span>
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
    </div>
  )
}

/**
 * The two teams as trading cards, away on the left, every part of one card the same as
 * the other: the logo on a lit stage, the school on a name bar, AP rank and record along
 * the foot. Your pick is the gold card.
 *
 * Both names share one size. If either would wrap, both step down together, twice at most,
 * and a name still too long after that wraps, balanced. The test is the text's own line
 * boxes: a range over a text node returns one rect per line.
 */
function Cards({ game, ranks, data, failed, picked, teams }) {
  const sides = ['away', 'home'].map((side) => {
    const id = game[`${side}_id`]
    const abbr = game[`${side}_abbr`]
    const team = teams?.find((t) => t.id === id)
    return {
      side,
      id,
      abbr,
      school: team?.school || game[`${side}_school`] || abbr,
      rank: rankOf(ranks, id) ?? game[`${side}_rank`],
      record: data?.records?.[side] || null,
      mine: picked === abbr,
    }
  })

  /* Only ever steps down. The sheet is keyed on the game, so a new game is a new mount; and
     resetting here raced the step, because React flushes this component's passive effects
     before rendering the update the layout effect asked for. */
  const ref = useRef(null)
  const [fit, setFit] = useState(0)
  const names = sides.map((s) => s.school).join('|')
  useLayoutEffect(() => {
    const lines = (el) => {
      const range = document.createRange()
      const walk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT)
      const tops = []
      while (walk.nextNode()) {
        range.selectNodeContents(walk.currentNode)
        for (const box of range.getClientRects()) tops.push(box.top)
      }
      tops.sort((a, b) => a - b)
      return tops.filter((t, i) => i === 0 || t - tops[i - 1] > 8).length
    }
    const check = () => {
      if (!ref.current) return
      const wraps = [...ref.current.querySelectorAll('.mu__cardname')].some((el) => lines(el) > 1)
      if (wraps) setFit((f) => (f < 2 ? f + 1 : f))
    }
    check()
    // The first sheet of a session can open before the lettering has loaded.
    document.fonts?.ready.then(check)
  }, [fit, names])

  return (
    <div ref={ref} className={`mu__head${fit ? ` is-fit${fit}` : ''}`}>
      {sides.map((s) => (
        <div key={s.side} className={`mu__card${s.mine ? ' is-mine' : ''}`}>
          <span className="mu__stage">
            <Mark id={s.id} abbr={s.abbr} size={100} />
            {s.mine && (
              <span className="mu__ribbon">
                <Check />
                Your pick
              </span>
            )}
          </span>
          <span className="mu__cardname">{s.school}</span>
          <span className="mu__cardstats">
            <span>
              <i>AP rank</i>
              {s.rank ? (
                <b>
                  <Rank n={s.rank} />
                </b>
              ) : (
                <b className="mu__nil">-</b>
              )}
            </span>
            <span>
              <i>Record</i>
              {/* Reserved while the fetch is out, so the card does not grow when it lands.
                  Week 1 records are legitimately "0-0". */}
              {s.record ? (
                <b className="num">{s.record}</b>
              ) : (
                <b className={failed || data ? 'mu__nil' : undefined}>{failed || data ? '-' : ' '}</b>
              )}
            </span>
          </span>
        </div>
      ))}
      <span className="mu__at">{game.neutral_site ? 'vs' : '@'}</span>
    </div>
  )
}

/** One column per team, a chip per game this season, oldest at the top. */
function Form({ abbr, games }) {
  return (
    <div className="mu__col">
      <span className="mu__colhead">{abbr}</span>
      {games.length ? (
        games.map((g, i) => (
          <span key={i} className="mu__game">
            <b className={`mu__res mu__res--${g.result === 'W' ? 'w' : 'l'}`}>{g.result}</b>
            <span className="mu__score num">{g.score || ''}</span>
            <span className="mu__opp">
              {g.away ? '@' : 'vs '}
              {g.opponent || '?'}
            </span>
          </span>
        ))
      ) : (
        <span className="mu__none">No games yet</span>
      )}
    </div>
  )
}
