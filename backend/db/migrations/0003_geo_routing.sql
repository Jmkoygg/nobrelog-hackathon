-- NobreLOG — camada de geografia e roteamento real.
-- "Eixo" deixa de ser regra dura do motor: vira so agrupamento de
-- referencia. O motor de rotas decide livremente veiculo->pedidos->ordem
-- usando coordenadas e distancia real de estrada (OSRM), guardadas em
-- cache para a demonstracao nao depender de internet ao vivo.

create table public.cities (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  name text not null,
  lat double precision not null,
  lng double precision not null,
  is_depot boolean not null default false,
  source text not null default 'nominatim',
  created_at timestamptz not null default now(),
  unique (org_id, name)
);

create table public.city_distances (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  from_city_id uuid not null references public.cities(id) on delete cascade,
  to_city_id uuid not null references public.cities(id) on delete cascade,
  distance_km numeric(10,3) not null,
  duration_min numeric(10,2) not null,
  source text not null default 'osrm',
  computed_at timestamptz not null default now(),
  unique (org_id, from_city_id, to_city_id)
);

alter table public.cities enable row level security;
alter table public.city_distances enable row level security;

create policy cities_select on public.cities for select using (public.is_org_member(org_id));
create policy cities_insert on public.cities for insert with check (public.is_org_member(org_id));
create policy cities_update on public.cities for update using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
create policy cities_delete on public.cities for delete using (public.is_org_member(org_id));

create policy city_distances_select on public.city_distances for select using (public.is_org_member(org_id));
create policy city_distances_insert on public.city_distances for insert with check (public.is_org_member(org_id));
create policy city_distances_update on public.city_distances for update using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
create policy city_distances_delete on public.city_distances for delete using (public.is_org_member(org_id));

create index city_distances_from_idx on public.city_distances (org_id, from_city_id);
