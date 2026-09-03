-- Fix: whoami was declared STABLE but writes.
-- Paste into the Supabase SQL Editor. Safe to re-run.
--
-- It touches sessions.last_seen, and Postgres accepts the definition then refuses at
-- call time with:
--     ERROR: 0A000: UPDATE is not allowed in a non-volatile function
-- which broke sign-in entirely: the seat was claimed, whoami failed, and the app could
-- not start a session. Dropping STABLE (the default is VOLATILE) is the fix; the touch
-- is worth keeping so an idle session can be spotted later.

create or replace function whoami(p_token text)
returns table (id smallint, name text, is_admin boolean, color text)
language plpgsql security definer set search_path = public, extensions as $$
declare me players;
begin
  me := _player_for(p_token);
  if me.id is null then raise exception 'Not signed in'; end if;
  update sessions set last_seen = now()
    where token_hash = encode(digest(p_token, 'sha256'), 'hex');
  return query select me.id, me.name, me.is_admin, me.color;
end $$;

revoke all on function whoami(text) from public;
grant execute on function whoami(text) to anon, authenticated;
