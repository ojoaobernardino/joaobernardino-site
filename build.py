#!/usr/bin/env python3
"""Gerador do blog joaobernardino.com.br/blog/.
Lê content/**/*.md (Markdown + frontmatter YAML), escreve blog/**/index.html, blog/feed.xml, sitemap.xml
e img/og/<slug>.jpg. Sem build no Netlify: a saída é commitada.
Uso: python3 build.py            (gera tudo)
     python3 build.py --drafts   (inclui draft: true, pra preview local)
"""
import os, re, sys, json, html, datetime, pathlib, unicodedata
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown_it import MarkdownIt

ROOT = pathlib.Path(__file__).resolve().parent
CONTENT = ROOT / 'content'
OUT = ROOT / 'blog'
SITE = {
    'url': 'https://joaobernardino.com.br',
    'year': datetime.date.today().year,
    'nav': [
        {'label': 'Textos', 'url': '/blog/'},
        {'label': 'Vendas', 'url': '/blog/vendas/'},
        {'label': 'Liderança', 'url': '/blog/lideranca/'},
        {'label': 'Neurociência', 'url': '/blog/neurociencia/'},
        {'label': 'Zero Nóia', 'url': '/blog/zero-noia/'},
        {'label': 'Sobre', 'url': '/blog/sobre/'},
    ],
}
CLUSTERS = {
    'vendas': 'Vendas', 'lideranca': 'Liderança', 'neurociencia': 'Neurociência', 'treino': 'Treino',
    'zero-noia': 'Zero Nóia', 'livros': 'Livros', 'uso': 'O que eu uso', 'parceiros': 'Parceiros',
    'wjr': 'Meu contador', 'dieta': 'Dieta', 'a-obra': 'A Obra',
}
PERSON_ID = SITE['url'] + '/#pessoa'
MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
INCLUDE_DRAFTS = '--drafts' in sys.argv

env = Environment(loader=FileSystemLoader(str(ROOT / 'templates')), autoescape=select_autoescape(['html']))
CSS = (ROOT / 'css' / 'blog.css').read_text(encoding='utf-8')
CSS = re.sub(r'\s*\n\s*', '', CSS)  # minify leve
md = MarkdownIt('commonmark', {'html': True, 'typographer': False}).enable('table').enable('strikethrough')


def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = re.sub(r'[^a-zA-Z0-9]+', '-', s).strip('-').lower()
    return s


def date_br(d):
    d = datetime.date.fromisoformat(str(d))
    return f'{d.day} {MESES[d.month - 1]} {d.year}'


def parse(path):
    raw = path.read_text(encoding='utf-8')
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', raw, re.S)
    if not m:
        raise SystemExit(f'sem frontmatter: {path}')
    fm = yaml.safe_load(m.group(1)) or {}
    body = m.group(2)
    for k in ('title', 'description', 'type', 'date', 'updated', 'summary'):
        if k not in fm:
            raise SystemExit(f'{path}: falta `{k}` no frontmatter')
    if len(fm['title']) > 70:
        raise SystemExit(f'{path}: title com {len(fm["title"])} caracteres (máx 70)')
    if len(fm['description']) > 160:
        raise SystemExit(f'{path}: description com {len(fm["description"])} caracteres (máx 160)')
    for bad in ('—', '→'):
        if bad in raw:
            raise SystemExit(f'{path}: contém "{bad}" (proibido pela voz do João)')
    rel = path.relative_to(CONTENT)
    parts = list(rel.parts)
    parts[-1] = parts[-1][:-3]  # tira .md
    if parts[-1] == 'index':
        parts = parts[:-1]
    url = '/blog/' + '/'.join(parts) + ('/' if parts else '')
    slug = parts[-1] if parts else 'blog'
    cluster = fm.get('cluster') or (parts[0] if len(parts) > 1 else None)
    return {**fm, 'body': body, 'url': url, 'slug': slug, 'cluster': cluster, 'src': str(rel)}


