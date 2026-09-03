-- Week metadata for the app header.
-- Paste into the Supabase SQL Editor after 002. Safe to re-run.
--
-- Week numbers follow ESPN's published college football calendar rather than a
-- Monday-to-Sunday guess. Boundaries land about 3am ET Monday, so a Thursday game
-- belongs to the week that opened the previous Monday, and Week 1 of 2026 is a
-- seventeen-day window because it absorbs Week 0. See scripts/cfb_weeks.py.

alter table weeks add column if not exists starts_at timestamptz;
alter table weeks add column if not exists ends_at   timestamptz;

create or replace function get_week(p_token text, p_week int)
returns table (
  id int, season smallint, week_no smallint, label text,
  published boolean, starts_at timestamptz, ends_at timestamptz,
  slate_size bigint
) language plpgsql stable security definer set search_path = public as $$
declare me players;
begin
  me := _player_for(p_token);
  if me.id is null then raise exception 'Not signed in'; end if;
  return query
    select w.id, w.season, w.week_no, w.label, w.published, w.starts_at, w.ends_at,
           (select count(*) from games g where g.week_id = w.id and g.in_slate)
      from weeks w
     where w.id = p_week;
end $$;

-- The week currently in progress, so the app does not have to know an id up front.
create or replace function get_current_week(p_token text)
returns table (
  id int, season smallint, week_no smallint, label text,
  published boolean, starts_at timestamptz, ends_at timestamptz,
  slate_size bigint
) language plpgsql stable security definer set search_path = public as $$
declare me players;
begin
  me := _player_for(p_token);
  if me.id is null then raise exception 'Not signed in'; end if;
  return query
    select w.id, w.season, w.week_no, w.label, w.published, w.starts_at, w.ends_at,
           (select count(*) from games g where g.week_id = w.id and g.in_slate)
      from weeks w
     where now() between coalesce(w.starts_at, '-infinity'::timestamptz)
                     and coalesce(w.ends_at, 'infinity'::timestamptz)
     order by w.season desc, w.week_no desc
     limit 1;
end $$;

revoke all on function get_week(text, int)      from public;
revoke all on function get_current_week(text)   from public;
grant execute on function get_week(text, int)    to anon, authenticated;
grant execute on function get_current_week(text) to anon, authenticated;
