-- Unifica "cidades" (coordenadas, usadas pelo despacho) e "eixos/cidades"
-- (agrupamento, usado pela importacao) num so cadastro. Eram duas tabelas
-- desconectadas por engano — o time notou a estranheza e pediu pra juntar.
-- Uma cidade agora pode (ou nao) pertencer a um eixo, e pode (ou nao) ter
-- coordenada ainda — as duas coisas sao independentes e opcionais.

alter table public.cities
  add column axis_id uuid references public.axes(id),
  add column sort_order int not null default 0,
  add column city_aliases text[] not null default '{}',
  alter column lat drop not null,
  alter column lng drop not null;

-- Merge por nome tem que ignorar acento/maiuscula — o CSV da operacao
-- grava cidade em CAIXA ALTA sem acento; o cadastro/geocoding grava nome
-- proprio com acento. Sem normalizar aqui, "ARARENDA" e "Ararendá" viram
-- duas linhas em vez de uma (foi exatamente o que aconteceu na primeira
-- tentativa desta migration — corrigido usando a extensao unaccent).
create extension if not exists unaccent;

insert into public.cities (org_id, name, axis_id, sort_order, is_depot)
select ac.org_id, ac.city_name, ac.axis_id, ac.sort_order, false
from public.axis_cities ac
on conflict (org_id, name) do update
  set axis_id = excluded.axis_id, sort_order = excluded.sort_order
where public.unaccent(upper(cities.name)) = public.unaccent(upper(excluded.name));

-- pares que so batem ignorando acento/caixa viram update manual (poucos,
-- resolvidos linha a linha porque ON CONFLICT so dispara em match exato
-- de (org_id, name), nao em match normalizado).
update public.cities acc
set axis_id = ac.axis_id, sort_order = ac.sort_order
from public.axis_cities ac
where public.unaccent(upper(acc.name)) = public.unaccent(upper(ac.city_name))
  and acc.name != ac.city_name;

delete from public.cities c
using public.axis_cities ac
where c.name = ac.city_name
  and public.unaccent(upper(c.name)) in (
    select public.unaccent(upper(name)) from public.cities group by public.unaccent(upper(name)) having count(*) > 1
  )
  and c.lat is null;

drop table public.axis_cities;

create index cities_axis_idx on public.cities (org_id, axis_id);
