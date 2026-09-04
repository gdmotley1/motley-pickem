-- Can anything outside Postgres tell whether the auto-pick job is actually scheduled?
-- Until this file, no.
--
-- Paste into the Supabase SQL Editor. Safe to re-run. Read-only.
--
-- Migration 005 moved auto-picks onto pg_cron because GitHub does not honour the
-- schedule it is given. Measured on 2026-09-04 across the workflow's entire run
-- history: it asks for every 15 minutes Thursday through Sunday, and the six scheduled
-- runs on record are 1.7 to 4.5 hours apart, a median gap of 262 minutes. So pg_cron is
-- the load-bearing path and the GitHub job is the backstop, not the other way round.
--
-- That makes "is the cron job alive?" a question worth being able to ask, and it was
-- unanswerable from here. PostgREST exposes only the public schema, so cron.job is
-- unreachable; the service key is a PostgREST credential rather than a Postgres login,
-- so psql is not an option; SUPABASE_DB_PASSWORD is empty; and the dashboard MCP is
-- attached to Grant's other, paid account. The only route was opening the SQL editor by
-- hand, which is exactly why it went unchecked from the day 005 shipped.
--
-- If this returns no row, auto-picks are NOT running and a player who misses a kickoff
-- cannot submit at all until the GitHub job catches up, which the numbers above say can
-- be four hours: the client posts the locked game with a null confidence and save_picks
-- rejects the whole payload with "Confidence must use every value from 1 to 20".

create or replace function cron_health(p_token text default null)
returns table (jobname text, schedule text, active boolean,
               last_start timestamptz, last_status text, minutes_ago numeric)
language plpgsql stable security definer set search_path = public, extensions as $$
declare
  me players;
  caller text := coalesce(
    nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role', '');
begin
  -- The sync job calls this as service_role and has no player token. A human calling
  -- from the app has a token and must be an admin. Anyone else is refused, because the
  -- schedule of a privileged job is not player-facing information.
  if caller <> 'service_role' then
    me := _player_for(p_token);
    if me.id is null or not me.is_admin then
      raise exception 'Admins only';
    end if;
  end if;

  return query
    select j.jobname::text, j.schedule::text, j.active,
           d.start_time, d.status::text,
           round(extract(epoch from (now() - d.start_time)) / 60.0, 1)
      from cron.job j
      left join lateral (
        select r.start_time, r.status
          from cron.job_run_details r
         where r.jobid = j.jobid
         order by r.start_time desc
         limit 1) d on true
     order by j.jobname;
end $$;

revoke all on function cron_health(text) from public;
grant execute on function cron_health(text) to anon, authenticated, service_role;
