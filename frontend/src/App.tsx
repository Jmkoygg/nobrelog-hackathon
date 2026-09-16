import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { Layout } from "./components/Layout";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { PedidosPage } from "./pages/PedidosPage";
import { PendenciasPage } from "./pages/PendenciasPage";
import { DespachoPage } from "./pages/DespachoPage";
import { CadastrosPage } from "./pages/CadastrosPage";
import { RomaneioPage } from "./pages/RomaneioPage";
import { DespachoRomaneioPage } from "./pages/DespachoRomaneioPage";
import { HistoricoPage } from "./pages/HistoricoPage";
import { api } from "./lib/api";

function AppShell() {
  const { session } = useAuth();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!session) return;
    // MVP de instancia unica: sem tela de criar/entrar em organizacao.
    // Todo login cai automaticamente na (unica) organizacao da operacao.
    api.post("/orgs/auto-join").finally(() => setReady(true));
  }, [session]);

  if (session && !ready) {
    return <div style={{ padding: 40 }}>Entrando…</div>;
  }

  return (
    <Layout>
      <Routes>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/despacho" element={<DespachoPage />} />
        <Route path="/pedidos" element={<PedidosPage />} />
        <Route path="/pendencias" element={<PendenciasPage />} />
        <Route path="/cadastros" element={<CadastrosPage />} />
        <Route path="/historico" element={<HistoricoPage />} />
        <Route path="/romaneio/:planId" element={<RomaneioPage />} />
        <Route path="/despacho/:runId/romaneio" element={<DespachoRomaneioPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Layout>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        />
      </Routes>
    </AuthProvider>
  );
}
