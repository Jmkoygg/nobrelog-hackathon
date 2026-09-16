import { useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import type { Batch, DispatchAssignment, DispatchRun } from "../types";

const money = (v: number) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

const REJECTION_LABEL: Record<string, string> = {
  sem_capacidade_disponivel_na_frota: "Sem capacidade disponível na frota",
  cidade_sem_coordenada_cadastrada: "Cidade sem coordenada cadastrada",
};

export function DespachoPage() {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [batchId, setBatchId] = useState("");
  const [mode, setMode] = useState<"simulacao_historica" | "operacao">("simulacao_historica");
  const [solving, setSolving] = useState(false);
  const [run, setRun] = useState<DispatchRun | null>(null);
  const [assignments, setAssignments] = useState<DispatchAssignment[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [issuing, setIssuing] = useState(false);

  useEffect(() => {
    api.get<Batch[]>("/batches").then((data) => {
      setBatches(data);
      if (data.length) setBatchId(data[0].id);
    });
  }, []);

  async function calculate() {
    setSolving(true);
    setError(null);
    setRun(null);
    setAssignments([]);
    try {
      const res = await api.post<{ dispatch_run: DispatchRun }>("/dispatch/solve", { batch_id: batchId, mode });
      const detail = await api.get<{ run: DispatchRun; assignments: DispatchAssignment[] }>(`/dispatch/${res.dispatch_run.id}`);
      setRun(detail.run);
      setAssignments(detail.assignments);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao calcular o despacho.");
    } finally {
      setSolving(false);
    }
  }

  async function issue() {
    if (!run) return;
    setIssuing(true);
    setError(null);
    try {
      const updated = await api.post<DispatchRun>(`/dispatch/${run.id}/issue`);
      setRun(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao emitir o despacho.");
    } finally {
      setIssuing(false);
    }
  }

  const served = assignments.filter((a) => a.selected);
  const dropped = assignments.filter((a) => !a.selected);
  const byVehicle = served.reduce<Record<string, DispatchAssignment[]>>((acc, a) => {
    const key = a.vehicle_id || "?";
    (acc[key] ||= []).push(a);
    return acc;
  }, {});
  for (const list of Object.values(byVehicle)) list.sort((a, b) => (a.stop_sequence || 0) - (b.stop_sequence || 0));

  return (
    <div>
      <header className="page-header">
        <div>
          <div className="eyebrow">Otimização completa · sem eixo fixo</div>
          <h1>Qual veículo, pra onde, em que ordem.</h1>
          <p className="muted">
            Decide junto: quais pedidos entram, em qual caminhão, e a rota real entre as cidades —
            um veículo pode combinar cidades de eixos diferentes numa mesma viagem.
          </p>
        </div>
      </header>

      <div className="toolbar">
        <div className="field">
          <label htmlFor="batch">Lote</label>
          <select id="batch" value={batchId} onChange={(e) => setBatchId(e.target.value)}>
            {batches.map((b) => (
              <option key={b.id} value={b.id}>{b.filename}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="mode">Modo</label>
          <select id="mode" value={mode} onChange={(e) => setMode(e.target.value as typeof mode)}>
            <option value="simulacao_historica">Simulação histórica</option>
            <option value="operacao">Operação</option>
          </select>
        </div>
        <button className="btn primary" onClick={calculate} disabled={!batchId || solving}>
          {solving ? "Calculando rotas… (pode levar até 20s)" : "Calcular despacho"}
        </button>
      </div>

      {error && <p className="notice error">{error}</p>}

      {run && (
        <>
          <div className="stats">
            <div className="stat">
              Rotas / veículos usados
              <strong>{Object.keys(byVehicle).length}</strong>
              <span className="footnote">de {batches.length ? "frota ativa" : "—"}</span>
            </div>
            <div className="stat">
              Pedidos servidos / descartados
              <strong>{served.length} / {dropped.length}</strong>
              <span className="footnote">{run.solver_status === "solved" ? "Solução encontrada" : run.solver_status}</span>
            </div>
            <div className="stat">
              Distância total real
              <strong>{run.total_distance_km?.toLocaleString("pt-BR")} km</strong>
              <span className="footnote">Valor total: {run.total_value != null ? money(run.total_value) : "—"}</span>
            </div>
          </div>

          {Object.entries(byVehicle).map(([vehicleId, stops]) => (
            <div className="panel" key={vehicleId}>
              <div className="panel-title">
                <h2>{stops[0]?.vehicles?.name || "Veículo"}</h2>
                <span className="badge">{stops.length} paradas</span>
              </div>
              <div className="route" style={{ marginBottom: 14 }}>
                {stops.map((s) => (
                  <div className="stop" key={s.id}>
                    <b>{s.stop_sequence}</b>
                    <div>{s.city}<small>+{s.leg_distance_km?.toFixed(1)} km</small></div>
                  </div>
                ))}
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr><th>Parada</th><th>Pedido</th><th>Cidade</th><th className="num">Valor</th><th className="num">kg</th><th className="num">m³</th></tr>
                  </thead>
                  <tbody>
                    {stops.map((s) => (
                      <tr key={s.id}>
                        <td>{s.stop_sequence}ª</td>
                        <td>{s.orders?.external_id}</td>
                        <td>{s.city}</td>
                        <td className="num">{money(Number(s.value))}</td>
                        <td className="num">{Number(s.weight_kg).toLocaleString("pt-BR")}</td>
                        <td className="num">{Number(s.volume_m3).toLocaleString("pt-BR", { maximumFractionDigits: 3 })}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}

          {dropped.length > 0 && (
            <div className="panel">
              <div className="panel-title"><h2>Pedidos não servidos nesta rodada</h2><span className="badge amber">{dropped.length}</span></div>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Pedido</th><th>Cidade</th><th className="num">Valor</th><th>Motivo</th></tr></thead>
                  <tbody>
                    {dropped.map((d) => (
                      <tr key={d.id}>
                        <td>{d.orders?.external_id}</td>
                        <td>{d.city}</td>
                        <td className="num">{money(Number(d.value))}</td>
                        <td><span className="badge amber">{REJECTION_LABEL[d.rejection_reason || ""] || d.rejection_reason}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="panel">
            <div className="panel-title">
              <h2>Status: {run.status === "draft" ? "Rascunho" : run.status === "issued" ? "Emitido" : "Cancelado"}</h2>
              {run.status === "draft" && (
                <button className="btn primary" onClick={issue} disabled={issuing || served.length === 0}>
                  {issuing ? "Emitindo…" : "Emitir despacho (reserva os pedidos)"}
                </button>
              )}
            </div>
            <p className="footnote">
              Critério quando falta capacidade para todos: valor comercial do pedido (diferente do
              critério de ocupação usado no fluxo de um eixo por vez — decisão a validar com o time).
            </p>
          </div>
        </>
      )}
    </div>
  );
}
