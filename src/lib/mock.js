/**
 * In-memory stand-in for the Postgres RPCs, used when Supabase env vars are absent.
 *
 * It deliberately enforces the SAME rules as migrations/001_init.sql: a seat cannot be
 * stolen, a locked game cannot be changed, confidence must be a permutation of 1..N, and
 * get_board hides picks until kickoff. A lenient mock would mean building the UI against
 * rules the real backend does not have, and every bug surfacing on deploy.
 *
 * Append ?demo=1 to the URL to fill the other three seats, give everyone picks, and
 * pretend the week has finished so the Board and Standings have something to show. That
 * flag only exists in this file and never reaches the real backend.
 */

const KEY = 'pickem.mock.state'
const COLORS = ['#B0641B', '#1F7053', '#2E5C8A', '#8A2E4F']
const NAMES = ['Grant', 'Dad', 'Mom', 'Sister']

const params = new URLSearchParams(
  typeof location === 'undefined' ? '' : location.search,
)
export const DEMO = params.get('demo') === '1'

/* In demo mode, pretend it is the Monday after the slate so every game is final. */
const DEMO_NOW = Date.parse('2026-09-08T12:00:00Z')
const now = () => (DEMO ? DEMO_NOW : Date.now())

let cache = null
let weekCache = null

function load() {
  if (cache) return cache
  let saved = null
  try {
    saved = JSON.parse(localStorage.getItem(KEY) || 'null')
  } catch {
    saved = null
  }
  cache = saved || {
    players: [1, 2, 3, 4].map((id) => ({
      id,
      name: null,
      pin: null,
      is_admin: id <= 2,
      color: COLORS[id - 1],
    })),
    sessions: {},
    picks: {}, // `${playerId}:${gameId}` -> { pick, confidence, auto }
  }
  return cache
}

function save() {
  try {
    localStorage.setItem(KEY, JSON.stringify(cache))
  } catch {
    /* demo without storage still works for this page load */
  }
}

/* ------------------------------------------------------------------ helpers */

const fail = (m) => {
  throw new Error(m)
}
const kicked = (g) => new Date(g.kickoff).getTime() <= now()

