import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import type { Axis, Batch, Plan, PlanOrderRow, SolveResponse, Vehicle } from "../types";

const money = (v: number) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export function MontarCargaPage() {
  const navigate = useNavigate();
  const [axes, setAxes] = useState<Axis[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [axisId, setAxisId] = useState("");
  const [vehicleId, setVehicleId] = useState("");
  const [batchId, setBatchId] = useState("");
  const [mode, setMode] = useState<"simulacao_historica" | "operacao">("simulacao_historica");
  const [policy, setPolicy] = useState("ocupacao_media_kg_m3");

  const [solving, setSolving] = useState(false);
  const [result, setResult] = useState<SolveResponse | null>(null);
  const [planOrders, setPlanOrders] = useState<PlanOrderRow[]>([]);
  const [tab, setTab] = useState<"selected" | "left">("selected");
  const [error, setError] = useState<string | null>(null);
  const [issuing, setIssuing] = useState(false);

  useEffect(() => {
    Promise.all([api.get<Axis[]>("/axes"), api.get<Vehicle[]>("/vehicles"), api.get<Batch[]>("/batches")]).then(
      ([a, v, b]) => {
        setAxes(a);
        setVehicles(v.filter((x) => x.active));
        setBatches(b);
        if (a.length) setAxisId(a[0].id);
        if (v.length) setVehicleId(v[0].id);
        if (b.length) setBatchId(b[0].id);
      }
    );
  }, []);

  function invalidate() {
    setResult(null);
    setPlanOrders([]);
  }

  async function calculate() {
    setSolving(true);
    setError(null);
    try {
      const res = await api.post<SolveResponse>("/plans/solve", {
        axis_id: axisId,
        vehicle_id: vehicleId,
        batch_id: batchId,
        mode,
        policy,
      });
      setResult(res);
      const detail = await api.get<{ plan: Plan; orders: PlanOrderRow[] }>(`/plans/${res.plan.id}`);
      setPlanOrders(detail.orders);
      setTab("selected");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao calcular a carga.");
    } finally {
      setSolving(false);
    }
  }

  async function issuePlan() {
    if (!result) return;
    setIssuing(true);
    setError(null);
    try {
      await api.post(`/plans/${result.plan.id}/issue`);
      navigate(`/romaneio/${result.plan.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao emitir o plano.");
    } finally {
      setIssuing(false);
    }
  }

  const vehicle = vehicles.find((v) => v.id === vehicleId);
  const selected = planOrders.filter((o) => o.selected).sort((a, b) => (a.stop_sequence || 0) - (b.stop_sequence || 0));
  const notSelected = planOrders.filter((o) => !o.selected);
  const activeList = tab === "selected" ? selected : notSelected;

  const stops: { city: string; seq: number }[] = [];
  for (const o of selected) {
    if (!stops.find((s) => s.city === o.city)) stops.push({ city: o.city, seq: stops.length + 1 });
  }

  return (
    <div>
      <header className="page-header">
        <div>
          <div className="eyebrow">Planejamento de expedição</div>
          <h1>A carga certa para a próxima saída.</h1>
          <div className="muted">Escolha o eixo, o veículo e o lote. Confira as duas ocupações.</div>
        </div>
      </header>

      <div className="toolbar">
        <div className="field">
          <label htmlFor="axis">Eixo de entrega</label>
          <select id="axis" value={axisId} onChange={(e) => { setAxisId(e.target.value); invalidate(); }}>
            {axes.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="vehicle">Veículo</label>
          <select id="vehicle" value={vehicleId} onChange={(e) => { setVehicleId(e.target.value); invalidate(); }}>
            {vehicles.map((v) => (
              <option key={v.id} value={v.id}>{v.name} · {v.capacity_kg} kg / {v.capacity_m3} m³</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="batch">Lote</label>
          <select id="batch" value={batchId} onChange={(e) => { setBatchId(e.target.value); invalidate(); }}>
            {batches.map((b) => (
              <option key={b.id} value={b.id}>{b.filename}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="mode">Modo</label>
          <select id="mode" value={mode} onChange={(e) => { setMode(e.target.value as typeof mode); invalidate(); }}>
            <option value="simulacao_historica">Simulação histórica</option>
            <option value="operacao">Operação</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="policy">Critério</label>
          <select id="policy" value={policy} onChange={(e) => { setPolicy(e.target.value); invalidate(); }}>
            <option value="ocupacao_media_kg_m3">Ocupação média (kg + m³)</option>
            <option value="valor_total">Valor total</option>
          </select>
        </div>
        <button className="btn primary" onClick={calculate} disabled={!axisId || !vehicleId || !batchId || solving}>
          {solving ? "Calculando…" : "Calcular carga"}
        </button>
      </div>

      {error && <p className="notice error">{error}</p>}

      <div className="grid-2">
        <div>
          <div className="panel">
            <div className="panel-title">
              <h2>Pedidos da viagem</h2>
              <span className="badge">{result ? `${result.selected_count} de ${result.candidate_count} pedidos` : "Aguardando cálculo"}</span>
            </div>
            <div className="tabs">
              <button className={tab === "selected" ? "active" : ""} onClick={() => setTab("selected")}>Selecionados</button>
              <button className={tab === "left" ? "active" : ""} onClick={() => setTab("left")}>Não selecionados</button>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Pedido / cidade</th>
                    <th className="num">Valor</th>
                    <th className="num">kg</th>
                    <th className="num">m³</th>
                    <th>Situação</th>
                  </tr>
                </thead>
                <tbody>
                  {activeList.map((o) => (
                    <tr key={o.id}>
                      <td><strong>{o.orders?.external_id}</strong><br /><small className="muted">{o.city}</small></td>
                      <td className="num">{money(Number(o.value))}</td>
                      <td className="num">{Number(o.weight_kg).toLocaleString("pt-BR")}</td>
                      <td className="num">{Number(o.volume_m3).toLocaleString("pt-BR", { maximumFractionDigits: 3 })}</td>
                      <td>
                        <span className={`badge ${o.selected ? "" : "amber"}`}>
                          {o.selected ? "Selecionado" : o.rejection_reason || "Fora da combinação"}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {activeList.length === 0 && (
                    <tr><td colSpan={5}>{result ? "Nenhum pedido nesta lista." : "Calcule a carga para ver os pedidos."}</td></tr>
                  )}
                </tbody>
              </table>
            </div>
            {result && (
              <p className="footnote">
                {result.solver_status === "optimal"
                  ? "Melhor solução comprovada para o critério adotado."
                  : "Solução válida encontrada; busca encerrada pelo limite de tempo (não é necessariamente a melhor possível)."}
                {!result.validated && " Atenção: o validador independente encontrou inconsistências — não emita este plano."}
              </p>
            )}
          </div>

          {stops.length > 0 && (
            <div className="panel">
              <div className="panel-title"><h2>Ordem de descarga</h2></div>
              <div className="route">
                {stops.map((s) => (
                  <div className="stop" key={s.city}>
                    <b>{s.seq}</b>
                    <div>{s.city}<small>Proposta a conferir</small></div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div>
          <div className="panel">
            <div className="eyebrow">Capacidade utilizada</div>
            <div className="gauge">
              <div className="gauge-head"><strong>Peso</strong><span className="big">{result ? `${result.occupancy_kg_pct.toFixed(1)}%` : "—"}</span></div>
              <div className="track"><div className="fill" style={{ width: `${Math.min(result?.occupancy_kg_pct ?? 0, 100)}%` }} /></div>
              <div className="footnote">{result ? `${result.plan.total_weight_kg} / ${vehicle?.capacity_kg} kg` : "—"}</div>
            </div>
            <div className="gauge">
              <div className="gauge-head"><strong>Volume</strong><span className="big">{result ? `${result.occupancy_m3_pct.toFixed(1)}%` : "—"}</span></div>
              <div className="track"><div className="fill volume" style={{ width: `${Math.min(result?.occupancy_m3_pct ?? 0, 100)}%` }} /></div>
              <div className="footnote">{result ? `${result.plan.total_volume_m3} / ${vehicle?.capacity_m3} m³` : "—"}</div>
            </div>
            <div className="sum"><span>Valor dos pedidos</span><strong>{result ? money(Number(result.plan.total_value)) : "—"}</strong></div>
            <div className="sum"><span>Pedidos selecionados</span><strong>{result ? result.selected_count : "—"}</strong></div>
            <button
              className="btn primary wide-button"
              style={{ width: "100%", marginTop: 10 }}
              disabled={!result || !result.validated || result.selected_count === 0 || issuing}
              onClick={issuePlan}
            >
              {issuing ? "Emitindo…" : "Emitir e conferir romaneio →"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