def render_md(body, page):
    # callouts: linha começando com "!!! "
    lines = []
    for line in body.split('\n'):
        if line.startswith('!!! '):
            txt = line[4:].strip()
            label, _, rest = txt.partition(':')
            if rest:
                lines.append(f'<div class="callout"><span class="callout-label">{html.escape(label.strip())}</span>{md.renderInline(rest.strip())}</div>')
            else:
                lines.append(f'<div class="callout">{md.renderInline(txt)}</div>')
        else:
            lines.append(line)
    body = '\n'.join(lines)
    # {sponsored} depois do link
    body = re.sub(r'\]\(([^)]+)\)\{sponsored\}', r'](\1){{SPONSORED}}', body)
    out = md.render(body)
    out = re.sub(r'<a href="([^"]+)">([^<]*)</a>\{\{SPONSORED\}\}', r'<a href="\1" rel="sponsored noopener">\2</a>', out)
    out = out.replace('{{SPONSORED}}', '')
    # ids nos H2/H3 + toc
    toc = []
    def add_id(m):
        level, text = m.group(1), m.group(2)
        plain = re.sub(r'<[^>]+>', '', text)
        i = slugify(plain)
        if level == '2':
            toc.append({'id': i, 'text': plain})
        return f'<h{level} id="{i}">{text}</h{level}>'
    out = re.sub(r'<h([23])>(.*?)</h\1>', add_id, out)
    # imagens relativas -> /img/blog/
    out = out.replace('src="img/', 'src="/img/blog/')
    # links externos ganham rel=noopener (sem target)
    out = re.sub(r'<a href="(https?://[^"]+)">', r'<a href="\1" rel="noopener">', out)
    out = out.replace('rel="noopener" rel="sponsored noopener"', 'rel="sponsored noopener"')
    return out, toc


def jsonld(page, pages):
    crumbs = [{'@type': 'ListItem', 'position': i + 1, 'name': c['name'], 'item': SITE['url'] + c['url']} for i, c in enumerate(page['crumbs'])]
    graph = [{'@type': 'BreadcrumbList', 'itemListElement': crumbs}]
    if page['type'] == 'post':
        graph.append({
            '@type': 'BlogPosting', '@id': SITE['url'] + page['url'] + '#artigo',
            'headline': page['title'], 'description': page['description'],
            'datePublished': str(page['date']), 'dateModified': str(page['updated']),
            'inLanguage': 'pt-BR', 'mainEntityOfPage': SITE['url'] + page['url'],
            'image': SITE['url'] + page['og_image'],
            'author': {'@id': PERSON_ID}, 'publisher': {'@id': PERSON_ID},
            'articleSection': page.get('cluster_name'), 'keywords': ', '.join(page.get('tags') or []),
            'wordCount': page['words'],
        })
    elif page['type'] == 'hub':
        graph.append({
            '@type': 'CollectionPage', '@id': SITE['url'] + page['url'] + '#secao',
            'name': page['title'], 'description': page['description'], 'inLanguage': 'pt-BR',
            'url': SITE['url'] + page['url'], 'author': {'@id': PERSON_ID},
            'hasPart': [{'@type': 'BlogPosting', 'headline': c['title'], 'url': SITE['url'] + c['url']} for c in page.get('children', [])],
        })
    elif page['slug'] == 'sobre':
        graph.append({
            '@type': 'ProfilePage', '@id': SITE['url'] + page['url'] + '#perfil',
            'name': page['title'], 'description': page['description'], 'inLanguage': 'pt-BR',
            'dateModified': str(page['updated']), 'mainEntity': {'@id': PERSON_ID},
        })
        graph.append({
            '@type': 'Person', '@id': PERSON_ID, 'name': 'João Bernardino',
            'alternateName': ['João Bêrnardino', 'João Pedro Vendramini Bernardino de Souza', 'ojoaobernardino', 'JB'],
            'url': SITE['url'] + '/', 'image': SITE['url'] + '/apple-touch-icon.png',
            'jobTitle': 'Vendedor & Neurotreinador',
            'description': 'Vendedor enterprise (Heineken, Stone/Pagar.me, Closecare, Pessoalize, Koin), Engenheiro de Produção (Mackenzie), pós em Neurociências e Comportamento (PUCRS), Master em PNL (SBPNL). Criador do Zero Nóia e da Comunidade A Obra.',
            'alumniOf': [{'@type': 'CollegeOrUniversity', 'name': 'Universidade Presbiteriana Mackenzie'}, {'@type': 'CollegeOrUniversity', 'name': 'PUCRS'}],
            'knowsAbout': ['Vendas B2B', 'Inside sales', 'Liderança comercial', 'PNL', 'Neurociência do hábito', 'Treinamento híbrido'],
            'worksFor': {'@type': 'Organization', 'name': 'JB Treinamento e Desenvolvimento'},
            'sameAs': ['https://www.instagram.com/ojoaobernardino', 'https://www.youtube.com/@ojoaobernardino', 'https://www.tiktok.com/@ojoaobernardino',
                       'https://www.linkedin.com/in/ojoaobernardino', 'https://strava.app.link/dRHfi2AGt1b', 'https://www.threads.com/@ojoaobernardino'],
        })
    else:
        graph.append({'@type': 'WebPage', '@id': SITE['url'] + page['url'], 'name': page['title'], 'description': page['description'], 'inLanguage': 'pt-BR', 'author': {'@id': PERSON_ID}})
    if page['slug'] != 'sobre':
        graph.append({'@type': 'Person', '@id': PERSON_ID, 'name': 'João Bernardino', 'alternateName': ['João Bêrnardino'], 'url': SITE['url'] + '/blog/sobre/'})
    return json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False)


