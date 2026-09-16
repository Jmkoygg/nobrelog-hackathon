import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import type { Plan } from "../types";

const STATUS_LABEL: Record<string, string> = {
  draft: "Rascunho",
  issued: "Emitido",
  cancelled: "Cancelado",
  completed: "Concluído",
};

export function HistoricoPage() {
  const [plans, setPlans] = useState<Plan[]>([]);

  useEffect(() => {
    api.get<Plan[]>("/plans").then(setPlans);
  }, []);

  async function cancelPlan(id: string) {
    await api.post(`/plans/${id}/cancel`);
    setPlans((prev) => prev.map((p) => (p.id === id ? { ...p, status: "cancelled" } : p)));
  }

  return (
    <div>
      <header className="page-header">
        <div>
          <div className="eyebrow">Rastreabilidade</div>
          <h1>Cada plano guarda sua versão.</h1>
          <p className="muted">Mudanças na frota não reescrevem documentos já emitidos.</p>
        </div>
      </header>

      <div className="panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Data</th>
                <th>Eixo</th>
                <th>Veículo</th>
                <th>Modo</th>
                <th className="num">Valor</th>
                <th>Estado</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {plans.map((p) => (
                <tr key={p.id}>
                  <td>{new Date(p.created_at).toLocaleString("pt-BR")}</td>
                  <td>{p.axes?.name}</td>
                  <td>{p.vehicles?.name}</td>
                  <td>{p.mode === "simulacao_historica" ? "Simulação" : "Operação"}</td>
                  <td className="num">{Number(p.total_value).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}</td>
                  <td><span className="badge">{STATUS_LABEL[p.status] || p.status}</span></td>
                  <td>
                    <Link className="btn secondary small" to={`/romaneio/${p.id}`}>Ver</Link>{" "}
                    {p.status === "issued" && (
                      <button className="btn secondary small" onClick={() => cancelPlan(p.id)}>Cancelar</button>
                    )}
                  </td>
                </tr>
              ))}
              {plans.length === 0 && (
                <tr><td colSpan={7}>Nenhum plano emitido ainda.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
