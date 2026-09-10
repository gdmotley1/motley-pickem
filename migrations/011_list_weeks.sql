-- The Week tab can step back through previous weeks, and nothing lists the weeks.
--
-- Paste into the Supabase SQL Editor. Safe to re-run. Read-only.
--
-- get_week returns one week by id and get_current_week returns the one now falls inside.
-- Neither can answer "which weeks are there, and which are worth visiting", which is what
-- both the arrows and the jump-to-a-week sheet need.
--
-- get_season looks like it would do, and does not: it returns week_no but no week id, and
-- the slate is loaded by id. Ids happen to equal week numbers today because seed_weeks.py
-- created all fifteen in order, and building navigation on that coincidence would break
-- silently the first time a week is ever inserted out of order. This returns both.
--
-- `graded` is what lets the sheet grey out a week with nothing to show, and `published`
-- is what lets it say "not published" for a week Dad has not opened yet, rather than
-- showing four zeroes.
--
-- Visibility: weeks carry no picks, so there is nothing here to leak. The one rule that
-- outranks everything is enforced in get_board, and this function returns no pick at all.

create or replace function list_weeks(p_token text)
returns table (
  id int, season smallint, week_no smallint, label text, published boolean,
  starts_at timestamptz, ends_at timestamptz, slate_size bigint, graded bigint
) language plpgsql stable security definer set search_path = public, extensions as $$
declare me players;
begin
  me := _player_for(p_token);
  if me.id is null then raise exception 'Not signed in'; end if;
  return query
    select w.id, w.season, w.week_no, w.label, w.published, w.starts_at, w.ends_at,
           (select count(*) from games g
             where g.week_id = w.id and g.in_slate),
           (select count(*) from games g
             where g.week_id = w.id and g.in_slate and g.winner_abbr is not null)
      from weeks w
     where w.season = (select max(w2.season) from weeks w2)
     order by w.week_no;
end $$;

revoke all on function list_weeks(text) from public;
grant execute on function list_weeks(text) to anon, authenticated;
