import sys,zipfile,csv,io,re,collections,json
from pypdf import PdfReader
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
z=zipfile.ZipFile(r'C:\Users\joaom\Downloads\Pasta CSV-20260915T232629Z-1-001.zip')
def text(n):
 b=z.read(n)
 try:return b.decode('utf-8-sig')
 except:return b.decode('cp1252')
def rows(n,d):return list(csv.DictReader(io.StringIO(text(n)),delimiter=d))
weekly=[]
for n in sorted(z.namelist()):
 if 'Semana_' in n:
  rs=rows(n,';');weekly+=rs
  print('WEEK',n,len(rs),'dates',collections.Counter(r['Data'][-4:] for r in rs),'status',dict(collections.Counter(r['Logistica'] for r in rs)))
rank=rows(next(n for n in z.namelist() if 'Ranking_' in n),';');catalog={r['Codigo']:r for r in rank}
base=rows(next(n for n in z.namelist() if 'Vendas_' in n),',')
print('TOTAL',len(weekly),'unique',len({r['Pedido'] for r in weekly}),'base',len(base),'unique_base',len({r['PEDIDO'] for r in base}))
for field in ['Situacao','Logistica','Situacao_CSV_Entrega','Cidade']:print('WEEKLY',field,dict(collections.Counter(r[field] for r in weekly)))
for field in ['SITUACAO','LOGISTICA','FATURAMENTO']:print('BASE',field,dict(collections.Counter(r[field] for r in base)))
print('CATALOG',len(rank),'estimated',dict(collections.Counter(r['Dado_Estimado'] for r in rank)))
print('CATALOG_ROWS')
for r in rank:print(r['Codigo'],r['Produto'], '|',r['Unidade_Venda'],'|',r['Peso_kg'],'|',r['Volume_m3'])
print('ROUTES',text(next(n for n in z.namelist() if 'ROTAS E' in n)))
for n in z.namelist():
 if n.endswith('.pdf'):
  print('EXAMPLE',n)
  for p in PdfReader(io.BytesIO(z.read(n))).pages:print(p.extract_text())
pat=re.compile(r'^\s*(\d+)\s*-\s*(.*?)\s*\(([\d.,]+)\s+([^()]+)\)\s*$')
missing=collections.Counter();bad=[];count_mismatch=[];eligible=[];all_items=[]
for r in weekly:
 items=r['Itens_Resumo'].split(' | ')
 if len(items)!=int(r['Qtd_Itens']):count_mismatch.append(r['Pedido'])
 parsed=[]
 for s in items:
  m=pat.match(s)
  if not m:bad.append((r['Pedido'],s));continue
  parsed.append(m.groups());all_items.append(m.groups())
 r['_items']=parsed
 if r['Cidade'].strip().upper()!='CRATEUS' and 'RETIR' not in r['Situacao_CSV_Entrega'].upper() and 'CANCEL' not in r['Situacao'].upper():eligible.append(r)
for label,rs in [('all',weekly),('outside_no_pickup_cancel',eligible)]:
 its=[i for r in rs for i in r['_items']]
 missing=collections.Counter(i[0] for i in its if i[0] not in catalog)
 complete=[r for r in rs if all(i[0] in catalog for i in r['_items']) and len(r['_items'])==int(r['Qtd_Itens'])]
 print('COVERAGE',label,'orders',len(rs),'lines',len(its),'unique_codes',len(set(i[0] for i in its)),'matched_lines',sum(i[0] in catalog for i in its),'full_orders',len(complete),'missing_unique',len(missing),'top_missing',missing.most_common(15))
 print('eligible_status',dict(collections.Counter(r['Logistica'] for r in rs)))
print('PARSE_BAD',bad,'ITEM_COUNT_MISMATCH',count_mismatch)
baseby=collections.defaultdict(list)
for r in base:baseby[r['PEDIDO']].append(r)
print('DUP_BASE',[(k,len(v)) for k,v in baseby.items() if len(v)>1])
print('JOIN_MISSING',[r['Pedido'] for r in weekly if r['Pedido'].removeprefix('L') not in baseby])
for r in weekly:
 if not r['Data'].endswith('2026'):print('DATE_ANOMALY',r['Pedido'],r['Data'],[(b['DATA'],b['DATA/HORA FATURAMENTO']) for b in baseby[r['Pedido'].removeprefix('L')]])

