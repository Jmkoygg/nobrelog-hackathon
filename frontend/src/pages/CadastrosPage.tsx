import { useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import { MapPicker } from "../components/MapPicker";
import type { Axis, City, ProductSpec, Vehicle } from "../types";

type Tab = "fleet" | "axes" | "products";

export function CadastrosPage() {
  const [tab, setTab] = useState<Tab>("fleet");

  return (
    <div>
      <header className="page-header">
        <div>
          <div className="eyebrow">Configuração da operação</div>
          <h1>A frota muda. O sistema acompanha.</h1>
          <p className="muted">Capacidades, produtos e localidades ficam fora da lógica do cálculo.</p>
        </div>
      </header>
      <div className="tabs">
        <button className={tab === "fleet" ? "active" : ""} onClick={() => setTab("fleet")}>Frota</button>
        <button className={tab === "axes" ? "active" : ""} onClick={() => setTab("axes")}>Eixos e cidades</button>
        <button className={tab === "products" ? "active" : ""} onClick={() => setTab("products")}>Produtos</button>
      </div>
      {tab === "fleet" && <FleetTab />}
      {tab === "axes" && <AxesTab />}
      {tab === "products" && <ProductsTab />}
    </div>
  );
}

function FleetTab() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [name, setName] = useState("");
  const [kg, setKg] = useState("");
  const [m3, setM3] = useState("");
  const [error, setError] = useState<string | null>(null);

  function load() {
    api.get<Vehicle[]>("/vehicles").then(setVehicles);
  }
  useEffect(load, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/vehicles", { name, capacity_kg: Number(kg), capacity_m3: Number(m3), active: true });
      setName(""); setKg(""); setM3("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao criar veículo.");
    }
  }

  async function toggleActive(v: Vehicle) {
    await api.patch(`/vehicles/${v.id}`, { name: v.name, capacity_kg: v.capacity_kg, capacity_m3: v.capacity_m3, active: !v.active });
    load();
  }

  return (
    <div className="panel">
      <h2>Veículos cadastrados</h2>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Nome</th><th className="num">kg</th><th className="num">m³</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {vehicles.map((v) => (
              <tr key={v.id}>
                <td>{v.name}</td>
                <td className="num">{v.capacity_kg}</td>
                <td className="num">{v.capacity_m3}</td>
                <td><span className={`badge ${v.active ? "" : "red"}`}>{v.active ? "Ativo" : "Inativo"}</span></td>
                <td><button className="btn secondary small" onClick={() => toggleActive(v)}>{v.active ? "Desativar" : "Ativar"}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 style={{ marginTop: 24 }}>Novo veículo</h2>
      <form onSubmit={create} className="toolbar" style={{ marginBottom: 0 }}>
        <div className="field"><label>Nome</label><input value={name} onChange={(e) => setName(e.target.value)} required /></div>
        <div className="field"><label>Capacidade (kg)</label><input type="number" step="0.001" value={kg} onChange={(e) => setKg(e.target.value)} required /></div>
        <div className="field"><label>Capacidade (m³)</label><input type="number" step="0.0001" value={m3} onChange={(e) => setM3(e.target.value)} required /></div>
        <button className="btn primary" type="submit">Adicionar</button>
      </form>
      {error && <p className="notice error">{error}</p>}
    </div>
  );
}

function AxesTab() {
  const [axes, setAxes] = useState<Axis[]>([]);
  const [allCities, setAllCities] = useState<City[]>([]);
  const [axisName, setAxisName] = useState("");
  const [cityInputs, setCityInputs] = useState<Record<string, string>>({});
  const [looseCityName, setLooseCityName] = useState("");
  const [editingCity, setEditingCity] = useState<string | null>(null);
  const [rebuilding, setRebuilding] = useState(false);
  const [rebuildMsg, setRebuildMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    api.get<Axis[]>("/axes").then(setAxes);
    api.get<City[]>("/cities").then(setAllCities);
  }
  useEffect(load, []);

  const looseCities = allCities.filter((c) => !c.axis_id);

  async function createAxis(e: React.FormEvent) {
    e.preventDefault();
    await api.post("/axes", { name: axisName });
    setAxisName("");
    load();
  }

  async function addCityToAxis(axisId: string) {
    const name = (cityInputs[axisId] || "").trim();
    if (!name) return;
    const axis = axes.find((a) => a.id === axisId);
    try {
      await api.post("/cities", { name, axis_id: axisId, sort_order: axis?.cities.length || 0 });
      setCityInputs((prev) => ({ ...prev, [axisId]: "" }));
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao adicionar cidade.");
    }
  }

  async function addLooseCity(e: React.FormEvent) {
    e.preventDefault();
    if (!looseCityName.trim()) return;
    await api.post("/cities", { name: looseCityName.trim() });
    setLooseCityName("");
    load();
  }

  async function setCoords(city: City, lat: number, lng: number) {
    await api.patch(`/cities/${city.id}`, { ...city, lat, lng });
    load();
  }

  async function setAxisFor(city: City, axisId: string) {
    await api.patch(`/cities/${city.id}`, { ...city, axis_id: axisId || null });
    load();
  }

  async function toggleDepot(city: City) {
    await api.patch(`/cities/${city.id}`, { ...city, is_depot: !city.is_depot });
    load();
  }

  async function removeCity(id: string) {
    await api.delete(`/cities/${id}`);
    if (editingCity === id) setEditingCity(null);
    load();
  }

  async function rebuild() {
    setRebuilding(true);
    setRebuildMsg(null);
    setError(null);
    try {
      const res = await api.post<{ cities: number; cities_sem_coordenada: number; pairs_computed: number }>(
        "/cities/distances/rebuild"
      );
      setRebuildMsg(
        `Matriz recalculada: ${res.cities} cidades com coordenada, ${res.pairs_computed} pares via OSRM` +
          (res.cities_sem_coordenada ? ` (${res.cities_sem_coordenada} sem coordenada ainda, ignoradas).` : ".")
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao calcular distâncias.");
    } finally {
      setRebuilding(false);
    }
  }

  function CityRow({ city }: { city: City }) {
    const hasCoords = city.lat != null && city.lng != null;
    return (
      <div key={city.id} style={{ borderBottom: "1px solid var(--line)", padding: "10px 0" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <strong style={{ minWidth: 160 }}>{city.name}</strong>
          {city.is_depot && <span className="badge">CDD</span>}
          <span className={`badge ${hasCoords ? "" : "amber"}`}>
            {hasCoords ? `${city.lat!.toFixed(4)}, ${city.lng!.toFixed(4)}` : "sem coordenada"}
          </span>
          <select
            value={city.axis_id || ""}
            onChange={(e) => setAxisFor(city, e.target.value)}
            style={{ maxWidth: 220 }}
          >
            <option value="">Sem eixo (avulsa)</option>
            {axes.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
          <button className="btn secondary small" onClick={() => setEditingCity(editingCity === city.id ? null : city.id)}>
            {editingCity === city.id ? "Fechar mapa" : "Editar no mapa"}
          </button>
          <button className="btn secondary small" onClick={() => toggleDepot(city)}>
            {city.is_depot ? "Desmarcar depósito" : "Marcar como depósito"}
          </button>
          <button className="btn secondary small" onClick={() => removeCity(city.id)}>✕</button>
        </div>
        {editingCity === city.id && (
          <div style={{ marginTop: 10 }}>
            <MapPicker lat={city.lat} lng={city.lng} onChange={(lat, lng) => setCoords(city, lat, lng)} />
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-title">
        <h2>Eixos, cidades e coordenadas</h2>
        <button className="btn secondary small" onClick={rebuild} disabled={rebuilding}>
          {rebuilding ? "Calculando…" : "Recalcular distâncias (OSRM)"}
        </button>
      </div>
      <p className="footnote">
        Cidade pode ter eixo, coordenada, os dois ou nenhum — são independentes. Eixo é referência
        para o fluxo de um veículo por vez; coordenada é o que o despacho multi-veículo usa pra
        rota real. Depois de marcar/mudar coordenada, clique em "Recalcular distâncias".
      </p>
      {rebuildMsg && <p className="notice">{rebuildMsg}</p>}
      {error && <p className="notice error">{error}</p>}

      {axes.map((axis) => (
        <div key={axis.id} className="panel" style={{ background: "var(--soft)" }}>
          <h3 style={{ margin: "0 0 10px" }}>{axis.name}</h3>
          {axis.cities
            .sort((a, b) => a.sort_order - b.sort_order)
            .map((c) => (
              <CityRow city={allCities.find((ac) => ac.id === c.id) || c} key={c.id} />
            ))}
          <div className="toolbar" style={{ marginBottom: 0, marginTop: 12 }}>
            <div className="field">
              <label>Nova cidade neste eixo</label>
              <input
                value={cityInputs[axis.id] || ""}
                onChange={(e) => setCityInputs((prev) => ({ ...prev, [axis.id]: e.target.value }))}
              />
            </div>
            <button className="btn secondary" onClick={() => addCityToAxis(axis.id)}>Adicionar cidade</button>
          </div>
        </div>
      ))}

      <h2 style={{ marginTop: 24 }}>Novo eixo</h2>
      <form onSubmit={createAxis} className="toolbar" style={{ marginBottom: 0 }}>
        <div className="field"><label>Nome do eixo</label><input value={axisName} onChange={(e) => setAxisName(e.target.value)} required /></div>
        <button className="btn primary" type="submit">Criar eixo</button>
      </form>

      <h2 style={{ marginTop: 24 }}>Cidades avulsas (sem eixo)</h2>
      <p className="footnote">
        Localidades citadas nos pedidos sem eixo confirmado — mapeie a coordenada e, se souber,
        associe a um eixo pelo seletor acima de cada uma.
      </p>
      {looseCities.map((c) => <CityRow city={c} key={c.id} />)}
      <form onSubmit={addLooseCity} className="toolbar" style={{ marginBottom: 0, marginTop: 12 }}>
        <div className="field"><label>Nova cidade avulsa</label><input value={looseCityName} onChange={(e) => setLooseCityName(e.target.value)} /></div>
        <button className="btn secondary" type="submit">Adicionar</button>
      </form>
    </div>
  );
}

function ProductsTab() {
  const [products, setProducts] = useState<ProductSpec[]>([]);
  const [form, setForm] = useState({ code: "", description: "", sale_unit: "UN", load_unit: "UN", conversion_factor: "1", weight_kg: "", volume_m3: "", is_estimated: false, source: "" });

  function load() {
    api.get<ProductSpec[]>("/products").then(setProducts);
  }
  useEffect(load, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    await api.post("/products", {
      code: form.code,
      description: form.description || null,
      sale_unit: form.sale_unit,
      load_unit: form.load_unit,
      conversion_factor: Number(form.conversion_factor) || 1,
      weight_kg: form.weight_kg ? Number(form.weight_kg) : null,
      volume_m3: form.volume_m3 ? Number(form.volume_m3) : null,
      is_estimated: form.is_estimated,
      source: form.source || null,
    });
    setForm({ code: "", description: "", sale_unit: "UN", load_unit: "UN", conversion_factor: "1", weight_kg: "", volume_m3: "", is_estimated: false, source: "" });
    load();
  }

  return (
    <div className="panel">
      <h2>Catálogo de produtos ({products.length})</h2>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Código</th><th>Descrição</th><th>Un. venda → carga</th><th className="num">Fator</th><th className="num">kg/un</th><th className="num">m³/un</th><th>Estim.</th></tr></thead>
          <tbody>
            {products.map((p) => (
              <tr key={p.id}>
                <td>{p.code}</td>
                <td>{p.description}</td>
                <td>{p.sale_unit} → {p.load_unit}</td>
                <td className="num">{p.conversion_factor}</td>
                <td className="num">{p.weight_kg ?? "—"}</td>
                <td className="num">{p.volume_m3 ?? "—"}</td>
                <td>{p.is_estimated ? <span className="badge amber">Sim</span> : "Não"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 style={{ marginTop: 24 }}>Cadastrar / atualizar produto</h2>
      <form onSubmit={save} className="toolbar" style={{ marginBottom: 0, flexWrap: "wrap" }}>
        <div className="field"><label>Código</label><input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} required /></div>
        <div className="field"><label>Descrição</label><input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
        <div className="field"><label>Un. venda</label><input value={form.sale_unit} onChange={(e) => setForm({ ...form, sale_unit: e.target.value })} /></div>
        <div className="field"><label>Un. carga</label><input value={form.load_unit} onChange={(e) => setForm({ ...form, load_unit: e.target.value })} /></div>
        <div className="field"><label>Fator conversão</label><input type="number" step="0.0001" value={form.conversion_factor} onChange={(e) => setForm({ ...form, conversion_factor: e.target.value })} /></div>
        <div className="field"><label>Peso (kg/un carga)</label><input type="number" step="0.0001" value={form.weight_kg} onChange={(e) => setForm({ ...form, weight_kg: e.target.value })} /></div>
        <div className="field"><label>Volume (m³/un carga)</label><input type="number" step="0.000001" value={form.volume_m3} onChange={(e) => setForm({ ...form, volume_m3: e.target.value })} /></div>
        <div className="field"><label>Fonte</label><input value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} /></div>
        <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <input type="checkbox" checked={form.is_estimated} onChange={(e) => setForm({ ...form, is_estimated: e.target.checked })} />
          Dado estimado
        </label>
        <button className="btn primary" type="submit">Salvar</button>
      </form>
    </div>
  );
}