def og_image(page):
    """Gera img/og/<slug>.jpg 1200x630, preto, título em Barlow Condensed (via fontTools woff2->ttf em cache)."""
    from PIL import Image, ImageDraw, ImageFont
    ogdir = ROOT / 'img' / 'og'; ogdir.mkdir(parents=True, exist_ok=True)
    out = ogdir / f"{page['slug']}.jpg"
    ttf = ROOT / '.cache' / 'barlow-condensed-900.ttf'
    if not ttf.exists():
        ttf.parent.mkdir(exist_ok=True)
        from fontTools.ttLib import TTFont
        f = TTFont(str(ROOT / 'fonts' / 'barlow-condensed-900.woff2')); f.flavor = None; f.save(str(ttf))
    ttf2 = ROOT / '.cache' / 'barlow-600.ttf'
    if not ttf2.exists():
        from fontTools.ttLib import TTFont
        f = TTFont(str(ROOT / 'fonts' / 'barlow-600.woff2')); f.flavor = None; f.save(str(ttf2))
    im = Image.new('RGB', (1200, 630), '#111111'); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 14, 630], fill='#C8102E')
    kicker = (page.get('cluster_name') or 'João Bêrnardino').upper()
    d.text((80, 80), kicker, font=ImageFont.truetype(str(ttf2), 26), fill='#F0405C')
    font = ImageFont.truetype(str(ttf), 78)
    words = page['title'].split(); lines = []; cur = ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=font) > 1040: lines.append(cur); cur = w
        else: cur = t
    lines.append(cur)
    lines = lines[:4]
    y = 140
    for i, line in enumerate(lines):
        d.text((80, y), line, font=font, fill='#ffffff'); y += 88
    try:
        av = Image.open(ROOT / 'img' / 'avatar-216.webp').convert('RGB').resize((96, 96))
        mask = Image.new('L', (96, 96), 0); ImageDraw.Draw(mask).ellipse([0, 0, 95, 95], fill=255)
        im.paste(av, (80, 500), mask)
        d.text((196, 512), 'João Bêrnardino', font=ImageFont.truetype(str(ttf), 40), fill='#ffffff')
        d.text((196, 556), 'joaobernardino.com.br', font=ImageFont.truetype(str(ttf2), 24), fill='#9a9a9a')
    except Exception:
        pass
    im.save(out, quality=82, optimize=True, progressive=True)
    return '/img/og/' + page['slug'] + '.jpg'


