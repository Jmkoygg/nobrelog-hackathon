import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
import type { DispatchAssignment, DispatchRun } from "../types";

const money = (v: number) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export function DespachoRomaneioPage() {
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<DispatchRun | null>(null);
  const [assignments, setAssignments] = useState<DispatchAssignment[]>([]);

  useEffect(() => {
    if (!runId) return;
    api.get<{ run: DispatchRun; assignments: DispatchAssignment[] }>(`/dispatch/${runId}`).then((data) => {
      setRun(data.run);
      setAssignments(
        data.assignments
          .filter((a) => a.selected)
          .sort((a, b) => (a.stop_sequence || 0) - (b.stop_sequence || 0))
      );
    });
  }, [runId]);

  if (!run) return <p style={{ padding: 40 }}>Carregando romaneio…</p>;

  const byVehicle = assignments.reduce<Record<string, DispatchAssignment[]>>((acc, a) => {
    const key = a.vehicle_id || "?";
    (acc[key] ||= []).push(a);
    return acc;
  }, {});

  return (
    <div>
      <header className="page-header no-print">
        <div>
          <div className="eyebrow">Documento de expedição</div>
          <h1>Romaneio de despacho — um papel por veículo.</h1>
        </div>
        <button className="btn primary" onClick={() => window.print()}>Imprimir / salvar PDF</button>
      </header>

      {Object.entries(byVehicle).map(([vehicleId, stops]) => {
        const totalValue = stops.reduce((a, s) => a + Number(s.value), 0);
        const totalWeight = stops.reduce((a, s) => a + Number(s.weight_kg), 0);
        const totalVolume = stops.reduce((a, s) => a + Number(s.volume_m3), 0);
        return (
          <div className="paper" key={vehicleId}>
            <div className="paper-top">
              <div>
                <div className="brand" style={{ color: "var(--green)" }}>NobreLOG</div>
                <h1>Romaneio de despacho</h1>
                <div>
                  {stops[0]?.vehicles?.name || "Veículo"} ·{" "}
                  {totalWeight.toLocaleString("pt-BR")} kg /{" "}
                  {totalVolume.toLocaleString("pt-BR", { maximumFractionDigits: 3 })} m³
                </div>
              </div>
              <div style={{ textAlign: "right", fontSize: 12 }}>
                Despacho {run.id.slice(0, 8)}
                <br />
                {run.status.toUpperCase()}
                <br />
                {run.issued_at ? new Date(run.issued_at).toLocaleString("pt-BR") : "—"}
              </div>
            </div>
            <p className="footnote">
              Rota calculada por distância real de estrada (OSRM). Não certifica arranjo físico/3D da carga.
            </p>

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
                  {stops.map((s) => (
                    <tr key={s.id}>
                      <td>{s.stop_sequence}ª</td>
                      <td>
                        <strong>{s.orders?.external_id}</strong>
                        <br />
                        {s.city}
                      </td>
                      <td className="num">{money(Number(s.value))}</td>
                      <td className="num">{Number(s.weight_kg).toLocaleString("pt-BR")}</td>
                      <td className="num">{Number(s.volume_m3).toLocaleString("pt-BR", { maximumFractionDigits: 3 })}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="sum">
              <strong>Total · {stops.length} pedidos</strong>
              <strong>{money(totalValue)}</strong>
            </div>
            <div className="sum">
              <span>Peso</span>
              <strong>{totalWeight.toLocaleString("pt-BR")} kg</strong>
            </div>
            <div className="sum">
              <span>Volume</span>
              <strong>{totalVolume.toLocaleString("pt-BR", { maximumFractionDigits: 3 })} m³</strong>
            </div>

            <div className="signature">Conferência do motorista · assinatura / data</div>
          </div>
        );
      })}
    </div>
  );
}
