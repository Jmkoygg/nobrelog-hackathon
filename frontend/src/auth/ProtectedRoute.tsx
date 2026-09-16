import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { session, loading, configured } = useAuth();

  if (!configured) {
    return (
      <div className="notice" style={{ margin: 40 }}>
        <strong>Backend/Supabase ainda nao configurado.</strong> Preencha{" "}
        <code>frontend/.env</code> a partir de <code>.env.example</code> com a URL e a anon key
        do projeto Supabase. Sem isso a autenticacao nao pode ser verificada — nao ha sessao
        simulada.
      </div>
    );
  }
  if (loading) return <div style={{ padding: 40 }}>Carregando sessao…</div>;
  if (!session) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
