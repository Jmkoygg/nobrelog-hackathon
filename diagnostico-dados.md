# Diagnóstico dos dados NobreLOG

Análise em 15/09/2026. Fontes: ZIP fornecido, PDF do desafio e 12 slides enviados. Originais preservados. Contagens por registro, sem inferir dados ausentes. Nenhuma pesquisa externa nem reidentificação realizada.

## Inventário e cobertura
- Quatro arquivos semanais: 149, 165, 172 e 202 pedidos. Total: 688 IDs distintos.
- 1.981 linhas de itens, com 672 códigos distintos. Qtd_Itens coincide com a quantidade de linhas em todos os pedidos.
- Catálogo: 85 códigos únicos, todos utilizados no conjunto. 71 registros marcados SIM em Dado_Estimado.
- 1.109 linhas encontram código no catálogo; 872 não encontram. São 587 códigos ausentes.
- 331 pedidos têm todos os códigos no catálogo. Isso não comprova conversões e cubagem válidas.
- Controle geral: 715 registros, dos quais quatro sem número de pedido após remover espaços. Dos 711 com número, 25 não aparecem nos arquivos semanais; dois pedidos semanais não aparecem no controle. Os 686 IDs cruzados não divergem em cidade, logística, tipo de entrega ou valor.

## Recorte do desafio
Exclusão por cidade CRATEUS, retirada em qualquer dos campos de logística/tipo, cancelamento em logística/situação.
- Sobram 93 pedidos e 330 linhas de itens, com 164 códigos distintos.
- 217 linhas encontram código no catálogo (65,8%); faltam 103 códigos distintos nas 113 linhas restantes.
- 46 pedidos com todos os códigos no catálogo; 47 com pelo menos um código ausente.
- 84 pedidos ENTREGUE, sete AGENDADA, um PROGRAMADO e um PARCIAL. Não tratar os 93 como pedidos abertos reais.
- Mapeamento literal pelas localidades da planilha de rotas: 81 pedidos, dos quais 39 têm todos os códigos no catálogo.
- 12 pedidos em oito localidades sem associação explícita: Rosario (1), Lagoa das Pedras (1), Sao Goncalo (2), Pau de Oleio (1), Umburana (1), Ibiapaba (3), Sitio Gira Sol (1), Vila Graca (2). Confirmar com coordenação, sem atribuição arbitrária.
- Dos nove não entregues no recorte, seis têm todos os códigos no catálogo, incluindo o PARCIAL. Quantidade restante do pedido parcial não foi identificada nesta auditoria.

## Qualidade e conversões
- 29 linhas sem unidade no conjunto; dez no recorte de 93. Código e quantidade são recuperáveis, mas a unidade ausente deve permanecer sinalizada.
- Unidades informadas: UN (1.387), MT (531), PC (13), PEC (5), KG (14), M2 (1), SC (1).
- MT aparece tanto em pisos quanto em tubos. A conversão depende do produto: área por caixa para pisos; metros por barra para tubos. Não há conversão global segura para MT.
- Código 21246: caixa de 2,30 m², 28,28 kg/caixa. Exemplo de cálculo: 23 m² correspondem a dez caixas e 282,8 kg. Volume estimado precisa manter essa marcação.
- Há faixas em peso/volume e área por caixa. Ex.: 15157 tem 18–19 kg e 0,020–0,022 m³; 23387 tem 2,18–2,20 m² por caixa. Não simplesmente concatenar/remover caracteres e tratar o resultado como número.
- Embalagens de 100 peças e barras de seis metros exigem conferir unidade comercial versus unidade da ficha.
- Data do L12609909: 26/08/2014 no semanal e 26/08/14 no controle, com faturamento em 24/08/2026. Data suspeita; trocar apenas o ano não resolve a divergência de dia. Preservar original e documentar a política de correção.
- Campos Situacao e Situacao_CSV_Entrega têm significados distintos. Cancelamentos aparecem em Logistica; filtrar somente Situacao perde casos.
- Controle geral usa vírgula como delimitador; semanais e catálogo usam ponto e vírgula. Valores monetários e decimais usam formato brasileiro.

## Frota
Planilha de rotas mistura agenda de coleta, rotas, totais financeiros e bloco de capacidade. Não importar como tabela retangular única de veículos.
- HR / BONGO: 1.700 kg e 2,1793 m³.
- ACELLO 815: 4.800 kg e 2,4543 m³.
- Motos: fora do desafio.
O bloco está rotulado Capacidade utilizada. O enunciado o apresenta como capacidade da frota: confirmar significado e capacidades úteis. Não há cadastro individual inequívoco dos quatro caminhões. Não inventar quantidades por modelo.

## Implicações para o produto
1. Importação repetível com trilha de correções e pendências.
2. Cadastro editável de veículos, produtos, conversões e localidades/eixos.
3. Separar simulação histórica de operação com pedidos abertos. Identificar lote, data de referência e política de seleção.
4. Impedir a liberação de pedido com peso/volume desconhecido; listar motivo e permitir completar cadastro. Nunca imputar zero silenciosamente.
5. Manter valor nominal, faixa e origem das estimativas. Limites matemáticos respeitados com estimativas não provam peso/volume reais medidos.
6. Confirmar política de caixas fracionadas e pedidos parciais; evitar arredondamentos silenciosos.
7. Emitir romaneio com ocupação separada por kg e m³ e justificativa dos pedidos não alocados.
8. Demonstrar mudança de frota e reprocessamento de novos lotes, sem fixar o sistema em agosto.

## Perguntas prioritárias à organização
- Qual lote/status será usado na avaliação: reprodução histórica ou somente pedidos abertos?
- Qual política aceita para produtos sem cubagem? Existe cadastro complementar autorizado?
- Quais são os quatro veículos e suas capacidades úteis? Valores de m³ representam capacidade total ou utilizada?
- Como tratar pedidos parciais, caixas fracionadas e localidades sem eixo explícito?

## Privacidade observada
Os PDFs de exemplo ocultam nome, CPF e telefone do cliente, mas mantêm endereços. Não reproduzir esses endereços em demonstração pública. A descrição de anonimização do material não equivale a remoção de todos os campos pessoais.

## Limites da análise
Diagnóstico de estrutura, cobertura e consistência. Não foi realizada validação externa das fichas técnicas, cálculo definitivo de cargas, otimização ou prova de arranjo físico tridimensional. Nenhuma capacidade ausente foi inventada. Os scripts locais permitem reproduzir a investigação; audit_data.py contém resultados exploratórios de parser estrito, superados pelas contagens finais de audit_summary.py e deste relatório.
