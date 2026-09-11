#!/usr/bin/env python3
"""Portões de qualidade do blog (herdados da Selva: _portao0 + _qa). Reprova o build se algo estiver fora.
Uso: python3 check.py
"""
import re, json, sys, pathlib
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / 'blog'
SITE = 'https://joaobernardino.com.br'
MAX_HTML_KB = 60
errors, warns = [], []


def err(m): errors.append(m)
def warn(m): warns.append(m)


htmls = sorted(OUT.rglob('index.html'))
if not htmls:
    err('nenhum HTML em blog/')
def url_of(h):
    rel = str(h.parent.relative_to(OUT)).replace('\\', '/')
    return '/blog/' if rel == '.' else '/blog/' + rel + '/'
existing = {'/', '/blog/'} | {url_of(h) for h in htmls}
for h in htmls:
    url = url_of(h)
    s = h.read_text(encoding='utf-8')
    kb = len(s.encode()) / 1024
    if kb > MAX_HTML_KB: err(f'{url}: HTML com {kb:.0f} KB (máx {MAX_HTML_KB})')
    for bad in ('—', '→'):
        if bad in re.sub(r'<script type="application/ld\+json">.*?</script>', '', s, flags=re.S):
            err(f'{url}: contém "{bad}"')
    m = re.search(r'<link rel="canonical" href="([^"]+)"', s)
    if not m or m.group(1) != SITE + url: err(f'{url}: canonical errado ({m.group(1) if m else "ausente"})')
    m = re.search(r'<meta property="og:url" content="([^"]+)"', s)
    if not m or m.group(1) != SITE + url: err(f'{url}: og:url errado')
    m = re.search(r'<meta property="og:image" content="([^"]+)"', s)
    if m:
        og = m.group(1).replace(SITE, '')
        f = ROOT / og.lstrip('/')
        if not f.exists(): err(f'{url}: og:image não existe ({og})')
        else:
            try:
                w, hh = Image.open(f).size
                if (w, hh) != (1200, 630): err(f'{url}: og:image {w}x{hh}, esperado 1200x630')
            except Exception as e: err(f'{url}: og:image ilegível {e}')
    for ld in re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
        try: json.loads(ld)
        except Exception as e: err(f'{url}: JSON-LD inválido: {e}')
    if 'BreadcrumbList' not in s: err(f'{url}: sem BreadcrumbList')
    for img in re.findall(r'<img [^>]+>', s):
        src = re.search(r'src="([^"]+)"', img)
        if src and src.group(1).startswith('/') and not (ROOT / src.group(1).lstrip('/')).exists(): err(f'{url}: imagem inexistente {src.group(1)}')
        if 'width=' not in img or 'height=' not in img: err(f'{url}: <img> sem width/height: {img[:80]}')
        if 'alt=' not in img: err(f'{url}: <img> sem alt: {img[:80]}')
    for href in re.findall(r'href="([^"]+)"', s):
        if href.startswith('/') and not href.startswith('//'):
            path = href.split('#')[0].split('?')[0]
            if path.endswith('/'):
                if path not in existing: err(f'{url}: link interno quebrado {path}')
            elif not (ROOT / path.lstrip('/')).exists(): err(f'{url}: arquivo interno inexistente {path}')
        if 'kiwify' in href and '/zero-noia/' not in url and url != '/blog/neurociencia/21-leis/':
            err(f'{url}: link de checkout fora do hub do Zero Nóia / 21 Leis ({href})')
    if re.search(r'<a [^>]*href="https?://(www\.)?(mercadolivre|gsuplementos|ultramel|apx|padraopuro)', s):
        if 'rel="sponsored' not in s: err(f'{url}: link de parceiro sem rel=sponsored')
        if '/zero-noia/' in url: err(f'{url}: afiliado dentro do cluster Zero Nóia')
    if 'fonts.googleapis' in s: err(f'{url}: Google Fonts (proibido)')
    if 'target="_blank"' in s: warn(f'{url}: target=_blank (evitar no WebView do IG)')
    if '<h1' not in s: err(f'{url}: sem H1')
    if s.count('<h1') > 1: err(f'{url}: mais de um H1')
# hubs listam todos os filhos do disco
for h in htmls:
    url = url_of(h)
    if url == '/blog/': continue
    s = h.read_text(encoding='utf-8')
    if 'class="post hub"' in s:
        cluster_dir = h.parent
        kids = [url_of(k) for k in cluster_dir.rglob('index.html') if k != h]
        for k in kids:
            if f'href="{k}"' not in s: err(f'{url}: hub não lista o filho {k} (Lei da Árvore)')
# sitemap cobre tudo
sm = (ROOT / 'sitemap.xml').read_text(encoding='utf-8')
for u in existing:
    if f'<loc>{SITE}{u}</loc>' not in sm: err(f'sitemap sem {u}')
# tokens da home = tokens do blog (cores da marca)
home = (ROOT / 'index.html').read_text(encoding='utf-8')
for tok in ('#C8102E', '#111111', '#F0405C'):
    if tok not in home or tok not in (ROOT / 'css' / 'blog.css').read_text(): err(f'token {tok} divergente entre home e blog')
# home intocada? (só pode ganhar o link "Textos")
if '/blog/' not in home: warn('home ainda não linka /blog/')
print(f'{len(htmls)} páginas verificadas · {len(errors)} erros · {len(warns)} avisos')
for w in warns: print('  aviso:', w)
for e in errors: print('  ERRO:', e)
sys.exit(1 if errors else 0)
