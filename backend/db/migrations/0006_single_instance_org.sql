-- MVP de instancia unica: nao existe mais tela de "criar/entrar em
-- organizacao". Todo usuario que faz login entra automaticamente na
-- (unica) organizacao da operacao — cria se ainda nao existir, junta se
-- ja existir. RLS e isolamento por org continuam intactos (nao custa
-- nada manter, e protege se um dia precisar de mais de uma org de novo).

create or replace function public.auto_join_organization()
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  target_org uuid;
begin
  select org_id into target_org from public.memberships where user_id = auth.uid() limit 1;
  if target_org is not null then
    return target_org;
  end if;

  select id into target_org from public.organizations order by created_at limit 1;

  if target_org is null then
    insert into public.organizations (name, created_by)
    values ('Grupo Nobre', auth.uid())
    returning id into target_org;

    insert into public.memberships (user_id, org_id, role)
    values (auth.uid(), target_org, 'owner');
  else
    insert into public.memberships (user_id, org_id, role)
    values (auth.uid(), target_org, 'member');
  end if;

  return target_org;
end;
$$;