def main():
    pages = []
    for path in sorted(CONTENT.rglob('*.md')):
        p = parse(path)
        if p.get('draft') and not INCLUDE_DRAFTS:
            continue
        p['cluster_name'] = CLUSTERS.get(p['cluster'], p['cluster'].title() if p['cluster'] else None)
        p['cluster_url'] = f"/blog/{p['cluster']}/" if p['cluster'] else None
        p['words'] = len(re.findall(r'\w+', p['body']))
        p['reading'] = max(1, round(p['words'] / 200))
        p['date_br'] = date_br(p['date']); p['updated_br'] = date_br(p['updated'])
        p['title_tag'] = p['title'] if 'Bêrnardino' in p['title'] else f"{p['title']} · João Bêrnardino"
        pages.append(p)
    by_url = {p['url']: p for p in pages}
    # crumbs
    for p in pages:
        crumbs = [{'name': 'Início', 'url': '/'}, {'name': 'Textos', 'url': '/blog/'}]
        if p['cluster'] and p['type'] == 'post' and p['cluster_url'] in by_url:
            crumbs.append({'name': p['cluster_name'], 'url': p['cluster_url']})
        crumbs.append({'name': p['title'], 'url': p['url']})
        p['crumbs'] = crumbs
    # children / related
    posts = [p for p in pages if p['type'] == 'post']
    for p in pages:
        if p['type'] == 'hub':
            p['children'] = sorted([c for c in posts if c['cluster'] == p['cluster']], key=lambda c: str(c['date']), reverse=True)
        if p['type'] == 'post':
            same = [c for c in posts if c['cluster'] == p['cluster'] and c['url'] != p['url']]
            same.sort(key=lambda c: len(set(c.get('tags') or []) & set(p.get('tags') or [])), reverse=True)
            other = [c for c in posts if c['cluster'] != p['cluster']]
            p['related'] = (same[:2] + other[:1])[:3]
    # render
    for p in pages:
        p['html'], p['toc'] = render_md(p['body'], p)
        cover = p.get('cover') or ''
        if cover:
            from PIL import Image
            im = Image.open(ROOT / 'img' / 'blog' / pathlib.Path(cover).name)
            p['cover'] = '/img/blog/' + pathlib.Path(cover).name; p['cover_w'], p['cover_h'] = im.size
        else:
            p['cover'] = ''
        p['og_image'] = og_image(p)
        p['jsonld'] = jsonld(p, pages)
        tpl = {'post': 'post.html', 'hub': 'hub.html', 'page': 'page.html'}[p['type']]
        out = OUT / p['url'][len('/blog/'):] / 'index.html'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(env.get_template(tpl).render(page=p, site=SITE, css=CSS), encoding='utf-8')
    # índice /blog/
    hubs = sorted([p for p in pages if p['type'] == 'hub'], key=lambda h: h['title'])
    for h in hubs:
        h['count'] = len(h.get('children', []))
    latest = sorted(posts, key=lambda c: str(c['date']), reverse=True)[:20]
    idx = {'title': 'Textos de João Bêrnardino', 'title_tag': 'Textos · João Bêrnardino', 'description': 'Vendas, neurociência, liderança, treino e o Zero Nóia. Os textos de João Bernardino, com número e em primeira pessoa.',
           'url': '/blog/', 'type': 'page', 'slug': 'blog', 'draft': False, 'og_image': '/og-image.jpg', 'hubs': hubs, 'posts': latest,
           'crumbs': [{'name': 'Início', 'url': '/'}, {'name': 'Textos', 'url': '/blog/'}], 'date': datetime.date.today(), 'updated': datetime.date.today()}
    idx['jsonld'] = json.dumps({'@context': 'https://schema.org', '@type': 'Blog', '@id': SITE['url'] + '/blog/#blog', 'name': 'Textos de João Bêrnardino',
                                'url': SITE['url'] + '/blog/', 'inLanguage': 'pt-BR', 'author': {'@id': PERSON_ID},
                                'blogPost': [{'@type': 'BlogPosting', 'headline': c['title'], 'url': SITE['url'] + c['url'], 'datePublished': str(c['date'])} for c in latest]}, ensure_ascii=False)
    (OUT / 'index.html').write_text(env.get_template('index.html').render(page=idx, site=SITE, css=CSS), encoding='utf-8')
    # feed
    items = ''.join(f"<item><title>{html.escape(c['title'])}</title><link>{SITE['url']}{c['url']}</link><guid>{SITE['url']}{c['url']}</guid><pubDate>{datetime.datetime.fromisoformat(str(c['date'])).strftime('%a, %d %b %Y 08:00:00 -0300')}</pubDate><description>{html.escape(c['description'])}</description></item>" for c in latest)
    (OUT / 'feed.xml').write_text(f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>João Bêrnardino</title><link>{SITE["url"]}/blog/</link><description>Vendas, cérebro e hábito, em primeira pessoa.</description><language>pt-BR</language>{items}</channel></rss>', encoding='utf-8')
    # sitemap (home + blog)
    urls = [('/', datetime.date(2026, 9, 10), '1.0'), ('/blog/', max(str(p['updated']) for p in pages) if pages else '2026-09-11', '0.9')]
    urls += [(p['url'], str(p['updated']), '0.8' if p['type'] == 'post' else '0.9') for p in pages]
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(
        f'  <url><loc>{SITE["url"]}{u}</loc><lastmod>{d}</lastmod><priority>{pr}</priority></url>\n' for u, d, pr in urls) + '</urlset>\n'
    (ROOT / 'sitemap.xml').write_text(sm, encoding='utf-8')
    print(f'ok: {len(pages)} páginas + índice + feed + sitemap ({len(urls)} URLs)')
    for p in pages:
        print(f"  {p['type']:4s} {p['url']:55s} {p['words']:5d} palavras  {len((OUT / p['url'][6:] / 'index.html').read_bytes())//1024} KB")


if __name__ == '__main__':
    main()