/** Deterministic pseudo-random in [0,1) from a game id, so results never reshuffle. */
function seeded(id) {
  let h = 2166136261
  const s = String(id)
  for (let i = 0; i < s.length; i += 1) {
    h ^= s.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return ((h >>> 0) % 10000) / 10000
}

/** In demo mode, invent a plausible final: the favourite covers about 70% of the time. */
function withResult(g) {
  if (!DEMO || !kicked(g)) return g
  if (g.winner_abbr) return g
  const r = seeded(g.game_id)
  const fav = g.favorite_abbr || g.home_abbr
  const dog = g.underdog_abbr || g.away_abbr
  const favWins = r < 0.7
  const margin = Math.max(3, Math.round((Number(g.spread_line) || 7) * (0.4 + r)))
  const winner = favWins ? fav : dog
  const loserPts = 10 + Math.round(r * 17)
  const winPts = loserPts + margin
  return {
    ...g,
    state: 'post',
    winner_abbr: winner,
    home_score: winner === g.home_abbr ? winPts : loserPts,
    away_score: winner === g.away_abbr ? winPts : loserPts,
    status_detail: 'Final',
  }
}

async function week() {
  if (weekCache) return weekCache
  const res = await fetch(`${import.meta.env.BASE_URL}data/week01.json`)
  if (!res.ok) throw new Error('Could not load the week data')
  const raw = await res.json()
  weekCache = {
    ...raw,
    slate: raw.slate.map(withResult),
    alternates: raw.alternates.map(withResult),
  }
  if (DEMO) seedDemo(weekCache)
  return weekCache
}

/** Fill the other seats and give everyone a full card, so the Board is not empty. */
function seedDemo(w) {
  const s = load()
  let changed = false
  for (const p of s.players) {
    if (!p.name) {
      p.name = NAMES[p.id - 1]
      p.pin = '1111'
      changed = true
    }
    const has = w.slate.some((g) => s.picks[`${p.id}:${g.game_id}`])
    if (has) continue
    // Order by the spread, then jitter per player so nobody has identical cards.
    const ordered = [...w.slate].sort((a, b) => {
      const la = Number(a.spread_line) || 0
      const lb = Number(b.spread_line) || 0
      return lb - la + (seeded(`${p.id}-${a.game_id}`) - seeded(`${p.id}-${b.game_id}`)) * 9
    })
    ordered.forEach((g, i) => {
      const r = seeded(`${p.id}:${g.game_id}`)
      const fav = g.favorite_abbr || g.home_abbr
      const dog = g.underdog_abbr || g.away_abbr
      s.picks[`${p.id}:${g.game_id}`] = {
        pick: r < 0.78 ? fav : dog,
        confidence: w.slate.length - i,
        auto: r > 0.97,
      }
    })
    changed = true
  }
  if (changed) save()
}

function playerFor(token) {
  const s = load()
  return s.players.find((p) => p.id === s.sessions[token]) || null
}

function requireMe(token) {
  const me = playerFor(token)
  if (!me) fail('Not signed in')
  return me
}

function newSession(playerId) {
  const s = load()
  const token = `mock-${playerId}-${Math.random().toString(36).slice(2)}`
  s.sessions[token] = playerId
  save()
  return token
}

/* ---------------------------------------------------------------------- rpc */

export async function rpc(fn, args = {}) {
  const s = load()

  switch (fn) {
    case 'list_seats': {
      if (DEMO) await week() // seeds the demo names before the tiles render
      return load().players.map((p) => ({
        id: p.id,
        name: p.name,
        is_admin: p.is_admin,
        claimed: p.name !== null,
        color: p.color,
      }))
    }

    case 'claim_seat': {
      const { p_seat, p_name, p_pin } = args
      if (!/^\d{4}$/.test(p_pin || '')) fail('PIN must be exactly 4 digits')
      if (!String(p_name || '').trim()) fail('Name is required')
      const seat = s.players.find((p) => p.id === p_seat)
      if (!seat) fail('No such seat')
      if (seat.name !== null) fail('That seat is already taken')
      seat.name = String(p_name).trim()
      seat.pin = p_pin
      save()
      return newSession(seat.id)
    }

    case 'sign_in': {
      const seat = s.players.find((p) => p.id === args.p_seat)
      if (!seat || seat.pin === null) fail('That seat has not been claimed yet')
      if (seat.pin !== args.p_pin) fail('Wrong PIN')
      return newSession(seat.id)
    }

    case 'whoami': {
      const me = playerFor(args.p_token)
      if (!me) fail('Not signed in')
      return [{ id: me.id, name: me.name, is_admin: me.is_admin, color: me.color }]
    }

    case 'sign_out':
      delete s.sessions[args.p_token]
      save()
      return null

    case 'get_week': {
      requireMe(args.p_token)
      const w = await week()
      return [{ ...w.week, slate_size: w.slate.length }]
    }

    /* The mock has exactly one week, so "current" is that week. It still has to answer,
       because the app resolves the week from here before it asks for anything else. */
    case 'get_current_week': {
      requireMe(args.p_token)
      const w = await week()
      return [{ ...w.week, slate_size: w.slate.length }]
    }

    case 'get_slate': {
      const me = requireMe(args.p_token)
      const w = await week()
      return w.slate.map((g) => {
        const mine = s.picks[`${me.id}:${g.game_id}`]
        return {
          ...g,
          locked: kicked(g),
          my_pick: mine?.pick ?? null,
          my_confidence: mine?.confidence ?? null,
          my_auto: mine?.auto ?? null,
        }
      })
    }

    case 'get_board': {
      requireMe(args.p_token)
      const w = await week()
      const rows = []
      for (const g of w.slate) {
        if (!kicked(g)) continue // the visibility rule
        for (const p of s.players) {
          if (!p.name) continue
          const mine = s.picks[`${p.id}:${g.game_id}`]
          if (!mine) continue
          const correct = g.winner_abbr ? mine.pick === g.winner_abbr : null
          rows.push({
            game_id: g.game_id,
            player_id: p.id,
            player_name: p.name,
            player_color: p.color,
            pick_abbr: mine.pick,
            confidence: mine.confidence,
            auto: !!mine.auto,
            correct,
            points: correct === null ? null : correct ? mine.confidence : 0,
          })
        }
      }
      return rows
    }

    case 'get_standings': {
      requireMe(args.p_token)
      const w = await week()
      const byId = Object.fromEntries(w.slate.map((g) => [g.game_id, g]))
      return s.players
        .filter((p) => p.name)
        .map((p) => {
          let correct = 0
          let games = 0
          let points = 0
          for (const [k, v] of Object.entries(s.picks)) {
            const [pid, gid] = k.split(':')
            if (Number(pid) !== p.id) continue
            const g = byId[Number(gid)]
            if (!g?.winner_abbr) continue
            games += 1
            if (v.pick === g.winner_abbr) {
              correct += 1
              points += v.confidence
            }
          }
          return {
            player_id: p.id,
            player_name: p.name,
            player_color: p.color,
            weeks_played: games ? 1 : 0,
            correct,
            games,
            points,
          }
        })
        .sort((a, b) => b.points - a.points || b.correct - a.correct)
    }

    case 'save_picks': {
      const me = requireMe(args.p_token)
      const w = await week()
      const sent = args.p_picks || []
      const n = w.slate.length

      if (sent.length !== n) fail(`Expected ${n} picks, got ${sent.length}`)
      if (new Set(sent.map((p) => p.game_id)).size !== n)
        fail('The same game was submitted twice')
      const confs = sent.map((p) => p.confidence).sort((a, b) => a - b)
      if (confs.some((c, i) => c !== i + 1))
        fail(`Confidence must use every value from 1 to ${n} exactly once`)

      const byId = Object.fromEntries(w.slate.map((g) => [g.game_id, g]))
      for (const p of sent) {
        const g = byId[p.game_id]
        if (!g) fail('A submitted game is not on this week’s slate')
        if (![g.home_abbr, g.away_abbr].includes(p.pick))
          fail('A pick is not one of the two teams in that game')
      }

      let locked = 0
      for (const p of sent) {
        const g = byId[p.game_id]
        if (!kicked(g)) continue
        locked += 1
        const held = s.picks[`${me.id}:${p.game_id}`]
        if (!held) fail(`Game ${p.game_id} already kicked off and has no pick to keep`)
        if (held.pick !== p.pick || held.confidence !== p.confidence)
          fail(`Game ${p.game_id} is locked and cannot be changed`)
      }

      let saved = 0
      for (const p of sent) {
        if (kicked(byId[p.game_id])) continue
        s.picks[`${me.id}:${p.game_id}`] = {
          pick: p.pick,
          confidence: p.confidence,
          auto: false,
        }
        saved += 1
      }
      save()
      return [{ saved, locked }]
    }

    case 'get_pool': {
      // Admin-only view of the pool, which is every FBS game in the week. The real
      // backend exposes this through get_slate on an unpublished week; the mock keeps
      // it simple.
      const me = requireMe(args.p_token)
      if (!me.is_admin) fail('Only an admin can see the pool')
      const w = await week()
      return [
        ...w.slate.map((g) => ({ ...g, in_slate: true, locked: kicked(g) })),
        ...w.alternates.map((g) => ({ ...g, in_slate: false, locked: kicked(g) })),
      ].sort((a, b) => new Date(a.kickoff) - new Date(b.kickoff))
    }

    case 'publish_slate': {
      const me = requireMe(args.p_token)
      if (!me.is_admin) fail('Only an admin can publish the slate')
      const ids = args.p_game_ids || []
      if (ids.length !== 20) fail(`A slate must be exactly 20 games, got ${ids.length}`)
      const w = await week()
      const pool = [...w.slate, ...w.alternates]
      if (pool.some((g) => ids.includes(g.game_id) && kicked(g) && !w.slate.some((x) => x.game_id === g.game_id)))
        fail('Cannot add a game that already kicked off')
      w.slate = ids.map((id) => pool.find((g) => g.game_id === id)).filter(Boolean)
      w.alternates = pool.filter((g) => !ids.includes(g.game_id))
      return 20
    }

    default:
      fail(`Mock has no implementation for ${fn}`)
  }
}

/** Demo helper: wipe the mock so the seat-claim flow can be replayed. */
export function resetMock() {
  cache = null
  weekCache = null
  try {
    localStorage.removeItem(KEY)
    localStorage.removeItem('pickem.token')
    localStorage.removeItem('pickem.draft.v1')
  } catch {
    /* ignore */
  }
}
