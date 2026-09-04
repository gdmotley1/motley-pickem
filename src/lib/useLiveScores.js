import { useEffect, useState } from 'react'
import { fetchLiveScores } from './espn.js'

/**
 * Keeps live ESPN results for a slate, refreshed while somebody is actually looking.
 *
 * Shared by the Board and the Standings so both react to a final the moment it happens
 * and neither has its own copy of the polling rules. Returns the map `withLive` and
 * `liveWinner` expect, or null before the first response.
 *
 * Every 60 seconds while a game is in play, which is well inside the ten minutes Grant
 * asked for and half the data of a 30 second poll. Every 5 minutes otherwise, so a
 * kickoff that happens with the app already open is still picked up. Nothing at all once
 * the database has graded every game.
 */
export function useLiveScores(games) {
  const [live, setLive] = useState(null)

  useEffect(() => {
    if (!games?.length) return undefined
    if (games.every((g) => g.winner_abbr)) return undefined

    let alive = true
    let timer = null
    // Held outside React state so each poll can narrow itself to the days it still has
    // something to learn about, rather than refetching settled games forever.
    let known = null

    const tick = async () => {
      if (!alive) return
      // A hidden tab is not being watched, and its timers are throttled anyway.
      if (document.visibilityState === 'visible') {
        try {
          known = await fetchLiveScores(games, known)
          if (alive) setLive(known)
        } catch {
          /* Keep whatever the database gave us. A missing live score is not an error
             worth putting on screen. */
        }
      }
      if (!alive) return
      const playing = games.some((g) => g.locked && !g.winner_abbr)
      timer = setTimeout(tick, playing ? 60000 : 300000)
    }

    // Coming back to the app is the moment the score matters most. Waiting out the rest
    // of the interval would show a stale number on the screen you just unlocked.
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
  }, [games])

  return live
}
