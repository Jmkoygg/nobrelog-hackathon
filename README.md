# NobreLOG — MVP

Montagem automática de carga por eixo para o Grupo Nobre Lar. Ver
[DESIGN-NOBRELOG.md](DESIGN-NOBRELOG.md) e [diagnostico-dados.md](diagnostico-dados.md)
para o desenho completo e a auditoria dos dados reais — este documento é só
o "como rodar" e o status real da implementação.

## Status

Projeto Supabase real criado (`ynnwiikvafavzroeijik`, região `sa-east-1`) e o
fluxo inteiro foi verificado ponta a ponta contra ele — não é só "compila",
foi rodado de verdade com dois usuários e dados reais das planilhas.

**Verificado de ponta a ponta (via API real, não só unit test):**
- Login real (Supabase Auth) → JWT validado pelo backend via JWKS.
- Importação do CSV semanal real → limpeza → cubagem com o catálogo real
  (85 produtos de `Ranking_Top85_Materiais.csv`).
- Otimizador CP-SAT rodando sobre pedidos reais: `optimal`, validador
  independente sem erros, ocupação de peso/volume calculada corretamente.
- Emissão do plano → reserva dos pedidos → romaneio.
- **RLS isolando organizações de verdade**: um segundo usuário, em outra
  organização, consultou `/vehicles` e recebeu lista vazia — não enxergou
  nada do primeiro.
- **Reimportação idempotente**: reenviar o mesmo arquivo retorna
  `already_imported: true`, sem duplicar pedido.
- **Impedimento de dupla alocação**: depois de emitir um plano, os mesmos
  pedidos somem da lista de candidatos de um novo cálculo.
- **Invalidação por versão**: alterar a capacidade do veículo faz a emissão
  de um plano-rascunho antigo falhar com 409 ("recalcule antes de emitir").
- 25 testes automatizados (`pytest`) — parsing, cubagem, solver comparado
  contra enumeração exaustiva.

**Bug real encontrado e corrigido nesse processo:** as pendências (`issues`)
geradas na importação não estavam sendo vinculadas ao pedido (`order_id`
ficava nulo) — a tela de Pendências ficava sempre vazia mesmo com pedido
pendente de verdade. Corrigido em `app/services/import_pipeline.py`.

## Despacho multi-veículo (rota real, sem eixo fixo)

Camada nova, adicionada depois do MVP obrigatório, a pedido explícito do
time: peso×volume + qual veículo atende quais pedidos + rota real entre
cidades, tudo num modelo só — sem travar por eixo (um veículo pode
combinar cidades de eixos diferentes numa mesma viagem).

**Verificado de ponta a ponta, com distância real de estrada (não linha reta):**
- 23 cidades do Sertão Central/Inhamuns geocodificadas e conferidas (uma,
  "Ibiapaba", foi **removida** por ser serra/região, não cidade — pendência
  real, não inventei coordenada pra ela).
- Matriz de distância real calculada via OSRM e cacheada no banco (a
  demonstração ao vivo não depende de internet no momento da montagem de
  carga, só no momento de recalcular o cache).
- Motor VRP (OR-tools `routing`, não o CP-SAT do fluxo single-axis) rodando
  sobre pedidos e frota reais: **um veículo combinou cidades de 3 eixos
  oficiais diferentes numa rota só** (Poranga → Sucesso → Independência),
  provando que a rota não está mais travada por eixo.
- Pedido que não cabe é descartado com motivo (`sem_capacidade_disponivel_na_frota`
  ou `cidade_sem_coordenada_cadastrada`, nunca silencioso).
- Emissão cria reserva na **mesma tabela** do fluxo single-axis — pedido
  reservado por um não pode ser pego pelo outro (dupla alocação continua
  impedida, agora entre os dois sistemas).
- 29 testes automatizados no total (4 novos só do VRP, incluindo o caso
  "descarta o pedido de menor valor quando a capacidade aperta").

**Bug real encontrado e corrigido:** nome de cidade do CSV vem sem acento
e maiúsculo (`ARARENDA`); nome cadastrado via geocoding vem com acento e
capitalização normal (`Ararendá`) — o cruzamento falhava silenciosamente
(0 pedidos casavam com cidade nenhuma). Corrigido com uma chave de
comparação que remove acento só para o match, sem alterar o que é exibido.

**Decisão de política que o time precisa validar:** como a decisão de
"quem fica de fora" agora é por pedido dentro de uma rota inteira (não
mais só ocupação agregada de um veículo), o critério de prioridade quando
falta capacidade pra todo mundo é **valor comercial do pedido** — diferente
do critério padrão do fluxo single-axis (ocupação). Está isolado em uma
função (`app/optimizer/vrp_solver.py`, comentário no topo do arquivo) —
trocar não exige mudar a estrutura do modelo.

**NÃO existe tela para isso ainda** — só testei via API/curl
(`POST /dispatch/solve`, `POST /dispatch/{id}/issue`). Se quiser demonstrar
isso na banca pela interface, preciso construir a tela ainda.

