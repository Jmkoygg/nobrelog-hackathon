import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Axis, Batch, City, DispatchRun, Plan, Vehicle } from "../types";

const money = (v: number) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export function DashboardPage() {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [axes, setAxes] = useState<Axis[]>([]);
  const [cities, setCities] = useState<City[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [dispatches, setDispatches] = useState<DispatchRun[]>([]);
  const [openIssues, setOpenIssues] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get<Batch[]>("/batches"),
      api.get<Vehicle[]>("/vehicles"),
      api.get<Axis[]>("/axes"),
      api.get<City[]>("/cities"),
      api.get<Plan[]>("/plans"),
      api.get<DispatchRun[]>("/dispatch"),
    ]).then(async ([b, v, a, c, p, d]) => {
      setBatches(b);
      setVehicles(v);
      setAxes(a);
      setCities(c);
      setPlans(p);
      setDispatches(d);
      const issueCounts = await Promise.all(
        b.map((batch) => api.get<unknown[]>(`/batches/${batch.id}/issues`).catch(() => []))
      );
      setOpenIssues(issueCounts.reduce((sum, list) => sum + list.length, 0));
      setLoading(false);
    });
  }, []);

  if (loading) return <p style={{ padding: 40 }}>Carregando painel…</p>;

  const totalLinhas = batches.reduce((s, b) => s + (b.summary.total_linhas || 0), 0);
  const totalDisponiveis = batches.reduce((s, b) => s + (b.summary.disponiveis || 0), 0);
  const totalPendentes = batches.reduce((s, b) => s + (b.summary.pendentes || 0), 0);
  const totalExcluidos = batches.reduce((s, b) => s + (b.summary.excluidos || 0), 0);

  const planosEmitidos = plans.filter((p) => p.status === "issued");
  const valorPlanos = planosEmitidos.reduce((s, p) => s + Number(p.total_value || 0), 0);

  const despachosEmitidos = dispatches.filter((d) => d.status === "issued");
  const distanciaTotal = despachosEmitidos.reduce((s, d) => s + Number(d.total_distance_km || 0), 0);
  const valorDespachos = despachosEmitidos.reduce((s, d) => s + Number(d.total_value || 0), 0);

  const cidadesComCoord = cities.filter((c) => c.lat != null && c.lng != null).length;
  const veiculosAtivos = vehicles.filter((v) => v.active).length;

  return (
    <div>
      <header className="page-header">
        <div>
          <div className="eyebrow">Visão geral</div>
          <h1>O que a operação já processou.</h1>
          <p className="muted">Números somados de todos os lotes e planos — atualiza a cada visita à página.</p>
        </div>
      </header>

      <h3 style={{ marginTop: 0 }}>Dados importados</h3>
      <div className="stats">
        <div className="stat">
          Pedidos no total
          <strong>{totalLinhas}</strong>
          <span className="footnote">{batches.length} lote(s) importado(s)</span>
        </div>
        <div className="stat">
          Disponíveis / pendentes
          <strong>{totalDisponiveis} / {totalPendentes}</strong>
          <span className="footnote">{totalExcluidos} excluídos (Crateús, retirada, cancelado)</span>
        </div>
        <div className="stat">
          Pendências abertas
          <strong>{openIssues ?? "—"}</strong>
          <span className="footnote">Ver aba Pendências</span>
        </div>
      </div>

      <h3>Planos de carga (um veículo por vez)</h3>
      <div className="stats">
        <div className="stat">
          Planos emitidos
          <strong>{planosEmitidos.length}</strong>
          <span className="footnote">de {plans.length} calculados (inclui rascunhos)</span>
        </div>
        <div className="stat">
          Valor total emitido
          <strong>{money(valorPlanos)}</strong>
          <span className="footnote">Soma dos planos com status "Emitido"</span>
        </div>
      </div>

      <h3>Despacho multi-veículo</h3>
      <div className="stats">
        <div className="stat">
          Despachos emitidos
          <strong>{despachosEmitidos.length}</strong>
          <span className="footnote">de {dispatches.length} calculados</span>
        </div>
        <div className="stat">
          Distância real percorrida
          <strong>{distanciaTotal.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} km</strong>
          <span className="footnote">Soma dos despachos emitidos (rota OSRM)</span>
        </div>
        <div className="stat">
          Valor total despachado
          <strong>{money(valorDespachos)}</strong>
        </div>
      </div>

      <h3>Cadastros</h3>
      <div className="stats">
        <div className="stat">
          Veículos ativos
          <strong>{veiculosAtivos}</strong>
          <span className="footnote">de {vehicles.length} cadastrados</span>
        </div>
        <div className="stat">
          Eixos cadastrados
          <strong>{axes.length}</strong>
          <span className="footnote">{axes.reduce((s, a) => s + a.cities.length, 0)} cidades vinculadas</span>
        </div>
        <div className="stat">
          Cidades com coordenada
          <strong>{cidadesComCoord} / {cities.length}</strong>
          <span className="footnote">Necessárias para o despacho multi-veículo</span>
        </div>
      </div>
    </div>
  );
}
