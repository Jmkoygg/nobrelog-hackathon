import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { supabase } from "../lib/supabaseClient";

const NAV = [
  { to: "/dashboard", num: "01", label: "Dashboard" },
  { to: "/carga", num: "02", label: "Montar carga" },
  { to: "/despacho", num: "03", label: "Despacho (multi-veículo)" },
  { to: "/pedidos", num: "04", label: "Pedidos" },
  { to: "/pendencias", num: "05", label: "Pendências" },
  { to: "/cadastros", num: "06", label: "Cadastros" },
  { to: "/historico", num: "07", label: "Histórico" },
];

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <aside>
        <div className="brand">
          Nobre<span>LOG</span>
        </div>
        <div className="subbrand">CENTRAL DE EXPEDIÇÃO</div>
        <nav className="main-nav" aria-label="Navegação principal">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              <span className="num">{item.num}</span> {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="aside-foot">
          <strong>NobreLOG · MVP</strong>
          Grupo Nobre Lar
          <br />
          <button
            className="btn secondary small"
            style={{ marginTop: 14, color: "#fff", borderColor: "#4d6c5f" }}
            onClick={() => supabase.auth.signOut()}
          >
            Sair
          </button>
        </div>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}
