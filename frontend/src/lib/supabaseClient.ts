import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

export const supabaseConfigured = Boolean(url && anonKey);

// Em vez de lancar e derrubar o app inteiro quando falta credencial, o
// client fica "vazio" e cada tela mostra a pendencia real de configuracao
// — nunca simula sessao logada.
export const supabase = supabaseConfigured
  ? createClient(url as string, anonKey as string)
  : createClient("https://placeholder.supabase.co", "placeholder-key");
