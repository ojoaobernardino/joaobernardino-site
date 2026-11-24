#!/usr/bin/env python3
"""Search Console do joaobernardino.com.br direto pela API (mesmo robô da WJR: robo-wos@wos-medicao).
Uso:
  python3 gsc.py                  resumo dos últimos 28 dias (totais, consultas, páginas)
  python3 gsc.py --dias 90        outro período
  python3 gsc.py oportunidades    consultas na posição 5 a 20 (perto de virar clique)
  python3 gsc.py sitemap          estado do sitemap no Google
  python3 gsc.py inspecionar URL  estado de indexação de uma URL
  python3 gsc.py --json ...       saída em JSON (para outros scripts)
A chave fica fora do repositório. Só leitura: este script não envia nem altera nada.
"""
import warnings; warnings.filterwarnings('ignore')
import argparse, datetime, json, os, sys
from google.oauth2 import service_account
from googleapiclient.discovery import build

SITE = 'sc-domain:joaobernardino.com.br'
CHAVE = os.environ.get('GSC_CHAVE', os.path.expanduser('~/wos-medicao/credenciais/robo-wos.json'))
ESCOPO = ['https://www.googleapis.com/auth/webmasters.readonly']

def servico():
    cred = service_account.Credentials.from_service_account_file(CHAVE, scopes=ESCOPO)
    return build('searchconsole', 'v1', credentials=cred, cache_discovery=False)

def periodo(dias):
    fim = datetime.date.today() - datetime.timedelta(days=2)  # o Google atrasa ~2 dias
    return str(fim - datetime.timedelta(days=dias - 1)), str(fim)

def consulta(svc, dias, dimensoes=(), limite=25):
    ini, fim = periodo(dias)
    # pede bastante e ordena aqui: a API desempata cliques iguais em ordem alfabética
    corpo = {'startDate': ini, 'endDate': fim, 'dimensions': list(dimensoes), 'rowLimit': max(limite, 1000)}
    rows = svc.searchanalytics().query(siteUrl=SITE, body=corpo).execute().get('rows', [])
    return sorted(rows, key=lambda r: (-r['clicks'], -r['impressions']))[:limite]

def linha(r):
    return f"{int(r['clicks']):>6} {int(r['impressions']):>7} {r['ctr']*100:>5.1f}% {r['position']:>5.1f}  {r['keys'][0] if r.get('keys') else ''}"

def tabela(titulo, rows):
    print(f"\n{titulo}\ncliques  impr.    CTR   pos.")
    for r in rows: print(linha(r))

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('comando', nargs='?', default='resumo', choices=['resumo', 'oportunidades', 'sitemap', 'inspecionar'])
    p.add_argument('url', nargs='?')
    p.add_argument('--dias', type=int, default=28)
    p.add_argument('--limite', type=int, default=25)
    p.add_argument('--json', action='store_true')
    a = p.parse_args()
    svc = servico()

    if a.comando == 'sitemap':
        out = svc.sitemaps().list(siteUrl=SITE).execute().get('sitemap', [])
        if a.json: return print(json.dumps(out, ensure_ascii=False, indent=1))
        for s in out:
            n = sum(int(c.get('submitted', 0)) for c in s.get('contents', []))
            print(f"{s['path']}  enviado {s.get('lastSubmitted','?')[:10]}  lido {s.get('lastDownloaded','?')[:10]}  URLs {n}  erros {s.get('errors',0)}  avisos {s.get('warnings',0)}")
        return

    if a.comando == 'inspecionar':
        if not a.url: sys.exit('Passe a URL: python3 gsc.py inspecionar https://joaobernardino.com.br/...')
        r = svc.urlInspection().index().inspect(body={'inspectionUrl': a.url, 'siteUrl': SITE, 'languageCode': 'pt-BR'}).execute()
        st = r['inspectionResult'].get('indexStatusResult', {})
        if a.json: return print(json.dumps(r, ensure_ascii=False, indent=1))
        for k in ('verdict', 'coverageState', 'lastCrawlTime', 'googleCanonical', 'robotsTxtState', 'pageFetchState'):
            print(f"{k}: {st.get(k, '-')}")
        return

    ini, fim = periodo(a.dias)
    if a.comando == 'oportunidades':
        rows = [r for r in consulta(svc, a.dias, ['query'], 1000) if 5 <= r['position'] <= 20]
        rows = sorted(rows, key=lambda r: -r['impressions'])[:a.limite]
        if a.json: return print(json.dumps(rows, ensure_ascii=False, indent=1))
        print(f"Consultas na posição 5 a 20, {ini} a {fim}")
        return tabela('Oportunidades (por impressões)', rows)

    total = consulta(svc, a.dias)
    consultas = consulta(svc, a.dias, ['query'], a.limite)
    paginas = consulta(svc, a.dias, ['page'], a.limite)
    if a.json: return print(json.dumps({'periodo': [ini, fim], 'total': total, 'consultas': consultas, 'paginas': paginas}, ensure_ascii=False, indent=1))
    print(f"Search Console · {SITE} · {ini} a {fim}")
    if total:
        t = total[0]; print(f"Cliques {int(t['clicks'])} · Impressões {int(t['impressions'])} · CTR {t['ctr']*100:.1f}% · Posição média {t['position']:.1f}")
    else: print('Sem dados no período.')
    tabela('Consultas', consultas); tabela('Páginas', paginas)

if __name__ == '__main__':
    main()
