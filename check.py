#!/usr/bin/env python3
"""Portões de qualidade do joaobernardino.com.br (v2, 29/09/2026). Reprova a publicação se algo estiver fora.
Roda depois do build.py:  python3 build.py && python3 check.py
Cobre: home, /linktree/ e tudo que o gerador escreve. A seção privada /blog/altive/ tem regra própria (sem SEO).
"""
import re, json, sys, pathlib
from collections import Counter
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent
SITE = 'https://joaobernardino.com.br'
MAX_HTML_KB = 120
errors, warns = [], []
def err(m): errors.append(m)
def warn(m): warns.append(m)

pages = {}
for idx in ROOT.rglob('index.html'):
    rel = idx.parent.relative_to(ROOT)
    if rel.parts[:1] in (('.git',), ('.cache',), ('templates',), ('node_modules',)):
        continue
    url = '/' if str(rel) == '.' else '/' + str(rel).replace('\\', '/') + '/'
    pages[url] = idx.read_text(encoding='utf-8')
private = {u: s for u, s in pages.items() if u.startswith('/blog/altive/')}
public = {u: s for u, s in pages.items() if u not in private}
redirects = {l.split()[0] for l in (ROOT / '_redirects').read_text().splitlines() if l and not l.startswith('#')} if (ROOT / '_redirects').exists() else set()

def visible(s):
    s = re.sub(r'<script.*?</script>|<style.*?</style>', '', s, flags=re.S)
    return re.sub(r'<[^>]+>', ' ', s)

titles, descs = Counter(), Counter()
for url, s in public.items():
    own = url in ('/', '/linktree/')          # páginas com layout próprio
    kb = len(s.encode()) / 1024
    if kb > MAX_HTML_KB: err(f'{url}: HTML com {kb:.0f} KB (máx {MAX_HTML_KB})')
    for bad in ('—', '→'):
        if bad in visible(s): err(f'{url}: texto com "{bad}" (a seta dos botões é CSS)')
    t = re.search(r'<title>(.*?)</title>', s, re.S)
    if not t: err(f'{url}: sem <title>')
    else:
        titles[t.group(1).strip()] += 1
        if len(t.group(1)) > 90: warn(f'{url}: <title> com {len(t.group(1))} caracteres')
    d = re.search(r'<meta name="description" content="([^"]*)"', s)
    if not own:
        if not d: err(f'{url}: sem meta description')
        else:
            descs[d.group(1)] += 1
            if len(d.group(1)) > 160: err(f'{url}: description com {len(d.group(1))} caracteres')
    m = re.search(r'<link rel="canonical" href="([^"]+)"', s)
    if not m or m.group(1) != SITE + url: err(f'{url}: canonical errado ({m.group(1) if m else "ausente"})')
    if not own:
        m = re.search(r'<meta property="og:url" content="([^"]+)"', s)
        if not m or m.group(1) != SITE + url: err(f'{url}: og:url errado')
        m = re.search(r'<meta property="og:image" content="([^"]+)"', s)
        if not m: err(f'{url}: sem og:image')
        else:
            f = ROOT / m.group(1).replace(SITE, '').lstrip('/')
            if not f.exists(): err(f'{url}: og:image não existe ({m.group(1)})')
            elif Image.open(f).size != (1200, 630): err(f'{url}: og:image {Image.open(f).size}, esperado 1200x630')
        if 'BreadcrumbList' not in s: err(f'{url}: sem BreadcrumbList')
    for ld in re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
        try: json.loads(ld)
        except Exception as e: err(f'{url}: JSON-LD inválido: {e}')
    if s.count('<h1') != 1: err(f'{url}: {s.count("<h1")} H1 (tem que ser 1)')
    if 'fonts.googleapis' in s: err(f'{url}: Google Fonts (a fonte é servida pelo próprio site)')
    for img in re.findall(r'<img [^>]+>', s):
        src = re.search(r'src="([^"]+)"', img)
        if src and src.group(1).startswith('/') and not (ROOT / src.group(1).lstrip('/')).exists(): err(f'{url}: imagem inexistente {src.group(1)}')
        if 'facebook.com/tr' in img: continue
        if 'width=' not in img or 'height=' not in img: err(f'{url}: <img> sem width/height: {img[:90]}')
        if 'alt=' not in img: err(f'{url}: <img> sem alt: {img[:90]}')
    ids = set(re.findall(r'id="([^"]+)"', s))
    for href in re.findall(r'href="([^"]+)"', s):
        if href == '#': err(f'{url}: link vazio (href="#")')
        elif href.startswith('#') and href[1:] not in ids: err(f'{url}: âncora sem destino {href}')
        elif href.startswith('/') and not href.startswith('//'):
            path = href.split('#')[0].split('?')[0]
            if path.startswith('/blog/altive'): err(f'{url}: aponta pra seção privada {path}')
            elif path.endswith('/'):
                if path not in public and path not in redirects: err(f'{url}: link interno quebrado {path}')
            elif not (ROOT / path.lstrip('/')).exists(): err(f'{url}: arquivo inexistente {path}')
    for a in re.findall(r'<a [^>]*href="https?://(?:www\.)?(?:meli\.la|mercadolivre|gsuplementos|ultramel|apx|padraopuro)[^"]*"[^>]*>', s):
        if 'sponsored' not in a and url != '/linktree/': err(f'{url}: link de parceiro sem rel=sponsored')
        if url.startswith('/blog/zero-noia/'): err(f'{url}: afiliado dentro do Zero Nóia')
    for f in re.findall(r'<form [^>]*>', s):
        if 'data-netlify="true"' not in f: err(f'{url}: formulário sem data-netlify')
    if 'target="_blank"' in s: warn(f'{url}: target=_blank (evitar no navegador do Instagram)')

