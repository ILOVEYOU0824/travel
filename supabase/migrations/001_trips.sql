-- JapanTrip: trips + RLS
-- Supabase SQL Editor 또는 CLI로 실행

create extension if not exists "pgcrypto";

create table if not exists public.trips (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid references auth.users (id) on delete set null,
  title text not null default '내 일본 여행',
  itinerary jsonb not null default '[]'::jsonb,
  meta jsonb not null default '{}'::jsonb,
  is_public boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  expires_at timestamptz
);

create index if not exists trips_owner_updated_idx
  on public.trips (owner_id, updated_at desc);

create index if not exists trips_public_idx
  on public.trips (is_public)
  where is_public = true;

alter table public.trips enable row level security;

-- 공개 일정: 누구나 읽기
drop policy if exists "trips_public_select" on public.trips;
create policy "trips_public_select"
  on public.trips
  for select
  using (is_public = true);

-- 소유자: 본인 일정 전체 읽기 (비공개 포함)
drop policy if exists "trips_owner_select" on public.trips;
create policy "trips_owner_select"
  on public.trips
  for select
  using (auth.uid() = owner_id);

drop policy if exists "trips_owner_insert" on public.trips;
create policy "trips_owner_insert"
  on public.trips
  for insert
  with check (auth.uid() = owner_id or owner_id is null);

drop policy if exists "trips_owner_update" on public.trips;
create policy "trips_owner_update"
  on public.trips
  for update
  using (auth.uid() = owner_id)
  with check (auth.uid() = owner_id);

drop policy if exists "trips_owner_delete" on public.trips;
create policy "trips_owner_delete"
  on public.trips
  for delete
  using (auth.uid() = owner_id);

-- updated_at 자동 갱신
create or replace function public.set_trips_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trips_set_updated_at on public.trips;
create trigger trips_set_updated_at
  before update on public.trips
  for each row
  execute function public.set_trips_updated_at();
