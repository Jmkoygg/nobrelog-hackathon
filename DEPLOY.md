# Deploy — NobreLOG

Backend (FastAPI + OR-Tools) e frontend (React) vivem no mesmo repositório
mas são deploys **separados**: backend na Railway, frontend na Vercel. Não
dá pra rodar o backend na Vercel — funções serverless lá têm timeout curto
(10s no plano grátis) e o motor de rotas às vezes passa disso.

## 1. Backend na Railway

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo** → escolha este repositório.
2. Em **Settings → Root Directory**, coloque `backend`. A Railway detecta o `railway.json` e o `requirements.txt` sozinha.
3. Em **Variables**, adicione (mesmos valores do `backend/.env` local):
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_JWKS_URL` (`${SUPABASE_URL}/auth/v1/.well-known/jwks.json`)
   - `CORS_ALLOW_ORIGINS` → a URL que a Vercel vai te dar no passo 2 (pode voltar aqui depois pra ajustar)
4. Deploy. A Railway te dá uma URL tipo `https://nobrelog-backend.up.railway.app` — guarda ela.
5. Teste: `https://<sua-url>.up.railway.app/health` deve responder `{"status":"ok","supabase_configured":true}`.

## 2. Frontend na Vercel

1. [vercel.com](https://vercel.com) → **Add New → Project** → importe o mesmo repositório.
2. Em **Root Directory**, escolha `frontend`. A Vercel detecta Vite sozinha (build `npm run build`, output `dist`); o `vercel.json` já cuida do roteamento client-side (React Router).
3. Em **Environment Variables**, adicione:
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_ANON_KEY`
   - `VITE_API_BASE_URL` → a URL da Railway do passo 1 (`https://<sua-url>.up.railway.app`)
4. Deploy. A Vercel te dá a URL final do site.
5. Volta na Railway e atualiza `CORS_ALLOW_ORIGINS` com essa URL da Vercel (sem barra no final), senão o navegador bloqueia as chamadas à API.

## 3. Checklist pós-deploy

- [ ] `<backend>/health` responde `supabase_configured: true`
- [ ] Login funciona no site da Vercel
- [ ] `POST /orgs/auto-join` funciona no primeiro acesso de cada pessoa do time (sem tela de onboarding)
- [ ] Importar um CSV funciona
- [ ] Calcular carga (Montar carga) e Despacho multi-veículo funcionam
- [ ] Romaneio abre e imprime

## Observações

- **OR-Tools em produção**: o build fixa Python 3.12 (`backend/.python-version`) por compatibilidade de wheel mais testada que a 3.14 usada em desenvolvimento local. Se o build da Railway falhar por causa disso, é o primeiro lugar a olhar.
- **Migrations**: se for um projeto Supabase novo (diferente do usado em desenvolvimento), rodar as 7 migrations de `backend/db/migrations/` em ordem no SQL Editor do Supabase antes do primeiro deploy.
- **Sem tela de criar organização**: é comportamento esperado (decisão do time) — todo login cai automaticamente na única organização.
