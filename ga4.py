#!/usr/bin/env python3
"""GA4 do joaobernardino.com.br direto pela API (mesmo robô da WJR: robo-wos@wos-medicao).
Uso:
  python3 ga4.py                          resumo dos últimos 28 dias (totais, páginas, origens)
  python3 ga4.py --dias 90                outro período
  python3 ga4.py --de 2026-10-01 --ate 2026-10-31   período exato
  python3 ga4.py paginas /blog/indicacoes/          páginas que contêm esse trecho
  python3 ga4.py origens /blog/indicacoes/          de onde veio quem viu essas páginas
  python3 ga4.py --json ...               saída em JSON (para outros scripts)
A chave fica fora do repositório. Só leitura.
"""
import warnings; warnings.filterwarnings('ignore')
import argparse, datetime, json, os
from google.oauth2 import service_account
from googleapiclient.discovery import build

PROPRIEDADE = 'properties/553655452'  # joaobernardino.com.br (G-5MSB6QLXN0)
CHAVE = os.environ.get('GA4_CHAVE', os.path.expanduser('~/wos-medicao/credenciais/robo-wos.json'))
ESCOPO = ['https://www.googleapis.com/auth/analytics.readonly']
METRICAS = ['screenPageViews', 'sessions', 'totalUsers']

def servico():
    cred = service_account.Credentials.from_service_account_file(CHAVE, scopes=ESCOPO)
    return build('analyticsdata', 'v1beta', credentials=cred, cache_discovery=False)

def relatorio(svc, ini, fim, dimensoes=(), trecho=None, limite=25):
    corpo = {'dateRanges': [{'startDate': ini, 'endDate': fim}],
             'dimensions': [{'name': d} for d in dimensoes],
             'metrics': [{'name': m} for m in METRICAS],
             'orderBys': [{'metric': {'metricName': 'screenPageViews'}, 'desc': True}], 'limit': limite}
    if trecho:
        corpo['dimensionFilter'] = {'filter': {'fieldName': 'pagePath', 'stringFilter': {'matchType': 'CONTAINS', 'value': trecho}}}
    r = svc.properties().runReport(property=PROPRIEDADE, body=corpo).execute()
    return [{'chave': ' / '.join(d['value'] for d in x.get('dimensionValues', [])),
             **{m: int(v['value']) for m, v in zip(METRICAS, x['metricValues'])}} for x in r.get('rows', [])]

def tabela(titulo, rows):
    print(f"\n{titulo}\n views sessões usuários")
    for r in rows: print(f"{r['screenPageViews']:>6} {r['sessions']:>7} {r['totalUsers']:>8}  {r['chave']}")
    if not rows: print('  (sem dados)')

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('comando', nargs='?', default='resumo', choices=['resumo', 'paginas', 'origens'])
    p.add_argument('trecho', nargs='?', help='trecho do caminho, ex.: /blog/indicacoes/')
    p.add_argument('--dias', type=int, default=28)
    p.add_argument('--de'); p.add_argument('--ate')
    p.add_argument('--limite', type=int, default=25)
    p.add_argument('--json', action='store_true')
    a = p.parse_args()
    hoje = datetime.date.today()
    ini = a.de or str(hoje - datetime.timedelta(days=a.dias - 1)); fim = a.ate or str(hoje)
    svc = servico()
    out = {'periodo': [ini, fim], 'total': relatorio(svc, ini, fim, trecho=a.trecho)}
    if a.comando in ('resumo', 'paginas'): out['paginas'] = relatorio(svc, ini, fim, ['pagePath'], a.trecho, a.limite)
    if a.comando in ('resumo', 'origens'): out['origens'] = relatorio(svc, ini, fim, ['sessionSource', 'sessionMedium'], a.trecho, a.limite)
    if a.json: return print(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"GA4 · joaobernardino.com.br · {ini} a {fim}" + (f" · páginas com '{a.trecho}'" if a.trecho else ''))
    t = out['total'][0] if out['total'] else None
    print(f"Views {t['screenPageViews']} · Sessões {t['sessions']} · Usuários {t['totalUsers']}" if t else 'Sem dados no período.')
    if 'paginas' in out: tabela('Páginas', out['paginas'])
    if 'origens' in out: tabela('Origens (fonte / meio)', out['origens'])

if __name__ == '__main__':
    main()
