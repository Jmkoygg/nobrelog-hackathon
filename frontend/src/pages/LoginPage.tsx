import { useState } from "react";
import { Navigate } from "react-router-dom";
import { supabase } from "../lib/supabaseClient";
import { useAuth } from "../auth/AuthContext";

type Mode = "signin" | "signup" | "reset";

export function LoginPage() {
  const { session, configured } = useAuth();
  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<{ text: string; error?: boolean } | null>(null);
  const [busy, setBusy] = useState(false);

  if (session) return <Navigate to="/dashboard" replace />;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      if (mode === "signin") {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      } else if (mode === "signup") {
        const { error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        setMessage({ text: "Conta criada. Confira seu e-mail para confirmar o acesso." });
      } else {
        const { error } = await supabase.auth.resetPasswordForEmail(email);
        if (error) throw error;
        setMessage({ text: "Enviamos um link de recuperação para o seu e-mail." });
      }
    } catch (err) {
      setMessage({ text: err instanceof Error ? err.message : "Erro inesperado.", error: true });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-shell">
      <div className="login-card">
        <div className="brand" style={{ color: "var(--green)", marginBottom: 6 }}>
          Nobre<span>LOG</span>
        </div>
        <p className="muted" style={{ marginTop: 0 }}>Central de expedição</p>

        {!configured && (
          <div className="notice error">
            Supabase nao configurado (<code>frontend/.env</code> vazio). Login desabilitado ate a
            configuracao ser preenchida.
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="field" style={{ marginBottom: 14 }}>
            <label htmlFor="email">E-mail</label>
            <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} disabled={!configured} />
          </div>
          {mode !== "reset" && (
            <div className="field" style={{ marginBottom: 18 }}>
              <label htmlFor="password">Senha</label>
              <input
                id="password"
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={!configured}
              />
            </div>
          )}
          <button className="btn primary" type="submit" disabled={!configured || busy} style={{ width: "100%" }}>
            {mode === "signin" ? "Entrar" : mode === "signup" ? "Criar conta" : "Enviar link de recuperação"}
          </button>
        </form>

        {message && (
          <p className={message.error ? "notice error" : "notice"} role="status">
            {message.text}
          </p>
        )}

        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 16, fontSize: 12 }}>
          {mode !== "signin" && (
            <button className="btn secondary small" onClick={() => setMode("signin")}>Entrar</button>
          )}
          {mode !== "signup" && (
            <button className="btn secondary small" onClick={() => setMode("signup")}>Criar conta</button>
          )}
          {mode !== "reset" && (
            <button className="btn secondary small" onClick={() => setMode("reset")}>Esqueci a senha</button>
          )}
        </div>
      </div>
    </div>
  );
}
