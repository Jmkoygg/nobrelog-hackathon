-- NobreLOG — schema inicial
-- Multi-tenant por organizacao. Nenhuma capacidade de veiculo, produto,
-- cidade ou periodo fica fixa em codigo: tudo aqui e dado editavel.

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------
-- Organizacoes e membros
-- ---------------------------------------------------------------------

create table public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now()
);

create table public.memberships (
  user_id uuid not null references auth.users(id) on delete cascade,
  org_id uuid not null references public.organizations(id) on delete cascade,
  role text not null default 'member' check (role in ('owner', 'member')),
  created_at timestamptz not null default now(),
  primary key (user_id, org_id)
);

create table public.org_invites (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  code text not null unique,
  created_by uuid not null references auth.users(id),
  used_by uuid references auth.users(id),
  used_at timestamptz,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null default (now() + interval '7 days')
);

-- ---------------------------------------------------------------------
-- Cadastros editaveis: frota, eixos, produtos
-- ---------------------------------------------------------------------

create table public.vehicles (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  name text not null,
  capacity_kg numeric(12,3) not null check (capacity_kg > 0),
  capacity_m3 numeric(12,6) not null check (capacity_m3 > 0),
  active boolean not null default true,
  source text,
  spec_date date,
  version int not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.axes (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  name text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.axis_cities (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  axis_id uuid not null references public.axes(id) on delete cascade,
  city_name text not null,
  city_aliases text[] not null default '{}',
  sort_order int not null default 0,
  created_at timestamptz not null default now(),
  unique (org_id, city_name)
);

create table public.products (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  code text not null,
  description text,
  sale_unit text,
  load_unit text,
  conversion_factor numeric(14,6),
  weight_kg numeric(12,4),
  volume_m3 numeric(12,6),
  weight_range_min numeric(12,4),
  weight_range_max numeric(12,4),
  volume_range_min numeric(12,6),
  volume_range_max numeric(12,6),
  source text,
  is_estimated boolean not null default false,
  version int not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (org_id, code)
);

-- ---------------------------------------------------------------------
-- Importacao
-- ---------------------------------------------------------------------

create table public.import_batches (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  file_hash text not null,
  filename text not null,
  mode text not null check (mode in ('simulacao_historica', 'operacao')),
  reference_date date,
  status text not null default 'processing' check (status in ('processing', 'done', 'failed')),
  summary jsonb not null default '{}'::jsonb,
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now(),
  unique (org_id, file_hash)
);

create table public.raw_rows (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  batch_id uuid not null references public.import_batches(id) on delete cascade,
  row_number int not null,
  raw_data jsonb not null
);

-- ---------------------------------------------------------------------
-- Pedidos
-- ---------------------------------------------------------------------

create table public.orders (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  batch_id uuid not null references public.import_batches(id) on delete cascade,
  external_id text not null,
  mode text not null check (mode in ('simulacao_historica', 'operacao')),
  city text,
  axis_id uuid references public.axes(id),
  logistics_status text,
  order_status text,
  order_date date,
  order_date_raw text,
  order_date_flagged boolean not null default false,
  delivered boolean not null default false,
  value numeric(14,2),
  excluded_reason text,
  weight_kg numeric(14,4),
  volume_m3 numeric(14,6),
  data_status text not null default 'pending' check (data_status in ('ready', 'pending', 'excluded')),
  created_at timestamptz not null default now(),
  unique (org_id, batch_id, external_id)
);

create table public.order_items (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  order_id uuid not null references public.orders(id) on delete cascade,
  product_code text not null,
  description text,
  quantity numeric(14,4) not null,
  unit text,
  matched_product_id uuid references public.products(id),
  computed_weight_kg numeric(14,4),
  computed_volume_m3 numeric(14,6),
  conversion_note text,
  created_at timestamptz not null default now()
);

create table public.issues (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  order_id uuid references public.orders(id) on delete cascade,
  product_code text,
  issue_type text not null check (issue_type in (
    'produto_sem_ficha', 'unidade_ausente', 'cidade_sem_eixo',
    'data_inconsistente', 'saldo_parcial_desconhecido', 'conversao_ambigua'
  )),
  description text not null,
  status text not null default 'open' check (status in ('open', 'resolved')),
  resolution jsonb,
  resolved_by uuid references auth.users(id),
  resolved_at timestamptz,
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- Planos de carga (romaneio) e reservas
-- ---------------------------------------------------------------------

create table public.plans (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  axis_id uuid not null references public.axes(id),
  vehicle_id uuid not null references public.vehicles(id),
  batch_id uuid not null references public.import_batches(id),
  mode text not null check (mode in ('simulacao_historica', 'operacao')),
  status text not null default 'draft' check (status in ('draft', 'issued', 'cancelled', 'completed')),
  objective_policy text not null default 'ocupacao_media_kg_m3',
  solver_status text,
  solver_wall_time_ms int,
  solver_seed int,
  solver_workers int,
  input_versions jsonb not null default '{}'::jsonb,
  snapshot jsonb not null default '{}'::jsonb,
  total_weight_kg numeric(14,4),
  total_volume_m3 numeric(14,6),
  total_value numeric(14,2),
  revision int not null default 1,
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now(),
  issued_at timestamptz,
  cancelled_at timestamptz,
  completed_at timestamptz
);

create table public.plan_orders (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  plan_id uuid not null references public.plans(id) on delete cascade,
  order_id uuid not null references public.orders(id),
  selected boolean not null,
  rejection_reason text,
  city text,
  stop_sequence int,
  value numeric(14,2),
  weight_kg numeric(14,4),
  volume_m3 numeric(14,6)
);

create table public.reservations (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  order_id uuid not null references public.orders(id),
  plan_id uuid not null references public.plans(id),
  status text not null default 'active' check (status in ('active', 'released')),
  created_at timestamptz not null default now(),
  released_at timestamptz
);

-- Um pedido so pode ter uma reserva ativa por vez (impede dupla alocacao operacional).
create unique index reservations_one_active_per_order
  on public.reservations (order_id)
  where status = 'active';

create index orders_org_batch_idx on public.orders (org_id, batch_id);
create index orders_axis_idx on public.orders (org_id, axis_id);
create index order_items_order_idx on public.order_items (order_id);
create index issues_org_status_idx on public.issues (org_id, status);
create index plans_org_axis_idx on public.plans (org_id, axis_id, status);
