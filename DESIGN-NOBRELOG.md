# NobreLOG — design completo do MVP

Versão 1 • 15/09/2026 • Design proposto, ainda não implementação do produto.

## 1. O produto em uma frase
Uma central de expedição que recebe pedidos, confere os dados, escolhe uma combinação dentro da capacidade de um veículo e emite um romaneio que o coordenador consegue conferir e assinar.

O fluxo diário é: Pedidos → Pendências → Montar carga → Conferir → Romaneio. Veículos, produtos e eixos são cadastros editáveis. Cada novo lote repete o processo, sem alterar o código.

## 2. Refinamentos sobre a proposta do Jay

| Tema | Decisão refinada |
|---|---|
| Configuração externa | Manter. Cadastros editáveis pela interface, persistidos em SQLite; JSON serve para importar/exportar configurações. O coordenador não precisa editar arquivos. |
| Motor | Manter OR-Tools CP-SAT. É uma biblioteca reutilizada, sobre a qual implementamos regras específicas do negócio. |
| Ordem das cidades | O edital define grupos de cidades, não uma sequência definitiva. Propor sequência inicial explicitamente marcada e permitir ordenar antes de emitir. |
| Carga inversa à descarga | Orientação de separação por parada, dependente do acesso à carroceria. Não comprova arranjo 3D, estabilidade, empilhamento ou compatibilidade física. |
| Open source | Não afirmar que não existe solução pronta no mundo. As fontes verificadas sustentam a escolha do componente, não uma conclusão universal sobre o mercado. |
| Localidades sem eixo | No recorte auditado: 12 pedidos em oito localidades. Difere das nove citadas pelo Jay possivelmente pelo filtro. Não misturar universos. |
| Frota | Existem duas categorias com capacidades informadas; não um cadastro inequívoco dos quatro veículos. Não inventar a distribuição. |
| Dados estimados | 71/85 produtos têm flag de estimativa. Limites são garantidos contra os valores usados no cálculo; não contra medidas reais desconhecidas. |
| IA | O MVP usa otimização matemática. Não requer ML ou chamada a modelo de linguagem. Confirmar se existe regra adicional do evento sobre IA, ausente nos materiais examinados. |

O link do artefato não abriu. A revisão usa o texto copiado pelo usuário, o PDF, os 12 slides e a auditoria local.

## 3. Escopo de entrega

### Obrigatório
- Importar os formatos fornecidos e um CSV normalizado documentado para novos lotes.
- Explicar filtros, correções e pendências, preservando originais.
- Cruzar itens por código e converter para uma unidade física comum.
- Selecionar pedidos inteiros de um eixo para um veículo.
- Mostrar separadamente kg, m³, ocupações, valor e pedidos não selecionados.
- Propor e permitir ajustar ordem de descarga por cidade.
- Imprimir romaneio em A4, com identificação, revisão, totais e assinatura.
- Editar frota, catálogo e eixos pela interface e reprocessar.

### Bônus após fechar o fluxo obrigatório
- Alocação conjunta entre veículos e eixos.
- Diagnóstico da dimensão com maior utilização relativa; não confundir isso com prova de que ela é o único impedimento a outro pedido.
- Comparação reproduzível com uma regra simples de seleção por valor.

### Depois do evento
Integração direta ao ERP, autenticação corporativa, custos de transporte, previsão de demanda, otimização de trajetos e arranjo 3D. Não são dependências da entrega inicial.

## 4. Telas e comportamento

### 4.1 Pedidos
Cabeçalho com lote, data de referência e modo: Simulação histórica ou Operação. Modo sempre visível, inclusive na impressão.
Botão Importar pedidos. Contagens por destino mutuamente exclusivo: disponíveis, pendentes de dados, excluídos por regra, já entregues (operação) e comprometidos em outro plano. Uma aba secundária mostra o histórico das importações.
Tabela: pedido, cidade/eixo, status logístico, valor, peso, volume e situação dos dados. Peso/volume desconhecidos aparecem como Não calculado, nunca zero. Busca por ID/cidade e filtros.
Ao abrir um pedido, mostrar itens e conta de conversão, por exemplo: 23 m² ÷ 2,30 m²/caixa = 10 caixas × 28,28 kg = 282,8 kg.

