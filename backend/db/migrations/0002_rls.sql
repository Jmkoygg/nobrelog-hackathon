-- NobreLOG — RLS: isolamento por organizacao.
-- Ninguem le ou escreve linha de outra organizacao, nem se auto-associa
-- a uma organizacao livremente. auth.uid() vem do JWT validado pelo
-- proprio Postgres/PostgREST (Supabase) a partir do token do usuario.

create or replace function public.is_org_member(target_org uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.memberships m
    where m.user_id = auth.uid() and m.org_id = target_org
  );
$$;

create or replace function public.is_org_owner(target_org uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.memberships m
    where m.user_id = auth.uid() and m.org_id = target_org and m.role = 'owner'
  );
$$;

-- Cria uma organizacao nova e torna o chamador owner. E o unico jeito
-- de ganhar a primeira membership — nao existe policy de insert direta
-- em memberships para usuarios comuns.
create or replace function public.bootstrap_organization(org_name text)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  new_org_id uuid;
begin
  if exists (select 1 from public.memberships where user_id = auth.uid()) then
    raise exception 'Usuario ja pertence a uma organizacao';
  end if;

  insert into public.organizations (name, created_by)
  values (org_name, auth.uid())
  returning id into new_org_id;

  insert into public.memberships (user_id, org_id, role)
  values (auth.uid(), new_org_id, 'owner');

  return new_org_id;
end;
$$;

create or replace function public.create_org_invite(target_org uuid)
returns text
language plpgsql
security definer
set search_path = public
as $$
declare
  new_code text;
begin
  if not public.is_org_owner(target_org) then
    raise exception 'Somente o owner pode criar convites';
  end if;

  new_code := encode(gen_random_bytes(6), 'hex');

  insert into public.org_invites (org_id, code, created_by)
  values (target_org, new_code, auth.uid());

  return new_code;
end;
$$;

create or replace function public.accept_org_invite(invite_code text)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  invite record;
begin
  if exists (select 1 from public.memberships where user_id = auth.uid()) then
    raise exception 'Usuario ja pertence a uma organizacao';
  end if;

  select * into invite from public.org_invites
    where code = invite_code and used_by is null and expires_at > now()
    for update;

  if invite is null then
    raise exception 'Convite invalido ou expirado';
  end if;

  update public.org_invites
    set used_by = auth.uid(), used_at = now()
    where id = invite.id;

  insert into public.memberships (user_id, org_id, role)
  values (auth.uid(), invite.org_id, 'member');

  return invite.org_id;
end;
$$;

-- ---------------------------------------------------------------------
-- Ativa RLS em toda tabela com dado de organizacao
-- ---------------------------------------------------------------------

alter table public.organizations enable row level security;
alter table public.memberships enable row level security;
alter table public.org_invites enable row level security;
alter table public.vehicles enable row level security;
alter table public.axes enable row level security;
alter table public.axis_cities enable row level security;
alter table public.products enable row level security;
alter table public.import_batches enable row level security;
alter table public.raw_rows enable row level security;
alter table public.orders enable row level security;
alter table public.order_items enable row level security;
alter table public.issues enable row level security;
alter table public.plans enable row level security;
alter table public.plan_orders enable row level security;
alter table public.reservations enable row level security;

-- organizations: membro le a propria org; ninguem insere direto (usa bootstrap_organization)
create policy org_select on public.organizations
  for select using (public.is_org_member(id));

-- memberships: cada um le suas proprias linhas de membership
create policy membership_select on public.memberships
  for select using (user_id = auth.uid());

-- org_invites: so o owner ve os convites da propria org
create policy invite_select on public.org_invites
  for select using (public.is_org_owner(org_id));

-- Padrao repetido para toda tabela org-scoped: select/insert/update/delete
-- restritos a quem tem membership na organizacao da linha.
do $$
declare
  t text;
begin
  foreach t in array array[
    'vehicles', 'axes', 'axis_cities', 'products',
    'import_batches', 'raw_rows', 'orders', 'order_items',
    'issues', 'plans', 'plan_orders', 'reservations'
  ]
  loop
    execute format($f$
      create policy %1$I_select on public.%1$I
        for select using (public.is_org_member(org_id));
      create policy %1$I_insert on public.%1$I
        for insert with check (public.is_org_member(org_id));
      create policy %1$I_update on public.%1$I
        for update using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
      create policy %1$I_delete on public.%1$I
        for delete using (public.is_org_member(org_id));
    $f$, t);
  end loop;
end $$;
