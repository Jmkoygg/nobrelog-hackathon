import { useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import type { Batch, Order } from "../types";

export function PedidosPage() {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [selectedBatch, setSelectedBatch] = useState<string>("");
  const [orders, setOrders] = useState<Order[]>([]);
  const [search, setSearch] = useState("");
  const [mode, setMode] = useState<"simulacao_historica" | "operacao">("simulacao_historica");
  const [file, setFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [importMessage, setImportMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadBatches() {
    try {
      const data = await api.get<Batch[]>("/batches");
      setBatches(data);
      if (data.length && !selectedBatch) setSelectedBatch(data[0].id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao carregar lotes.");
    }
  }

  useEffect(() => {
    loadBatches();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedBatch) return;
    api
      .get<Order[]>(`/batches/${selectedBatch}/orders${search ? `?search=${encodeURIComponent(search)}` : ""}`)
      .then(setOrders)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Erro ao carregar pedidos."));
  }, [selectedBatch, search]);

  async function handleImport(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setImporting(true);
    setImportMessage(null);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("mode", mode);
      const result = await api.upload<{ batch_id: string; already_imported: boolean; summary: Batch["summary"] }>(
        "/imports",
        form
      );
      setImportMessage(
        result.already_imported
          ? "Este arquivo ja tinha sido importado — nada foi duplicado."
          : `Importado: ${result.summary.total_linhas} linhas · ${result.summary.disponiveis} disponiveis · ${result.summary.pendentes} pendentes · ${result.summary.excluidos} excluidos.`
      );
      setSelectedBatch(result.batch_id);
      await loadBatches();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao importar arquivo.");
    } finally {
      setImporting(false);
    }
  }

  const currentBatch = batches.find((b) => b.id === selectedBatch);
  const summary = currentBatch?.summary || {};

  return (
    <div>
      <header className="page-header">
        <div>
          <div className="eyebrow">Entrada da operação</div>
          <h1>Pedidos, com dados conferidos.</h1>
          <p className="muted">Cada lote mantém sua origem, seu modo e suas pendências.</p>
        </div>
      </header>

      <div className="panel">
        <h2>Importar lote</h2>
        <form onSubmit={handleImport} className="toolbar" style={{ marginBottom: 0 }}>
          <div className="field">
            <label htmlFor="file">Arquivo (Pedidos_Filtrados_*.csv)</label>
            <input id="file" type="file" accept=".csv" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          </div>
          <div className="field">
            <label htmlFor="mode">Modo</label>
            <select id="mode" value={mode} onChange={(e) => setMode(e.target.value as typeof mode)}>
              <option value="simulacao_historica">Simulação histórica</option>
              <option value="operacao">Operação</option>
            </select>
          </div>
          <button className="btn primary" type="submit" disabled={!file || importing}>
            {importing ? "Importando…" : "Importar"}
          </button>
        </form>
        {importMessage && <p className="notice">{importMessage}</p>}
        {error && <p className="notice error">{error}</p>}
      </div>

      {batches.length > 0 && (
        <>
          <div className="toolbar">
            <div className="field">
              <label htmlFor="batch">Lote</label>
              <select id="batch" value={selectedBatch} onChange={(e) => setSelectedBatch(e.target.value)}>
                {batches.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.filename} · {new Date(b.created_at).toLocaleString("pt-BR")} · {b.mode}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="stats">
            <div className="stat">
              Total no lote
              <strong>{summary.total_linhas ?? "—"}</strong>
              <span className="footnote">Linhas do arquivo original</span>
            </div>
            <div className="stat">
              Disponíveis
              <strong>{summary.disponiveis ?? "—"}</strong>
              <span className="footnote">Prontos para montar carga</span>
            </div>
            <div className="stat">
              Pendentes / excluídos
              <strong>
                {summary.pendentes ?? "—"} / {summary.excluidos ?? "—"}
              </strong>
              <span className="footnote">Ver aba Pendências</span>
            </div>
          </div>

          <div className="panel">
            <label htmlFor="search">Buscar pedido ou cidade</label>
            <input
              id="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Ex.: Poranga"
              style={{ maxWidth: 400, margin: "10px 0 18px" }}
            />
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Pedido</th>
                    <th>Cidade</th>
                    <th className="num">kg</th>
                    <th className="num">m³</th>
                    <th>Dados</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((o) => (
                    <tr key={o.id}>
                      <td>
                        <strong>{o.external_id}</strong>
                      </td>
                      <td>{o.city}</td>
                      <td className="num">{o.weight_kg === null ? "Não calculado" : o.weight_kg.toLocaleString("pt-BR")}</td>
                      <td className="num">
                        {o.volume_m3 === null ? "Não calculado" : o.volume_m3.toLocaleString("pt-BR", { maximumFractionDigits: 3 })}
                      </td>
                      <td>
                        <span
                          className={`badge ${o.data_status === "ready" ? "" : o.data_status === "excluded" ? "red" : "amber"}`}
                        >
                          {o.data_status === "ready" ? "Pronto" : o.data_status === "excluded" ? `Excluído: ${o.excluded_reason}` : "Pendente"}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {orders.length === 0 && (
                    <tr>
                      <td colSpan={5}>Nenhum pedido encontrado.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