### 4.2 Pendências
Fila agrupada por produto sem ficha, unidade ausente, cidade sem eixo, data inconsistente ou saldo parcial desconhecido. Priorizar pelo número de pedidos afetados.
Painel lateral com valor original, proposta de correção, fonte, responsável e motivo. Salvar gera evento de auditoria e reprocessa somente os pedidos afetados.
Correções determinísticas, como decimal brasileiro e remoção de espaços, são automáticas e registradas. Decisões sem evidência exigem preenchimento; sem invenção silenciosa.
Pode calcular o subconjunto válido. A tela mostra quantos pedidos ficaram indisponíveis por dados, sem escondê-los.

### 4.3 Montar carga — tela principal
Topo: eixo, veículo, data da viagem e botão Calcular carga. Somente veículos ativos e sem conflito na viagem.
Área central: lista de pedidos elegíveis; após o cálculo, abas Selecionados e Não selecionados. Lista pendente de dados continua acessível.
Coluna direita: duas barras independentes de ocupação, valores absolutos/capacidades e total comercial. Ao trocar veículo, invalidar resultado anterior e pedir recálculo.
Rodapé: sequência de cidades, com botões subir/descer acessíveis por teclado. Inicialmente marcada Proposta a conferir. Sem mapa obrigatório.
Resultado textual: Melhor solução comprovada para o critério adotado ou Solução válida; busca encerrada pelo limite de tempo. Não exibir Melhor possível sem prova.
Ação Conferir romaneio somente após cálculo válido e ordem confirmada. Nenhuma seleção manual pode contornar os limites.

### 4.4 Romaneio
Prévia A4 branca e botão Imprimir / salvar PDF pelo navegador. Não depender de serviço de PDF externo.
Cabeçalho: ID/revisão, data, eixo, identificação do veículo, modo e lote.
Tabela por parada: ordem, cidade, pedido, valor, kg e m³. Seção de detalhes dos itens para separação, em páginas adicionais quando necessário.
Rodapé: totais, capacidade, ocupação em cada dimensão, indicação de estimativas, data de emissão e campo de assinatura do coordenador. Nunca incluir endereço pessoal dos PDFs de exemplo em demonstração pública.
Documento emitido guarda um retrato das configurações e dos pedidos usados. Editar veículo depois não altera um romaneio antigo.

### 4.5 Cadastros
Três abas, não três sistemas separados:
- Frota: identificação, capacidade útil kg/m³, ativo, fonte e data da ficha. Editar um veículo não altera outro do mesmo modelo.
- Eixos: nome, localidades e sequência sugerida; aliases explícitos para grafias. Acentos/espaços podem ser normalizados, mas localidades ambíguas não são associadas automaticamente.
- Produtos: código textual, unidade de venda, unidade de carga, fator de conversão, peso/volume por unidade de carga, faixas, origem e estimativa. Campo vazio continua vazio.

### 4.6 Histórico
Lista de planos com modo, data, veículo, eixo, totais e estado: rascunho, emitido, cancelado, concluído. Reabrir mostra o retrato emitido, não recalcula silenciosamente.
No MVP, emissão reserva pedidos em transação. Cancelamento libera a reserva. Conclusão só marca entregue mediante ação explícita; imprimir não equivale a entregar.

### Estados comuns
Vazio: explicar primeiro passo. Processando: feedback de andamento sem inventar percentuais. Erro de arquivo: apontar coluna/linha e manter lote anterior intacto. Falha de cálculo: preservar entrada e permitir repetir. Nenhum pedido cabe: resultado vazio explicado, sem romaneio de viagem vazia. Falha de salvamento: não mostrar sucesso. Mudança de dados: resultado desatualizado e nova revisão exigida.

## 5. Direção visual
Estética de central de expedição: fundo marfim #F4F2EA, texto carvão #202821, verde profundo #244B3C e amarelo #EAC449 reservado às ações principais. Vermelho indica impedimento; âmbar indica estimativa/pendência. Sempre usar rótulo junto da cor.
Títulos: Georgia no protótipo offline; corpo: Trebuchet MS; números alinhados e tabulares. Ícones discretos com texto. Bordas finas, pouca sombra, bom contraste, navegação lateral compacta e tabelas legíveis.
O elemento principal é a dupla régua de ocupação: peso e volume sempre lado a lado. Não misturar as duas em uma porcentagem física única.
Desktop prioritário para expedição. Tablet com colunas empilhadas. Em celular, filtros empilham e tabelas podem rolar horizontalmente dentro do painel. Foco visível, labels em inputs, ações por teclado e respeito a movimento reduzido. Impressão elimina navegação e usa preto sobre branco.

