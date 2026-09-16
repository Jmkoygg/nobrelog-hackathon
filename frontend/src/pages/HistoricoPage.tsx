import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import type { DispatchRun, Plan } from "../types";

const STATUS_LABEL: Record<string, string> = {
  draft: "Rascunho",
  issued: "Emitido",
  cancelled: "Cancelado",
  completed: "Concluído",
};

interface HistoryRow {
  id: string;
  kind: "plan" | "dispatch";
  created_at: string;
  detail: string;
  total_value: number | null;
  status: string;
  viewHref: string;
  printHref: string;
}

export function HistoricoPage() {
  const [rows, setRows] = useState<HistoryRow[]>([]);

  async function load() {
    const [plans, dispatches] = await Promise.all([
      api.get<Plan[]>("/plans"),
      api.get<DispatchRun[]>("/dispatch"),
    ]);
    const planRows: HistoryRow[] = plans.map((p) => ({
      id: p.id,
      kind: "plan",
      created_at: p.created_at,
      detail: `${p.axes?.name || "—"} · ${p.vehicles?.name || "—"} (legado)`,
      total_value: Number(p.total_value),
      status: p.status,
      viewHref: `/romaneio/${p.id}`,
      printHref: `/romaneio/${p.id}`,
    }));
    const dispatchRows: HistoryRow[] = dispatches.map((d) => ({
      id: d.id,
      kind: "dispatch",
      created_at: d.created_at,
      detail: `Multi-veículo${d.total_distance_km != null ? ` · ${d.total_distance_km.toLocaleString("pt-BR")} km` : ""}`,
      total_value: d.total_value,
      status: d.status,
      viewHref: `/despacho?run=${d.id}`,
      printHref: `/despacho/${d.id}/romaneio`,
    }));
    setRows([...planRows, ...dispatchRows].sort((a, b) => b.created_at.localeCompare(a.created_at)));
  }

  useEffect(() => {
    load();
  }, []);

  async function cancelRow(row: HistoryRow) {
    await api.post(row.kind === "plan" ? `/plans/${row.id}/cancel` : `/dispatch/${row.id}/cancel`);
    setRows((prev) => prev.map((r) => (r.id === row.id ? { ...r, status: "cancelled" } : r)));
  }

  return (
    <div>
      <header className="page-header">
        <div>
          <div className="eyebrow">Rastreabilidade</div>
          <h1>Cada carga montada guarda sua versão.</h1>
          <p className="muted">Mudanças na frota não reescrevem documentos já emitidos.</p>
        </div>
      </header>

      <div className="panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Data</th>
                <th>Montagem</th>
                <th className="num">Valor</th>
                <th>Estado</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={`${r.kind}-${r.id}`}>
                  <td>{new Date(r.created_at).toLocaleString("pt-BR")}</td>
                  <td>{r.detail}</td>
                  <td className="num">{r.total_value != null ? r.total_value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "—"}</td>
                  <td><span className="badge">{STATUS_LABEL[r.status] || r.status}</span></td>
                  <td>
                    <Link className="btn secondary small" to={r.viewHref}>Ver</Link>{" "}
                    {r.status === "issued" && (
                      <>
                        <Link className="btn secondary small" to={r.printHref}>Imprimir</Link>{" "}
                        <button className="btn secondary small" onClick={() => cancelRow(r)}>Cancelar</button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr><td colSpan={5}>Nenhuma carga emitida ainda.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
