import { useEffect, useState } from 'react'
import { fetchRankings } from './matchup.js'

/**
 * The AP poll, keyed by ESPN team id, for any screen that shows a team.
 *
 * Shared by Picks, the Board, the matchup sheet and Setup so none of them has its own
 * copy of the fetch, and so a rank looks the same wherever it appears. `fetchRankings`
 * caches one promise for the life of the session, so four screens calling this still
 * make one ~35KB request.
 *
 * Returns null until the poll arrives, and stays null if it never does. A failure is
 * swallowed on purpose: a missing rank is not worth an error message on a pick screen,
 * and the `Rank` component reserves its space either way, so nothing moves when the
 * numbers land.
 */
export function useRanks() {
  const [ranks, setRanks] = useState(null)

  useEffect(() => {
    let alive = true
    fetchRankings()
      .then((r) => alive && setRanks(r))
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [])

  return ranks
}

/** The rank for one side of a game, or undefined. Ids are strings in the ranking map. */
export const rankOf = (ranks, teamId) =>
  teamId == null ? undefined : ranks?.get(String(teamId))