## Verificado clicando na tela (não só API), fluxo completo

Pedidos → Pendências → Montar carga → Emitir → Romaneio → Histórico →
Cancelar → confirmar que o pedido cancelado volta a ficar disponível de
verdade (recalculado e reapareceu selecionável, não é só rótulo mudando).
Também Despacho multi-veículo → Emitir, e Cadastros → Cidades. Zero erro
no console em toda a sequência.

## Ainda não verificado (geral)

- Reconciliação com o arquivo `Pedidos.csv` (controle geral) — o pipeline
  hoje importa o formato semanal (`Pedidos_Filtrados_*.csv`), que é o único
  com itens.
- Reprocessamento automático de pedido após corrigir uma pendência (hoje
  exige reimportar; ver aviso na tela de Pendências).
- Import em lote do catálogo de produtos pela tela (hoje só via API/script).

## Setup

### 1. Projeto Supabase
1. Crie um projeto em [supabase.com](https://supabase.com) (gratuito).
2. Em **SQL Editor**, rode os 5 arquivos de `backend/db/migrations/` **em ordem numérica** (0001 a 0005).
3. Em **Project Settings → API**, copie a `Project URL` e a `anon public` key.
4. Em **Authentication → Providers**, confirme que Email está habilitado (padrão).

### 2. Backend
```bash
cd backend
py -m venv .venv
./.venv/Scripts/pip install -r requirements.txt
cp .env.example .env   # preencha SUPABASE_URL e SUPABASE_ANON_KEY
./.venv/Scripts/uvicorn app.main:app --reload
```
`GET http://localhost:8000/health` deve responder `{"supabase_configured": true}`.

Rodar os testes automatizados (não precisam de Supabase — são só lógica pura):
```bash
./.venv/Scripts/pytest tests/ -v
```

### 3. Frontend
```bash
cd frontend
npm install
cp .env.example .env   # mesma URL/anon key do Supabase, + VITE_API_BASE_URL
npm run dev
```

### 4. Primeiro uso
MVP de instância única: não existe tela de criar/entrar em organização.
Qualquer conta criada em `/login` entra automaticamente na única
organização da operação (cria na primeira vez, junta nas seguintes) —
todo o time compartilha os mesmos dados sem passo extra.
1. Crie uma conta em `/login`.
2. Em **Cadastros**, cadastre ao menos um veículo, um eixo com cidades, e os
   produtos do lote que for importar (ou aceite o `Ranking_Top85_Materiais.csv`
   como ponto de partida — importação em lote do catálogo ainda não tem tela
   dedicada; use `POST /products` por item, ou um script simples contra a API).
4. Em **Pedidos**, importe um `Pedidos_Filtrados_Semana_N_Anonimizado.csv`.
5. Em **Montar carga**, escolha eixo/veículo/lote e calcule.

### 5. Despacho multi-veículo (opcional, via API — sem tela ainda)
1. `POST /cities` para cada cidade que os pedidos usam, com `lat`/`lng` reais
   e `is_depot: true` para Crateús (CDD).
2. `POST /cities/distances/rebuild` — calcula e guarda a matriz de distância
   real via OSRM (demora alguns segundos, 1x por cadastro de cidade novo).
3. `POST /dispatch/solve` com `{batch_id, mode}` — roda o VRP sobre todos os
   pedidos prontos do lote, sem travar por eixo.
4. `POST /dispatch/{id}/issue` — reserva os pedidos servidos.

## Decisões que ainda pertencem ao time (não resolvidas em código)
- As 9 cidades sem eixo confirmado no diagnóstico — cadastrar manualmente em
  Cadastros → Eixos quando houver critério.
- As duas categorias de capacidade encontradas (HR/Bongo, Acello 815) não
  cobrem os "quatro caminhões" citados no edital — cadastre a frota real
  quando confirmada.
- Critério de objetivo (`ocupacao_media_kg_m3` vs `valor_total`) — ambos
  implementados e trocáveis por tela, sem mexer em código.

## Estrutura
```
backend/app/
  core/       config, autenticação (validação JWT Supabase)
  services/   parsing, cubagem, pipeline de importação, romaneio/reservas,
              despacho multi-veículo (dispatch.py), org
  optimizer/  policy + solver CP-SAT (single-axis) + validador;
              vrp_solver.py (multi-veículo, OR-tools routing)
  routers/    rotas FastAPI (inclui geo.py e dispatch.py)
  db/migrations/  0001-0002 schema+RLS core; 0003 cidades/distâncias;
                   0004 despacho multi-veículo; 0005 ajuste de reservas
frontend/src/
  auth/       contexto de sessão + rota protegida
  pages/      uma por tela do design (login, pedidos, pendências, montar
              carga, cadastros, romaneio, histórico, onboarding de org)
  lib/        client Supabase + wrapper de API autenticado
```
