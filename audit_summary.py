import contextlib,io,runpy,re,collections,json
from pathlib import Path
with contextlib.redirect_stdout(io.StringIO()):d=runpy.run_path(str(Path(__file__).with_name('audit_data.py')))
weekly,base,catalog=d['weekly'],d['base'],d['catalog']
pat=re.compile(r'^\s*(\d+)\s*-\s*(.*?)\s*\(([\d.,]+)(?:\s+([^()]+))?\)\s*$')
for r in weekly:r['_items']=[pat.match(s).groups() for s in r['Itens_Resumo'].split(' | ')]
validbase=[r for r in base if r['PEDIDO'].strip()]
print('BASE_VALID',len(validbase),'EMPTY',len(base)-len(validbase),'EXTRA_BASE_IDS',len({r['PEDIDO'] for r in validbase}-{r['Pedido'][1:] for r in weekly}))
print('EMPTY_BASE_ROWS',[{k:v for k,v in r.items() if v} for r in base if not r['PEDIDO'].strip()])
axes=[['BURITI DOS MONTES','BARRO VERMELHO','TUCUNS','QUEIMADAS','FILOMENA'],['SUCESSO','TAMBORIL','NOVA RUSSAS','FAZENDA'],['INDEPENDENCIA','ACENTAMENTO SAO JOSE','ADAO'],['IPAPORANGA','PORANGA','ARARENDA','VACA MORTA','CURRAL VELHO','CURRAL DO MEIO'],['NOVO ORIENTE','REALEJO','SANTANA','MONTE NEBO','SANTO ANDRE','QUITERIANOPOLIS','BARRA DOS SIMIOES']]
cities=set(sum(axes,[]))
eligible=[r for r in weekly if r['Cidade']!='CRATEUS' and 'RETIRADA' not in [r['Logistica'],r['Situacao_CSV_Entrega']] and 'CANCELADO' not in [r['Logistica'],r['Situacao']]]
for label,rs in [('todos',weekly),('fora_crateus_sem_retirada_cancelamento',eligible),('eixos_mapeados',[r for r in eligible if r['Cidade'] in cities])]:
 its=[i for r in rs for i in r['_items']]
 print(label,json.dumps({'orders':len(rs),'items':len(its),'unique_products':len(set(i[0] for i in its)),'matched_lines':sum(i[0] in catalog for i in its),'fully_catalogued_orders':sum(all(i[0] in catalog for i in r['_items']) for r in rs),'missing_unit_lines':sum(i[3] is None for i in its),'missing_codes':len(set(i[0] for i in its if i[0] not in catalog)),'statuses':dict(collections.Counter(r['Logistica'] for r in rs))},ensure_ascii=False))
print('UNMAPPED',dict(collections.Counter(r['Cidade'] for r in eligible if r['Cidade'] not in cities)))
print('OPEN_ORDERS',[(r['Pedido'],r['Cidade'],r['Logistica'],all(i[0] in catalog for i in r['_items'])) for r in eligible if r['Logistica']!='ENTREGUE'])
print('CAT_DUP',len(catalog),'CAT_UNUSED',sorted(set(catalog)-set(i[0] for r in weekly for i in r['_items'])))
print('UNITS',dict(collections.Counter(i[3] for r in weekly for i in r['_items'])))
print('JOIN_DISAGREE')
by={r['PEDIDO']:r for r in validbase}
for field,bfield in [('Cidade','CIDADE'),('Logistica','LOGISTICA'),('Situacao_CSV_Entrega','SITUACAO'),('Valor_Pedido','VALOR DO PEDIDO')]:
 dif=[(r['Pedido'],r[field],by[r['Pedido'][1:]][bfield]) for r in weekly if r['Pedido'][1:] in by and r[field].strip()!=by[r['Pedido'][1:]][bfield].strip()]
 print(field,len(dif),dif[:8])
print('MISSING_JOIN',[(r['Pedido'],r['Cidade'],r['Logistica']) for r in weekly if r['Pedido'][1:] not in by])
