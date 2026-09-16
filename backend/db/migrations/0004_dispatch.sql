-- NobreLOG — despacho multi-veiculo (VRP): substitui a nocao de "um plano
-- = um eixo + um veiculo" por "uma rodada = N veiculos, rotas livres".
-- O plano single-axis (tabela plans) continua existindo como caminho
-- garantido; isto e' uma camada nova, nao uma substituicao destrutiva.

create table public.dispatch_runs (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  batch_id uuid not null references public.import_batches(id),
  mode text not null check (mode in ('simulacao_historica', 'operacao')),
  status text not null default 'draft' check (status in ('draft', 'issued', 'cancelled')),
  solver_status text,
  solver_wall_time_ms int,
  total_distance_km numeric(12,2),
  total_duration_min numeric(12,2),
  total_value numeric(14,2),
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now(),
  issued_at timestamptz
);

create table public.dispatch_assignments (
  id uuid primary key default gen_random_uuid(),
  dispatch_run_id uuid not null references public.dispatch_runs(id) on delete cascade,
  org_id uuid not null references public.organizations(id) on delete cascade,
  order_id uuid not null references public.orders(id),
  vehicle_id uuid references public.vehicles(id),
  city text,
  stop_sequence int,
  leg_distance_km numeric(10,3),
  value numeric(14,2),
  weight_kg numeric(14,4),
  volume_m3 numeric(14,6),
  selected boolean not null default true,
  rejection_reason text
);

alter table public.dispatch_runs enable row level security;
alter table public.dispatch_assignments enable row level security;

create policy dispatch_runs_select on public.dispatch_runs for select using (public.is_org_member(org_id));
create policy dispatch_runs_insert on public.dispatch_runs for insert with check (public.is_org_member(org_id));
create policy dispatch_runs_update on public.dispatch_runs for update using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
create policy dispatch_runs_delete on public.dispatch_runs for delete using (public.is_org_member(org_id));

create policy dispatch_assignments_select on public.dispatch_assignments for select using (public.is_org_member(org_id));
create policy dispatch_assignments_insert on public.dispatch_assignments for insert with check (public.is_org_member(org_id));
create policy dispatch_assignments_update on public.dispatch_assignments for update using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
create policy dispatch_assignments_delete on public.dispatch_assignments for delete using (public.is_org_member(org_id));

create index dispatch_assignments_run_idx on public.dispatch_assignments (dispatch_run_id);
