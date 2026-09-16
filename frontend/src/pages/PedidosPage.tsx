import { useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import type { Axis, Batch, City, Order, ProductSpec } from "../types";

interface ManualItemRow {
  product_code: string;
  quantity: string;
}

export function PedidosPage() {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [selectedBatch, setSelectedBatch] = useState<string>("");
  const [orders, setOrders] = useState<Order[]>([]);
  const [search, setSearch] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [importMessage, setImportMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [products, setProducts] = useState<ProductSpec[]>([]);
  const [axes, setAxes] = useState<Axis[]>([]);
  const [allCities, setAllCities] = useState<City[]>([]);
  const [manualCityId, setManualCityId] = useState("");
  const [manualValue, setManualValue] = useState("");
  const [manualItems, setManualItems] = useState<ManualItemRow[]>([{ product_code: "", quantity: "1" }]);
  const [creatingOrder, setCreatingOrder] = useState(false);
  const [manualMessage, setManualMessage] = useState<string | null>(null);
  const [manualBatchChoice, setManualBatchChoice] = useState<string>(""); // "" = ainda nao decidido, "__new__" = criar lote novo, senao = id de lote existente
  const [newBatchName, setNewBatchName] = useState("");

  useEffect(() => {
    api.get<ProductSpec[]>("/products").then(setProducts);
    api.get<Axis[]>("/axes").then(setAxes);
    api.get<City[]>("/cities").then(setAllCities);
  }, []);

  function updateItem(i: number, patch: Partial<ManualItemRow>) {
    setManualItems((prev) => prev.map((row, idx) => (idx === i ? { ...row, ...patch } : row)));
  }

  function addItemRow() {
    setManualItems((prev) => [...prev, { product_code: "", quantity: "1" }]);
  }

  function removeItemRow(i: number) {
    setManualItems((prev) => prev.filter((_, idx) => idx !== i));
  }

  async function handleCreateOrder(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setManualMessage(null);
    const items = manualItems
      .filter((r) => r.product_code && Number(r.quantity) > 0)
      .map((r) => ({ product_code: r.product_code, quantity: Number(r.quantity) }));
    if (!manualCityId || items.length === 0) {
      setError("Selecione a cidade e pelo menos um item com quantidade.");
      return;
    }
    setCreatingOrder(true);
    try {
      const payload: { city_id: string; value: number; items: typeof items; batch_id?: string; batch_name?: string } = {
        city_id: manualCityId,
        value: Number(manualValue) || 0,
        items,
      };
      if (manualBatchChoice === "__new__") {
        if (newBatchName.trim()) payload.batch_name = newBatchName.trim();
      } else if (manualBatchChoice) {
        payload.batch_id = manualBatchChoice;
      }
      const order = await api.post<Order>("/orders", payload);
      setManualMessage(
        order.data_status === "ready"
          ? `Pedido ${order.external_id} criado e pronto: ${order.weight_kg} kg / ${order.volume_m3} m³.`
          : `Pedido ${order.external_id} criado, mas ficou pendente — confira a aba Pendências.`
      );
      setManualCityId("");
      setManualValue("");
      setManualItems([{ product_code: "", quantity: "1" }]);
      setNewBatchName("");
      await loadBatches();
      setManualBatchChoice(order.batch_id);
      setSelectedBatch(order.batch_id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao criar pedido.");
    } finally {
      setCreatingOrder(false);
    }
  }

  async function loadBatches() {
    try {
      const data = await api.get<Batch[]>("/batches");
      setBatches(data);
      if (data.length && !selectedBatch) setSelectedBatch(data[0].id);
      if (!manualBatchChoice) {
        const manualDefault = data.find((b) => !b.filename.endsWith(".csv"));
        setManualBatchChoice(manualDefault ? manualDefault.id : "__new__");
      }
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
          <p className="muted">Cada lote mantém sua origem e suas pendências.</p>
        </div>
      </header>

      <div className="panel">
        <h2>Importar lote</h2>
        <form onSubmit={handleImport} className="toolbar" style={{ marginBottom: 0 }}>
          <div className="field">
            <label htmlFor="file">Arquivo (Pedidos_Filtrados_*.csv)</label>
            <input id="file" type="file" accept=".csv" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          </div>
          <button className="btn primary" type="submit" disabled={!file || importing}>
            {importing ? "Importando…" : "Importar"}
          </button>
        </form>
        {importMessage && <p className="notice">{importMessage}</p>}
      </div>

      <div className="panel">
        <h2>Montar pedido</h2>
        <p className="footnote">
          Pedido criado aqui passa pela mesma conferência de peso/volume que um importado — fica
          disponível pra montar carga assim que todo item tiver ficha no catálogo.
        </p>
        <form onSubmit={handleCreateOrder}>
          <div className="toolbar" style={{ marginBottom: 14 }}>
            <div className="field">
              <label htmlFor="manualCity">Cidade</label>
              <select id="manualCity" value={manualCityId} onChange={(e) => setManualCityId(e.target.value)}>
                <option value="">Selecione uma cidade…</option>
                {axes.map((axis) =>
                  axis.cities.length > 0 ? (
                    <optgroup key={axis.id} label={axis.name}>
                      {axis.cities.map((c) => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                      ))}
                    </optgroup>
                  ) : null
                )}
                {allCities.filter((c) => !c.axis_id).length > 0 && (
                  <optgroup label="Sem eixo">
                    {allCities
                      .filter((c) => !c.axis_id)
                      .map((c) => (
                        <option key={c.id} value={c.id}>{c.name}</option>
                      ))}
                  </optgroup>
                )}
              </select>
              {manualCityId && !allCities.find((c) => c.id === manualCityId)?.axis_id && (
                <small className="muted">Cidade sem eixo — o pedido fica pendente, não entra em Montar Carga.</small>
              )}
            </div>
            <div className="field">
              <label htmlFor="manualValue">Valor do pedido</label>
              <input id="manualValue" type="number" step="0.01" min="0" value={manualValue} onChange={(e) => setManualValue(e.target.value)} placeholder="0,00" />
            </div>
            <div className="field">
              <label htmlFor="manualBatch">Lote</label>
              <select id="manualBatch" value={manualBatchChoice} onChange={(e) => setManualBatchChoice(e.target.value)}>
                <option value="__new__">+ Novo lote…</option>
                {batches
                  .filter((b) => !b.filename.endsWith(".csv"))
                  .map((b) => (
                    <option key={b.id} value={b.id}>{b.filename}</option>
                  ))}
              </select>
            </div>
            {manualBatchChoice === "__new__" && (
              <div className="field">
                <label htmlFor="newBatchName">Nome do novo lote</label>
                <input
                  id="newBatchName"
                  value={newBatchName}
                  onChange={(e) => setNewBatchName(e.target.value)}
                  placeholder="Ex.: Pedidos avulsos — semana 5"
                />
              </div>
            )}
          </div>

          <div className="table-wrap" style={{ marginBottom: 10 }}>
            <table>
              <thead><tr><th>Produto</th><th style={{ width: 140 }}>Quantidade</th><th></th></tr></thead>
              <tbody>
                {manualItems.map((row, i) => (
                  <tr key={i}>
                    <td>
                      <select value={row.product_code} onChange={(e) => updateItem(i, { product_code: e.target.value })}>
                        <option value="">Selecione um produto…</option>
                        {products.map((p) => (
                          <option key={p.id} value={p.code}>{p.code} — {p.description}</option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={row.quantity}
                        onChange={(e) => updateItem(i, { quantity: e.target.value })}
                      />
                    </td>
                    <td>
                      {manualItems.length > 1 && (
                        <button type="button" className="btn secondary small" onClick={() => removeItemRow(i)}>✕</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button type="button" className="btn secondary small" onClick={addItemRow} style={{ marginBottom: 14 }}>
            + Adicionar item
          </button>
          <div>
            <button className="btn primary" type="submit" disabled={creatingOrder}>
              {creatingOrder ? "Criando…" : "Criar pedido"}
            </button>
          </div>
        </form>
        {manualMessage && <p className="notice">{manualMessage}</p>}
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
                    {b.filename} · {new Date(b.created_at).toLocaleString("pt-BR")}
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
