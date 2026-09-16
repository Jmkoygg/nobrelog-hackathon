import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
import type { Plan, PlanOrderRow } from "../types";

const money = (v: number) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export function RomaneioPage() {
  const { planId } = useParams<{ planId: string }>();
  const [plan, setPlan] = useState<Plan | null>(null);
  const [orders, setOrders] = useState<PlanOrderRow[]>([]);

  useEffect(() => {
    if (!planId) return;
    api.get<{ plan: Plan; orders: PlanOrderRow[] }>(`/plans/${planId}`).then((data) => {
      setPlan(data.plan);
      setOrders(data.orders.filter((o) => o.selected).sort((a, b) => (a.stop_sequence || 0) - (b.stop_sequence || 0)));
    });
  }, [planId]);

  if (!plan) return <p style={{ padding: 40 }}>Carregando romaneio…</p>;

  const totalValue = orders.reduce((a, o) => a + Number(o.value), 0);

  return (
    <div>
      <header className="page-header no-print">
        <div>
          <div className="eyebrow">Documento de expedição</div>
          <h1>Plano de carga.</h1>
        </div>
        <button className="btn primary" onClick={() => window.print()}>Imprimir / salvar PDF</button>
      </header>

      <div className="paper">
        <div className="paper-top">
          <div>
            <div className="brand" style={{ color: "var(--green)" }}>NobreLOG</div>
            <h1>Plano de carga</h1>
            <div>{plan.vehicles?.name} · {Number(plan.total_weight_kg).toLocaleString("pt-BR")} kg / {Number(plan.total_volume_m3).toLocaleString("pt-BR", { maximumFractionDigits: 3 })} m³</div>
          </div>
          <div style={{ textAlign: "right", fontSize: 12 }}>
            Plano {plan.id.slice(0, 8)}
            <br />
            {plan.status.toUpperCase()}
            <br />
            {plan.issued_at ? new Date(plan.issued_at).toLocaleString("pt-BR") : "—"}
          </div>
        </div>
        <p><strong>Eixo:</strong> {plan.axes?.name}</p>
        <p className="footnote">Ordem de descarga proposta pela sequência cadastrada do eixo. Não certifica arranjo físico/3D da carga.</p>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Parada</th>
                <th>Pedido / cidade</th>
                <th className="num">Valor</th>
                <th className="num">kg</th>
                <th className="num">m³</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.id}>
                  <td>{o.stop_sequence}ª</td>
                  <td><strong>{o.orders?.external_id}</strong><br />{o.city}</td>
                  <td className="num">{money(Number(o.value))}</td>
                  <td className="num">{Number(o.weight_kg).toLocaleString("pt-BR")}</td>
                  <td className="num">{Number(o.volume_m3).toLocaleString("pt-BR", { maximumFractionDigits: 3 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="sum"><strong>Total · {orders.length} pedidos</strong><strong>{money(totalValue)}</strong></div>
        <div className="sum"><span>Peso</span><strong>{Number(plan.total_weight_kg).toLocaleString("pt-BR")} kg</strong></div>
        <div className="sum"><span>Volume</span><strong>{Number(plan.total_volume_m3).toLocaleString("pt-BR", { maximumFractionDigits: 3 })} m³</strong></div>

        <p className="footnote">
          Critério de seleção: {plan.objective_policy}. A ordem apresentada não certifica
          empilhamento ou arranjo tridimensional da carga.
        </p>

        <div className="signature">Conferência do coordenador · assinatura / data</div>
      </div>
    </div>
  );
}