## 6. Regras dos dados
1. Preservar arquivo bruto, hash, linha de origem e perfil de importação.
2. Detectar delimitador/codificação e validar campos; nunca cortar a linha de CSV por vírgula manualmente.
3. Normalizar IDs por regra explícita: prefixo L somente no adaptador conhecido; preservar zeros e ID original.
4. Importação repetida é idempotente pelo hash. Arquivo alterado vira nova revisão, com conflito por pedido mostrado e substituição explícita.
5. Filtrar Crateús, retiradas e cancelados. Avaliar os campos corretos: cancelamento aparece em Logistica.
6. Operação exclui entregues; parcial exige saldo por item. Simulação reproduz lote histórico explicitamente escolhido; não muda status real nem mistura pedidos de datas futuras no cenário.
7. Associar localidades por cadastro. Ausência bloqueia apenas o pedido afetado.
8. Converter por produto. MT não tem interpretação universal. Piso usa área/caixa; tubos usam comprimento/barra; pacotes usam peças/pacote quando documentado.
9. Caixas inteiras: não arredondar pedido para baixo. Se o quociente não for inteiro na tolerância configurada, exigir política de embalagem confirmada. Arredondar para cima, se autorizado, registra diferença entre quantidade vendida e separada.
10. Estimativas: modo nominal usa valor documentado; modo conservador usa limite superior disponível. Margem sem fundamento é hipótese visível, não garantia física. Dado ausente bloqueia; estimativa válida não bloqueia automaticamente.
11. Data inválida não vira data de hoje. A discrepância de 2014 tem conflito adicional com dia de faturamento; registrar pendência e não usar para desempate por antiguidade.
12. Pedidos inteiros no MVP. Nunca descartar um item sem cubagem e carregar o restante como se fosse o pedido completo.

## 7. Motor matemático

### Entrada e restrições
Recebe apenas pedidos validados do eixo selecionado e a capacidade da viagem. Cada pedido i tem peso w_i, volume v_i e variável binária x_i (entra ou não entra).

    soma(w_i * x_i) <= W
    soma(v_i * x_i) <= V
    x_i pertence a {0,1}

Não há obrigação de carregar todos os pedidos. Pedido sozinho acima do limite recebe motivo próprio. Restrições futuras de prioridade obrigatória são opcionais e, quando incompatíveis, geram conflito explícito.

### Critério proposto
O edital não fornece fórmula de agregação. Padrão proposto: maximizar a média das ocupações de peso e volume, com importância igual. Isto é decisão nossa a declarar à banca, não regra oficial.

    score = 0,5 * peso_total/W + 0,5 * volume_total/V

A tela mostra ambas as ocupações, não só score. Empate primário: atender maior número de pedidos; empate seguinte: maior valor total. Antiguidade só entra quando as datas de referência forem confiáveis e a política for habilitada. Não permitir que desempates reduzam a qualidade do objetivo principal.

### Implementação exata e validação
CP-SAT usa inteiros. Usar Decimal na leitura, gramas para peso e cm³ para volume. Converter contribuição do pedido para cima e capacidade para baixo quando houver precisão adicional, registrando o ajuste. Não arredondar carga para baixo.
Com W,V inteiros, maximizar V * soma(w_i*x_i) + W * soma(v_i*x_i) é equivalente ao score acima para um veículo fixo. Reduzir coeficientes por fatores comuns e verificar limites inteiros do modelo; rejeitar escalas que possam transbordar. Não aproximar silenciosamente.
Resolver etapas de desempate somente se a etapa anterior tiver ótimo comprovado. Fixar seu valor antes de prosseguir. Usar orçamento total de 10 segundos inicialmente, configurável e medido no hardware real; é meta, não tempo já comprovado.
Guardar status, duração, versão, seed, número de workers, objetivo e limite superior. FEASIBLE não é OPTIMAL. UNKNOWN não prova impossibilidade. Resultado vazio não deve ser confundido com INFEASIBLE: sem pedidos obrigatórios, vazio normalmente é solução possível.
Validador independente do solver recalcula totais em Decimal e verifica limite, integridade de pedidos, duplicatas, eixo e reservas. Falha impede emissão.

### Motivos de não seleção
Distinguir: sem cadastro; outro eixo; status excluído; pedido sozinho excede limite; não selecionado na combinação calculada. Só afirmar Não cabe no espaço restante depois de testar a adição contra a carga escolhida. Esse teste não prova que não exista outra combinação.

