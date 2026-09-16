-- Reserva agora pode vir de um plano single-axis OU de uma rodada de
-- despacho multi-veiculo — exatamente uma das duas, nunca as duas nem
-- nenhuma. O indice unico por pedido ativo (da migration 0001) continua
-- garantindo que um pedido nunca tenha duas reservas ativas ao mesmo
-- tempo, venha ela de qual fluxo vier.

alter table public.reservations
  alter column plan_id drop not null,
  add column dispatch_run_id uuid references public.dispatch_runs(id),
  add constraint reservations_source_check check (
    (plan_id is not null and dispatch_run_id is null) or
    (plan_id is null and dispatch_run_id is not null)
  );