for t, n in titles.items():
    if n > 1: err(f'título repetido em {n} páginas: {t}')
for d, n in descs.items():
    if n > 1: err(f'description repetida em {n} páginas: {d[:70]}')

# Lei da Árvore: todo texto aparece no índice do seu tema
for url, s in public.items():
    parent = url.rsplit('/', 2)[0] + '/'
    if url.count('/') >= 4 and parent in public and parent != url and '"@type": "CollectionPage"' in public[parent]:
        if f'href="{url}"' not in public[parent]: err(f'{parent}: índice não lista {url} (Lei da Árvore)')

# página órfã: toda página pública precisa de pelo menos um link vindo de outra página (exceto home e /linktree/)
linked = set()
for u, s2 in public.items():
    for href in re.findall(r'href="(/[^"#?]*)', s2):
        if href != u: linked.add(href if href.endswith('/') else href)
for u in public:
    if u not in ('/', '/linktree/') and u not in linked:
        err(f'{u}: página órfã (nenhuma outra página aponta pra ela)')

# seção privada: sem SEO nenhum e ninguém aponta pra ela
for url, s in private.items():
    if 'noindex' not in s: err(f'{url}: página privada sem noindex')
    for bad in ('rel="canonical"', 'og:', 'application/ld+json', 'googletagmanager', 'name="description"'):
        if bad in s: err(f'{url}: página privada com "{bad}"')
for f in ('sitemap.xml', 'llms.txt', 'robots.txt', 'blog/feed.xml'):
    p = ROOT / f
    if p.exists() and '/altive' in p.read_text(encoding='utf-8'): err(f'{f} menciona a seção privada')

# sitemap = todas as páginas públicas
sm = (ROOT / 'sitemap.xml').read_text(encoding='utf-8')
for u in public:
    if f'<loc>{SITE}{u}</loc>' not in sm: err(f'sitemap sem {u}')
for u in re.findall(r'<loc>' + re.escape(SITE) + r'([^<]+)</loc>', sm):
    if u not in public: err(f'sitemap com página que não existe: {u}')
if 'Sitemap:' not in (ROOT / 'robots.txt').read_text(): err('robots.txt sem Sitemap')

print(f'{len(public)} páginas públicas + {len(private)} privada(s) verificadas · {len(errors)} erros · {len(warns)} avisos')
for w in warns: print('  aviso:', w)
for e in errors: print('  ERRO:', e)
sys.exit(1 if errors else 0)