### Referência comparativa
Baseline: ordenar por valor decrescente e incluir cada pedido inteiro se ainda couber em ambos os limites. Mesmo lote elegível, fichas e capacidades para baseline e otimizador. Identificar como regra de referência, não reprodução comprovada da prática humana. Medir tempo total importação→romaneio e tempo do solver separadamente. Não inventar ganho percentual.

## 8. Ordem de descarga
Configurar sequência de localidades por eixo; o coordenador pode ajustar e confirmar. Usar só cidades atendidas no plano, preservando ordem relativa. Pedidos da mesma cidade agrupados e ordenados por ID no MVP.
Não alegar menor quilometragem sem distâncias e avaliação de trajetos. Sequência fixa confirmada é uma regra determinística; propor a sequência inicial ainda é uma decisão operacional.
A sugestão de separação em ordem inversa depende do tipo de acesso ao veículo. Romaneio descreve descarga; não certifica arranjo espacial.

## 9. Arquitetura proposta
React + TypeScript para interface; Python + FastAPI para API; OR-Tools CP-SAT para cálculo; SQLite para persistência local. Uma aplicação pequena, módulos separados, sem microserviços ou fila externa no MVP. Frontend compilado servido pela mesma origem da API. Sem API paga obrigatória.

    Navegador
        → API
            → Importação e auditoria
            → Validação e conversão
            → Seleção CP-SAT
            → Validador independente
            → Plano versionado e impressão
        ↔ SQLite + originais em diretório local controlado

Rodar cálculo com concorrência limitada fora do event loop da API. Clientes recebem job ID e consultam estado. Protótipo visual separado, sem fingir integração ao motor.

### Entidades
- ImportBatch: hash, arquivo, perfil, modo, referência, estado e resumo.
- Order / OrderItem: origem, ID externo, status, cidade, itens, quantidades e valores.
- ProductSpec: unidade, conversão, kg/m³, faixas, fonte, versão.
- Vehicle: ID, nome, capacidades úteis, ativo e versão.
- Axis / AxisCity: ID, localidades, aliases, ordem proposta.
- Issue / AuditEvent: campo, antes/depois, motivo, fonte e responsável.
- Plan / PlanOrder: retrato de entradas, viagem, solver, sequência, totais, revisão, estado.
- Reservation: pedido, viagem/plano e estado; unicidade para impedir dupla alocação ativa.

### Contrato mínimo de API
POST /imports: arquivos + perfil + modo + referência; retorna lote e resumo.
GET /batches/{id}/orders: filtros e paginação.
GET /batches/{id}/issues; PATCH /issues/{id}: correção com motivo/fonte.
GET/POST/PATCH /vehicles, /axes, /products: cadastros versionados.
POST /plans/solve: batch_id, axis_id, vehicle_id, departure_date, expected_versions, policy; retorna job_id.
GET /jobs/{id}: pending/running/succeeded/failed e plan_id.
GET /plans/{id}: selecionados, não selecionados, evidências e versões.
PATCH /plans/{id}/stops: sequência antes da emissão.
POST /plans/{id}/issue: valida versões e cria reservas em transação; conflito retorna 409.
POST /plans/{id}/cancel: libera reservas; GET /plans/{id}/print: retrato para impressão.
Qualquer alteração posterior à solução invalida revisão pendente. Frontend nunca é fonte de verdade para totais ou permissões de emissão.

## 10. Bônus multieixo
Introduzir x[i,t] para pedido/veículo e y[t,e] para veículo/eixo. Cada pedido em no máximo um veículo; cada veículo atende no máximo um eixo por viagem; x depende de y; kg/m³ limitados por veículo. Configurar disponibilidade, sem inventar quatro instâncias.
O objetivo multiveículo exige política própria: somar ocupações normalizadas pode favorecer veículos menores e não maximiza carga absoluta nem cobertura de eixos. Avaliar cobertura de eixos com demanda e atrasos como prioridades explícitas, seguidas de ocupação. Não reutilizar silenciosamente o score monoveículo.
Sem simular múltiplas viagens por dia sem durações. Primeiro resultado deste bônus deve mostrar eixos não atendidos e motivos.

