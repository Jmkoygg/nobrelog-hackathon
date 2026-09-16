import { useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import type { Batch, Issue } from "../types";

const ISSUE_LABELS: Record<string, string> = {
  produto_sem_ficha: "Produto sem ficha",
  unidade_ausente: "Unidade ausente",
  cidade_sem_eixo: "Cidade sem eixo",
  data_inconsistente: "Data inconsistente",
  saldo_parcial_desconhecido: "Saldo parcial desconhecido",
  conversao_ambigua: "Conversão ambígua",
};

export function PendenciasPage() {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [batchId, setBatchId] = useState("");
  const [issues, setIssues] = useState<Issue[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<Batch[]>("/batches").then((data) => {
      setBatches(data);
      if (data.length) setBatchId(data[0].id);
    });
  }, []);

  useEffect(() => {
    if (!batchId) return;
    api
      .get<Issue[]>(`/batches/${batchId}/issues`)
      .then(setIssues)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Erro ao carregar pendências."));
  }, [batchId]);

  const grouped = issues.reduce<Record<string, Issue[]>>((acc, issue) => {
    (acc[issue.issue_type] ||= []).push(issue);
    return acc;
  }, {});

  return (
    <div>
      <header className="page-header">
        <div>
          <div className="eyebrow">Qualidade dos dados</div>
          <h1>Resolva a informação que falta.</h1>
          <p className="muted">Cada pendência aponta o pedido ou produto afetado e o motivo exato.</p>
        </div>
        <span className="badge amber">{issues.length} pendências abertas</span>
      </header>

      <div className="toolbar">
        <div className="field">
          <label htmlFor="batch">Lote</label>
          <select id="batch" value={batchId} onChange={(e) => setBatchId(e.target.value)}>
            {batches.map((b) => (
              <option key={b.id} value={b.id}>
                {b.filename}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <p className="notice error">{error}</p>}

      {Object.entries(grouped).map(([type, list]) => (
        <div className="panel" key={type}>
          <div className="panel-title">
            <h2>{ISSUE_LABELS[type] || type}</h2>
            <span className="badge amber">{list.length}</span>
          </div>
          {list.map((issue) => (
            <div className="issue" key={issue.id} style={{ padding: "14px 0", borderBottom: "1px solid var(--line)" }}>
              <div className="text">
                <p style={{ margin: 0 }}>{issue.description}</p>
                {issue.product_code && <p className="footnote">Código do produto: {issue.product_code}</p>}
              </div>
            </div>
          ))}
        </div>
      ))}

      {issues.length === 0 && !error && (
        <div className="panel">
          <h2>Nenhuma pendência aberta neste lote.</h2>
          <p className="muted">Todos os pedidos elegíveis têm dados completos para o cálculo.</p>
        </div>
      )}

      <div className="notice">
        Correção de cadastro (produto/eixo) é feita na aba <strong>Cadastros</strong>. Depois de
        corrigir, recalcule a carga em <strong>Montar carga</strong> — o reprocessamento
        automático do pedido específico ainda não está implementado nesta versão.
      </div>
    </div>
  );
}
