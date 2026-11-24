-- Run once in the Supabase SQL Editor, in a dedicated project.
create table if not exists public.hunt_submissions (
  id bigint generated always as identity primary key,
  team smallint not null check (team between 0 and 3),
  stop smallint not null check (stop between 0 and 7),
  note text not null check (length(note) between 1 and 1500),
  status text not null check (status in ('pending','approved','rejected')),
  feedback text not null default '' check (length(feedback) <= 500),
  image text not null check (length(image) between 20 and 2200000),
  updated bigint not null,
  unique (team,stop)
);
alter table public.hunt_submissions enable row level security;
revoke all on table public.hunt_submissions from public, anon, authenticated;
grant select, insert, update, delete on table public.hunt_submissions to service_role;
grant usage, select on sequence public.hunt_submissions_id_seq to service_role;

-- Server-only RPC: atomic route enforcement and resubmission.
create or replace function public.hunt_submit(p_team integer, p_stop integer, p_note text, p_image text)
returns boolean language plpgsql security invoker set search_path = public as $$
declare
  starts integer[] := array[0,2,4,6];
  s integer;
  existing_status text;
begin
  if p_team not between 0 and 3 or p_stop not between 0 and 7 or
     p_note is null or length(trim(p_note)) not between 1 and 1500 or
     p_image is null or length(p_image) not between 20 and 2200000 then
    raise exception 'Invalid submission.';
  end if;
  perform pg_advisory_xact_lock(765434, p_team);
  for i in 0..7 loop
    s := (starts[p_team+1]+i) % 8;
    exit when s = p_stop;
    if not exists (select 1 from public.hunt_submissions where team=p_team and stop=s and status='approved') then
      raise exception 'Earlier challenge needs approval.';
    end if;
  end loop;
  select status into existing_status from public.hunt_submissions where team=p_team and stop=p_stop;
  if existing_status in ('pending','approved') then
    raise exception 'This challenge is already submitted.';
  end if;
  insert into public.hunt_submissions(team, stop, note, status, feedback, image, updated)
  values(p_team,p_stop,trim(p_note),'pending','',p_image,(extract(epoch from clock_timestamp())*1000)::bigint)
  on conflict(team,stop) do update set note=excluded.note, status='pending', feedback='', image=excluded.image, updated=excluded.updated;
  return true;
end $$;

create or replace function public.hunt_review(p_id bigint, p_decision text, p_feedback text)
returns boolean language plpgsql security invoker set search_path = public as $$
declare affected integer;
begin
  if p_decision not in ('approved','rejected') or length(coalesce(p_feedback,''))>500 or (p_decision='rejected' and length(trim(coalesce(p_feedback,'')))=0) then
    raise exception 'Invalid submission.';
  end if;
  update public.hunt_submissions set status=p_decision, feedback=coalesce(p_feedback,''), updated=(extract(epoch from clock_timestamp())*1000)::bigint where id=p_id and status='pending';
  get diagnostics affected = row_count;
  return affected > 0;
end $$;
revoke all on function public.hunt_submit(integer,integer,text,text) from public, anon, authenticated;
revoke all on function public.hunt_review(bigint,text,text) from public, anon, authenticated;
grant execute on function public.hunt_submit(integer,integer,text,text) to service_role;
grant execute on function public.hunt_review(bigint,text,text) to service_role;

-- ============================================================================
-- LIVE SCOREBOARD (scoreboard.html / tiny-app.js)
-- Tables for the 5-team Golden Gelato Goblet hunt: a guild roster and a
-- stream of score events. The scoreboard reads these from the browser with
-- the PUBLIC anon key, so RLS allows anon to read teams and to read/insert/
-- update/delete score events. That is intentional for a trusted, small
-- event: anyone with the link can award points. Never put your secret key
-- in HTML. This section is idempotent and mirrors the structure already
-- live in the demo project, so re-running the whole file is safe.
-- ============================================================================

create table if not exists public.teams (
  id text primary key,
  name text not null,
  color text not null default '#0f8a8a',
  mascot text not null default '',
  god text not null default '',
  chant text not null default '',
  created_at timestamptz not null default now()
);

create table if not exists public.score_events (
  id uuid primary key default gen_random_uuid(),
  team_id text not null references public.teams(id) on delete cascade,
  stop_number integer check (stop_number between 1 and 18),
  points integer not null default 0,
  description text,
  created_at timestamptz not null default now()
);
create index if not exists score_events_created_idx on public.score_events (created_at desc);

alter table public.teams enable row level security;
alter table public.score_events enable row level security;
drop policy if exists "public read teams" on public.teams;
drop policy if exists "public insert teams" on public.teams;
drop policy if exists "public read score_events" on public.score_events;
drop policy if exists "public insert score_events" on public.score_events;
drop policy if exists "public update score_events" on public.score_events;
drop policy if exists "public delete score_events" on public.score_events;
create policy "public read teams"        on public.teams        for select using (true);
create policy "public insert teams"      on public.teams        for insert with check (true);
create policy "public read score_events" on public.score_events for select using (true);
create policy "public insert score_events" on public.score_events for insert with check (true);
create policy "public update score_events" on public.score_events for update using (true);
create policy "public delete score_events" on public.score_events for delete using (true);

grant select, insert on public.teams to anon, authenticated;
grant select, insert, update, delete on public.score_events to anon, authenticated;

-- Seed the five guilds (safe to re-run: existing rows are skipped by id).
insert into public.teams (id, name, color, mascot, god, chant) values
  ('sapphire_scarabs', 'Sapphire Scarabs', '#2b6cb0', 'Scarab beetle', 'Khepri',  'Roll it, roll it, scarab style — we shine bluer than the Nile!'),
  ('crimson_cobras',   'Crimson Cobras',   '#c0392b', 'Cobra',         'Wadjet',  'Hiss, snap, strike — red cobras never strike out!'),
  ('emerald_ibises',   'Emerald Ibises',   '#2e8b57', 'Ibis',          'Thoth',   'Quill and beak, we''re super wise — Emerald Ibises win the prize!'),
  ('golden_jackals',   'Golden Jackals',   '#e0a800', 'Jackal',        'Anubis',  'Anubis guide, jackals gold — we sniff out treats like legends told!'),
  ('violet_vultures',  'Violet Vultures',  '#7d3c98', 'Vulture',       'Nekhbet', 'Circle high, swoop down low — Violet Vultures steal the show!')
on conflict (id) do nothing;