## 11. Validação que prova a entrega
- Todos os 688 pedidos e 1.981 itens reconhecidos, com reconciliação de contagens após filtros.
- Conversão demonstrada para piso, tubo, pacote e unidade ausente.
- Limites: exatamente no limite é aceito; acima por uma unidade de precisão é rejeitado.
- Casos pequenos comparados com enumeração exaustiva para provar objetivo e desempates.
- Reimportação não duplica pedidos; emitir dois planos para o mesmo pedido gera conflito.
- Capacidade alterada muda solução e não reescreve plano antigo.
- Pedido sem cubagem aparece pendente, não pesa zero.
- Operação não inclui entregues; simulação é rotulada e não reserva pedidos operacionais.
- Falha/timeout não resulta em falso sucesso ou promessa de ótimo.
- Impressão legível em A4 com várias páginas, totais e assinatura.
- Teste do fluxo completo no lote definido pela organização e medição da meta de cinco minutos.

## 12. Trabalho para quatro pessoas
Plano relativo a partir do início da implementação; ajustar ao tempo restante real. Reservar as últimas duas horas antes das 8h para estabilização e apresentação.

| Pessoa | Entrega principal | Primeiro marco |
|---|---|---|
| 1 | Dados, conversões e pendências | Lote normalizado com reconciliação |
| 2 | Solver e validador independente | Solução de exemplo conferida por enumeração |
| 3 | Interface e cadastros | Navegação e formulários ligados ao contrato |
| 4 | API/persistência, integração e romaneio | Fluxo vertical salva e imprime uma carga |

Primeiros 30 minutos: acordar schema, unidade física e fixture comum. Até 2h: fluxo pequeno ponta a ponta com exemplo sintético rotulado. Até 4h: dados reais e pendências. Até 6h: impressão, troca de frota e testes. Bônus só após fluxo completo validado. Essas são metas de execução, não entregas já concluídas.

## 13. Decisões propostas e questões externas
Decisões de design já propostas: pedidos inteiros, score equilibrado, cadastros pela UI, SQLite local, ausência não vira zero, emissão versionada e simulação separada.
Perguntas à organização não bloqueiam o desenho: lote/status exato da avaliação; política de produtos sem ficha; capacidades úteis dos quatro veículos; fracionamento de caixas e saldo parcial; eventual exigência adicional de IA.
Enquanto isso: usar capacidades fornecidas identificadas como referências, demonstrar subconjunto válido com cobertura explícita e não alegar que pendências foram resolvidas.

## 14. Fontes verificadas
Consultadas em 15/09/2026. Não foi feita varredura exaustiva do mercado.
- OR-Tools, licença Apache-2.0 e componentes: https://github.com/google/or-tools
- Modelo de múltiplas mochilas: https://developers.google.com/optimization/pack/multiple_knapsack
- CP-SAT, inteiros e estados de solução: https://developers.google.com/optimization/cp/cp_solver
- Knapsack: https://developers.google.com/optimization/pack/knapsack
- VROOM: https://github.com/VROOM-Project/vroom — API admite capacidades multidimensionais e elegibilidade por skills: https://github.com/VROOM-Project/vroom/blob/master/docs/API.md
- PyVRP: https://github.com/PyVRP/PyVRP — inclui múltiplas dimensões de carga e outras restrições de roteamento.
- React: https://react.dev/ ; FastAPI: https://fastapi.tiangolo.com/

VROOM/PyVRP são alternativas reais se roteamento se tornar central. Para o escopo atual, CP-SAT permite expressar seleção, eixo e políticas diretamente, com menos componentes. Bin packing 3D trata também posição/dimensões físicas, escopo que estes dados não permitem certificar.

## 15. Artefatos desta revisão
- DESIGN-NOBRELOG.md: especificação proposta do produto e da implementação.
- design-preview.html: prévia navegável offline com seis telas e sete pedidos fictícios (seis calculáveis e um pendente). Não é o MVP integrado.
- Na prévia funcionam navegação, busca, comparação exaustiva das combinações do exemplo, troca de veículo, alteração de capacidade em memória, inversão da sequência e impressão.
- Importação real, persistência, CRUD completo e integração OR-Tools ainda não estão implementados.
- Verificação executada no Edge headless: cálculo, mudança de capacidade (seleção passou de três para um pedido no cenário testado), invalidação de resultado antigo, busca, navegação, geração de impressão e ausência de erros JavaScript. Layout de 1440 px e 390 px revisado; sem transbordamento da página no cenário móvel testado.
