#!/usr/bin/env python3
"""Gerador do joaobernardino.com.br (v2, 29/09/2026).

Lê content/**/*.md (Markdown + frontmatter YAML) e escreve o HTML de cada página na pasta de mesmo caminho.
O caminho do arquivo é a URL:  content/blog/zero-noia/como-parar-de-fumar.md  ->  /blog/zero-noia/como-parar-de-fumar/
                              content/blog/zero-noia/index.md               ->  /blog/zero-noia/   (índice do tema)

Tipos (campo `type`):
  post  texto do blog (fundo off-white)            page  texto fora do blog (off-white)
  hub   índice de um tema; lista sozinho as filhas  blog  o índice geral /blog/
  lp    página de apresentação/venda (fundo preto), molde em templates/lp_<template>.html

Os índices se adaptam ao tamanho: até CARDS_MAX textos diretos, cards; acima disso, 3 destaques em card
e o resto em lista compacta, agrupada por `subtopic` (ou por ano). Passou de SPLIT_WARN, o check.py avisa
pra dividir o tema em subtemas (uma pasta dentro da pasta, com o próprio index.md).

Home (/index.html) e /linktree/ são arquivos próprios, fora do gerador.
Uso: python3 build.py            (gera tudo)
     python3 build.py --drafts   (inclui draft: true, pra prévia local)
"""
import re, sys, json, html, datetime, pathlib, unicodedata
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown_it import MarkdownIt

ROOT = pathlib.Path(__file__).resolve().parent
CONTENT = ROOT / 'content'
CARDS_MAX = 12      # até aqui o índice mostra cards
SPLIT_WARN = 30     # acima disso o check.py pede subtemas
SITE = {
    'url': 'https://joaobernardino.com.br',
    'year': datetime.date.today().year,
    # cabeçalho e rodapé de todas as páginas geradas (home e linktree ficam de fora)
    'nav': [
        {'label': 'Cupons', 'url': '/linktree/', 'section': 'linktree'},
        {'label': 'Produtos', 'url': '/sobre/#produtos', 'section': 'produtos'},
        {'label': 'Serviços', 'url': '/sobre/#servicos', 'section': 'servicos'},
        {'label': 'Blog', 'url': '/blog/', 'section': 'blog'},
        {'label': 'Sobre', 'url': '/sobre/', 'section': 'sobre'},
    ],
    'author_bio': 'Empreendedor, criador de conteúdo, atleta e Growth Marketing & Sales. Pós em Neurociências e Comportamento (PUCRS), Master Trainer em PNL (SBPNL), Engenheiro de Produção (Mackenzie).',  # assinatura padrão (João, 29/09)
}
# nome curto dos temas do blog (chips e breadcrumbs); o que não estiver aqui usa `name` do index.md
CLUSTERS = {
    'vendas': 'Vendas', 'lideranca': 'Liderança', 'gestao': 'Gestão', 'neurociencia': 'Neurociência', 'treino': 'Treino',
    'dieta': 'Dieta', 'zero-noia': 'Zero Nóia', 'livros': 'Livros', 'uso': 'O que eu uso', 'wjr': 'WJR',
}
MENU_ORDER = ['zero-noia', 'livros', 'indicacoes', 'vendas', 'lideranca', 'neurociencia', 'gestao', 'treino', 'dieta', 'uso']
# endereços antigos que não viraram página (os de páginas vivas ficam em `aliases:` no frontmatter)
STATIC_REDIRECTS = [('/blog/parceiros/', '/linktree/'), ('/blog/parceiros', '/linktree/'), ('/menu/', '/sobre/'), ('/menu', '/sobre/')]
SHORT_TITLES = {'Alcançando Excelência em Vendas: SPIN Selling': 'SPIN Selling', 'Legado: 15 Lições sobre Liderança': 'Legado'}
PERSON_ID = SITE['url'] + '/#pessoa'
MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
INCLUDE_DRAFTS = '--drafts' in sys.argv

env = Environment(loader=FileSystemLoader(str(ROOT / 'templates')), autoescape=select_autoescape(['html']))


def thumb(path, h=320):
    """Miniatura pra card e prateleira: mesma imagem com h px de altura (o dobro do que aparece), gerada uma vez só."""
    from PIL import Image
    src = ROOT / path.lstrip('/')
    out = ROOT / 'img' / 'thumbs' / f"{src.stem}-{h}.webp"
    if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
        out.parent.mkdir(parents=True, exist_ok=True)
        im = Image.open(src)
        if im.height > h:
            im = im.convert('RGB') if im.mode not in ('RGB', 'RGBA') else im
            im = im.resize((round(im.width * h / im.height), h), Image.LANCZOS)
        im.save(out, 'WEBP', quality=80, method=6)
    return '/img/thumbs/' + out.name


def thumb_wh(path, h=320):
    from PIL import Image
    im = Image.open(ROOT / thumb(path, h).lstrip('/'))
    return im.width, im.height


def asset_v(path):
    import hashlib
    return path + '?v=' + hashlib.md5((ROOT / path.lstrip('/')).read_bytes()).hexdigest()[:8]


env.filters['thumb'] = thumb
env.globals['thumb_wh'] = thumb_wh
env.globals['asset_v'] = asset_v
def mini(css): return re.sub(r'\s*\n\s*', '', re.sub(r'/\*.*?\*/', '', css, flags=re.S))
CSS = mini((ROOT / 'css' / 'site.css').read_text(encoding='utf-8'))
CSS_LP = mini((ROOT / 'css' / 'lp.css').read_text(encoding='utf-8'))
md = MarkdownIt('commonmark', {'html': True, 'typographer': False}).enable('table').enable('strikethrough')


def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-zA-Z0-9]+', '-', s).strip('-').lower()


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
    for k in ('title', 'description', 'type', 'date', 'updated'):
        if k not in fm:
            raise SystemExit(f'{path}: falta `{k}` no frontmatter')
    if fm['type'] in ('post', 'page') and not fm.get('summary'):
        raise SystemExit(f'{path}: falta `summary` (o "Em resumo")')
    if len(fm['title']) > 70:
        raise SystemExit(f'{path}: title com {len(fm["title"])} caracteres (máx 70)')
    if len(fm['description']) > 160:
        raise SystemExit(f'{path}: description com {len(fm["description"])} caracteres (máx 160)')
    for bad in ('—', '→'):
        if bad in raw:
            raise SystemExit(f'{path}: contém "{bad}" (proibido pela voz do João)')
    rel = path.relative_to(CONTENT)
    parts = list(rel.parts)
    parts[-1] = parts[-1][:-3]
    is_index = parts[-1] == 'index'
    if is_index:
        parts = parts[:-1]
    url = '/' + '/'.join(parts) + '/' if parts else '/'
    section = parts[0] if parts else ''
    # pasta-mãe: pra um texto é a pasta onde ele está; pra um índice é a pasta de cima
    folder = '/'.join(parts[:-1]) if not is_index else '/'.join(parts[:-1])
    own_folder = '/'.join(parts) if is_index else None
    slug = parts[-1] if parts else 'home'
    t = fm['type']
    theme = fm.get('theme') or ('paper' if (section == 'blog' or t in ('post', 'page')) else 'dark')
    return {**fm, 'body': body, 'url': url, 'slug': slug, 'section': section, 'folder': folder,
            'own_folder': own_folder, 'theme': theme, 'src': str(rel)}


PENDING = []


def extract_faq(body):
    if '## Perguntas frequentes' not in body:
        return []
    sec = body.split('## Perguntas frequentes', 1)[1].split('\n## ', 1)[0]
    sec = re.sub(r'<!--.*?-->', '', sec, flags=re.S)
    out = []
    for q, a in re.findall(r'### (.*?)\n\n(.*?)(?=\n### |\Z)', sec, re.S):
        txt = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', a)
        txt = re.sub(r'[*_`]', '', txt)
        out.append({'@type': 'Question', 'name': q.strip(), 'acceptedAnswer': {'@type': 'Answer', 'text': ' '.join(txt.split())}})
    return out


def render_md(body, page):
    for m in re.findall(r'<!--\s*CONFIRMAR:?\s*(.*?)-->', body, re.S):
        PENDING.append((page['url'], ' '.join(m.split())))
    body = re.sub(r'\s*<!--\s*CONFIRMAR.*?-->', '', body, flags=re.S)
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
    body = re.sub(r'\]\(([^)]+)\)\{sponsored\}', r'](\1){{SPONSORED}}', body)
    out = md.render(body)
    out = re.sub(r'<a href="([^"]+)">([^<]*)</a>\{\{SPONSORED\}\}', r'<a href="\1" rel="sponsored noopener">\2</a>', out)
    out = out.replace('{{SPONSORED}}', '')
    toc = []
    def add_id(m):
        level, text = m.group(1), m.group(2)
        plain = re.sub(r'<[^>]+>', '', text)
        i = slugify(plain)
        if level == '2' and i != 'fontes':
            toc.append({'id': i, 'text': plain})
        return f'<h{level} id="{i}">{text}</h{level}>'
    out = re.sub(r'<h([23])>(.*?)</h\1>', add_id, out)
    out = out.replace('<table>', '<div class="tbl"><table>').replace('</table>', '</table></div>')
    if page.get('book'):
        bk = page['book']; short = page['short_title']
        buy = (f'<div class="next" style="margin:24px 0 32px"><span class="k">Onde comprar</span><h3>{html.escape(short)}, edição {html.escape(str(bk.get("editora","")))}</h3>'
               f'<p>{html.escape(bk.get("pra_quem",""))}: este é o livro.</p><a class="btn w go" href="{bk["afiliado"]}" rel="sponsored noopener" data-track="livro-fim:{page["slug"]}">Comprar o livro</a>'
               '<small>Link de parceiro: eu ganho uma comissão e você paga o mesmo.</small></div>\n')
        out = out.replace('<h2 id="perguntas-frequentes">', buy + '<h2 id="perguntas-frequentes">', 1)
    if page.get('produto'):
        out = out.replace('<h2 id="perguntas-frequentes">', buybox(page, 'fim') + '\n<h2 id="perguntas-frequentes">', 1)
    out = out.replace('<h2 id="fontes">', '<h2 id="fontes" class="fontes-h">')
    out = collapse(out)
    out = out.replace('src="img/', 'src="/img/blog/')
    out = re.sub(r'<a href="(https?://[^"]+)">', r'<a href="\1" rel="noopener">', out)
    out = out.replace('rel="noopener" rel="sponsored noopener"', 'rel="sponsored noopener"')
    return out, toc


def collapse(out):
    """Perguntas frequentes e fontes viram botões que abrem (details/summary). O texto continua no HTML: Google e IA leem igual."""
    def faq(m):
        body = re.sub(r'<h3 id="([^"]+)">(.*?)</h3>\s*(.*?)(?=<h3 id=|\Z)',
                      lambda q: f'<details class="faq" id="{q.group(1)}"><summary>{q.group(2)}</summary><div>{q.group(3).strip()}</div></details>\n', m.group(2), flags=re.S)
        return m.group(1) + '\n' + body
    out = re.sub(r'(<h2 id="perguntas-frequentes">.*?</h2>)(.*?)(?=<h2 |\Z)', faq, out, count=1, flags=re.S)
    def fontes(m):
        n = m.group(2).count('<li>')
        return (m.group(1) + f'\n<details class="fontes"><summary>Ver {"as " + str(n) + " fontes" if n > 1 else "a fonte"}</summary>'
                + m.group(2).strip() + '</details>\n')
    return re.sub(r'(<h2 id="fontes" class="fontes-h">.*?</h2>)(.*?)(?=<h2 |\Z)', fontes, out, count=1, flags=re.S)


def brl(v):
    v = float(v); return ('R$ ' + f'{v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')).replace(',00', '')


def buybox(page, onde):
    """Onde comprar: site da marca com cupom JB e Mercado Livre, lado a lado (regra do João p/ parceiro com cupom)."""
    pr = page['produto']
    # sem preço na página: a marca muda preço e promoção toda hora; o que não muda é o cupom (João, 29/09)
    preco = f'<p class="preco"><b>{html.escape(pr["desconto"])}</b> com o cupom <b>{pr["cupom"]}</b> no site da {html.escape(pr["marca"])}</p>'
    nome = '' if onde == 'topo' else f'<h3>{html.escape(pr["nome"])}</h3>'
    return (f'<div class="buy2"><span class="k">Onde comprar</span>{nome}{preco}'
            f'<div class="bts"><a class="btn w go" href="{pr["loja_url"]}" rel="sponsored noopener" data-track="produto-{onde}:loja:{page["slug"]}">Comprar com cupom {pr["cupom"]}</a>'
            + (f'<a class="btn g go" href="{pr["ml_url"]}" rel="sponsored noopener" data-track="produto-{onde}:ml:{page["slug"]}">Ver no Mercado Livre</a>' if pr.get('ml_url') else '') + '</div>'
            f'<p class="cupom">Cupom <b>{pr["cupom"]}</b>: digite no checkout do site da {html.escape(pr["marca"])}.</p>'
            f'<small>{html.escape(pr["aviso"])}</small></div>')


def person_full():
    """A entidade Pessoa completa (vive em /sobre/jb/ e /sobre/). Nomes, formação e redes pra o Google juntar tudo."""
    return {
        '@type': 'Person', '@id': PERSON_ID, 'name': 'João Bêrnardino',
        'alternateName': ['João Bernardino', 'João Pedro Vendramini Bernardino de Souza', 'João Pedro Bernardino', 'ojoaobernardino', 'JB'],
        'givenName': 'João Pedro', 'familyName': 'Vendramini Bernardino de Souza',
        'birthDate': '1998-02-20',
        'birthPlace': {'@type': 'Place', 'name': 'São José do Rio Preto, São Paulo, Brasil'},
        'nationality': {'@type': 'Country', 'name': 'Brasil'},
        'url': SITE['url'] + '/sobre/jb/', 'image': SITE['url'] + '/img/joao.webp',
        'jobTitle': 'Growth Marketing & Sales',
        'description': 'Empreendedor, criador de conteúdo, atleta e Growth Marketing & Sales. Engenheiro de Produção pela Universidade Presbiteriana Mackenzie, pós-graduado em Neurociências e Comportamento pela PUCRS e Master Trainer em PNL pela Sociedade Brasileira de Programação Neurolinguística.',
        'alumniOf': [
            {'@type': 'CollegeOrUniversity', 'name': 'Universidade Presbiteriana Mackenzie', 'sameAs': 'https://www.mackenzie.br/', 'address': {'@type': 'PostalAddress', 'addressLocality': 'São Paulo', 'addressRegion': 'SP', 'streetAddress': 'Campus Higienópolis'}},
            {'@type': 'CollegeOrUniversity', 'name': 'Pontifícia Universidade Católica do Rio Grande do Sul (PUCRS)', 'sameAs': 'https://portal.pucrs.br/'},
            {'@type': 'EducationalOrganization', 'name': 'Sociedade Brasileira de Programação Neurolinguística (SBPNL)', 'sameAs': 'https://pnl.com.br/'},
        ],
        'hasCredential': [
            {'@type': 'EducationalOccupationalCredential', 'name': 'Bacharel em Engenharia de Produção', 'credentialCategory': 'degree', 'recognizedBy': {'@type': 'CollegeOrUniversity', 'name': 'Universidade Presbiteriana Mackenzie'}},
            {'@type': 'EducationalOccupationalCredential', 'name': 'Pós-graduação em Neurociências e Comportamento', 'credentialCategory': 'degree', 'recognizedBy': {'@type': 'CollegeOrUniversity', 'name': 'PUCRS'}},
            {'@type': 'EducationalOccupationalCredential', 'name': 'Master Trainer em Programação Neurolinguística', 'credentialCategory': 'certificate', 'recognizedBy': {'@type': 'EducationalOrganization', 'name': 'Sociedade Brasileira de Programação Neurolinguística'}},
        ],
        'knowsAbout': ['Growth marketing', 'Treinamento híbrido', 'Vendas B2B', 'Inside sales', 'Liderança comercial', 'Agentes de IA', 'Programação Neurolinguística', 'Neurociência do hábito'],
        'worksFor': {'@type': 'Organization', 'name': 'JB Treinamento e Desenvolvimento'},
        'sameAs': ['https://www.instagram.com/ojoaobernardino', 'https://www.youtube.com/@ojoaobernardino', 'https://www.tiktok.com/@ojoaobernardino',
                   'https://www.linkedin.com/in/jo%C3%A3o-b%C3%AArnardino-176a70108/', 'https://strava.app.link/dRHfi2AGt1b', 'https://www.threads.com/@ojoaobernardino',
                   'https://joaobernardino.substack.com'],
    }


def jsonld(page):
    crumbs = [{'@type': 'ListItem', 'position': i + 1, 'name': c['name'], 'item': SITE['url'] + c['url']} for i, c in enumerate(page['crumbs'])]
    graph = [{'@type': 'BreadcrumbList', 'itemListElement': crumbs}]
    t = page['type']
    if t == 'post' and page.get('book'):
        bk = page['book']
        graph.append({'@type': ['Review', 'BlogPosting'], '@id': SITE['url'] + page['url'] + '#resenha', 'headline': page['title'], 'name': page['title'],
                      'description': page['description'], 'url': SITE['url'] + page['url'], 'mainEntityOfPage': SITE['url'] + page['url'],
                      'datePublished': str(page['date']), 'dateModified': str(page['updated']), 'inLanguage': 'pt-BR', 'wordCount': page['words'],
                      'image': SITE['url'] + page['og_image'], 'author': {'@id': PERSON_ID}, 'publisher': {'@id': PERSON_ID},
                      'reviewRating': {'@type': 'Rating', 'ratingValue': bk['nota'], 'bestRating': 5, 'worstRating': 0}, 'reviewBody': page['summary'],
                      'itemReviewed': {'@type': 'Book', 'name': bk['titulo'], 'author': {'@type': 'Person', 'name': bk['autor']},
                                       'publisher': {'@type': 'Organization', 'name': str(bk.get('editora', ''))}, 'inLanguage': 'pt-BR',
                                       'image': SITE['url'] + bk['capa']}})
    if page.get('produto'):
        pr = page['produto']
        graph.append({'@type': 'Product', '@id': SITE['url'] + page['url'] + '#produto', 'name': pr['nome'], 'brand': {'@type': 'Brand', 'name': pr['marca']},
                      'image': [SITE['url'] + pr['imagem']] + [SITE['url'] + i for i in pr.get('imagens', [])], 'description': page['description'],
                      'category': pr.get('categoria'), 'sku': pr.get('sku'),
                      'additionalProperty': [{'@type': 'PropertyValue', 'name': k, 'value': str(v)} for k, v in (pr.get('ficha') or {}).items()],
                      'url': pr['loja_url'].split('?')[0],
                      **({'review': {'@type': 'Review', 'author': {'@id': PERSON_ID}, 'datePublished': str(page['date']),
                                     'reviewRating': {'@type': 'Rating', 'ratingValue': pr['nota'], 'bestRating': 10, 'worstRating': 0},
                                     'reviewBody': page['summary']}} if pr.get('nota') else {})})
    if t == 'post' and page.get('produto'):
        graph.append({'@type': 'BlogPosting', '@id': SITE['url'] + page['url'] + '#artigo', 'headline': page['title'], 'description': page['description'],
                      'datePublished': str(page['date']), 'dateModified': str(page['updated']), 'inLanguage': 'pt-BR',
                      'mainEntityOfPage': SITE['url'] + page['url'], 'image': SITE['url'] + page['og_image'], 'about': {'@id': SITE['url'] + page['url'] + '#produto'},
                      'author': {'@id': PERSON_ID}, 'publisher': {'@id': PERSON_ID}, 'keywords': ', '.join(page.get('tags') or []), 'wordCount': page['words']})
    elif t == 'post':
        graph.append({'@type': 'BlogPosting', '@id': SITE['url'] + page['url'] + '#artigo', 'headline': page['title'], 'description': page['description'],
                      'datePublished': str(page['date']), 'dateModified': str(page['updated']), 'inLanguage': 'pt-BR',
                      'mainEntityOfPage': SITE['url'] + page['url'], 'image': SITE['url'] + page['og_image'],
                      'author': {'@id': PERSON_ID}, 'publisher': {'@id': PERSON_ID},
                      'articleSection': page.get('cluster_name'), 'keywords': ', '.join(page.get('tags') or []), 'wordCount': page['words']})
    elif t in ('hub', 'blog'):
        graph.append({'@type': 'CollectionPage', '@id': SITE['url'] + page['url'] + '#secao', 'name': page['title'], 'description': page['description'],
                      'inLanguage': 'pt-BR', 'url': SITE['url'] + page['url'], 'author': {'@id': PERSON_ID},
                      'hasPart': [{'@type': 'BlogPosting', 'headline': c['title'], 'url': SITE['url'] + c['url']} for c in page.get('all_posts', [])[:100]]})
    elif page['url'] in ('/sobre/', '/sobre/jb/'):
        graph.append({'@type': 'ProfilePage', '@id': SITE['url'] + '/sobre/#perfil', 'name': page['title'], 'description': page['description'],
                      'inLanguage': 'pt-BR', 'dateModified': str(page['updated']), 'mainEntity': {'@id': PERSON_ID}})
    else:
        graph.append({'@type': 'WebPage', '@id': SITE['url'] + page['url'], 'name': page['title'], 'description': page['description'],
                      'inLanguage': 'pt-BR', 'author': {'@id': PERSON_ID}})
    if page.get('faq'):
        graph.append({'@type': 'FAQPage', '@id': SITE['url'] + page['url'] + '#perguntas', 'mainEntity': page['faq']})
    graph.append(person_full() if page['url'] in ('/sobre/', '/sobre/jb/') else
                 {'@type': 'Person', '@id': PERSON_ID, 'name': 'João Bêrnardino', 'alternateName': ['João Bernardino'], 'url': SITE['url'] + '/sobre/jb/'})
    return json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False)


def _inter(weight):
    """Inter (variável) em TTF no peso pedido, pro Pillow desenhar a imagem de compartilhamento."""
    from PIL import ImageFont
    ttf = ROOT / '.cache' / 'inter-var.ttf'
    if not ttf.exists():
        ttf.parent.mkdir(exist_ok=True)
        from fontTools.ttLib import TTFont
        f = TTFont(str(ROOT / 'fonts' / 'inter-var-latin.woff2')); f.flavor = None; f.save(str(ttf))
    def make(size):
        font = ImageFont.truetype(str(ttf), size)
        try: font.set_variation_by_axes([32, weight])
        except Exception: pass
        return font
    return make


def og_image(page):
    """img/og/<caminho>.jpg 1200x630 no padrão novo: preto, Inter, ponto vermelho."""
    from PIL import Image, ImageDraw
    name = page['url'].strip('/').replace('/', '--') or 'home'
    ogdir = ROOT / 'img' / 'og'; ogdir.mkdir(parents=True, exist_ok=True)
    out = ogdir / f'{name}.jpg'
    bold, reg = _inter(700), _inter(500)
    if page.get('book') or page.get('produto'):
        return og_book(page, out, name, bold, reg)
    im = Image.new('RGB', (1200, 630), '#000000'); d = ImageDraw.Draw(im)
    kicker = (page.get('cluster_name') or page.get('kicker') or 'João Bêrnardino').upper()
    d.text((80, 84), kicker, font=reg(26), fill='#BF1E2D')
    font = bold(72)
    words = page['title'].split(); lines = []; cur = ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=font) > 1040: lines.append(cur); cur = w
        else: cur = t
    lines.append(cur)
    y = 140
    for line in lines[:4]:
        d.text((80, y), line, font=font, fill='#ffffff'); y += 84
    try:
        av = Image.open(ROOT / 'img' / 'avatar-216.webp').convert('RGB').resize((88, 88))
        mask = Image.new('L', (88, 88), 0); ImageDraw.Draw(mask).ellipse([0, 0, 87, 87], fill=255)
        im.paste(av, (80, 494), mask)
        d.text((188, 504), 'João Bêrnardino', font=bold(34), fill='#ffffff')
        d.text((188, 546), 'joaobernardino.com.br', font=reg(22), fill='#8a8a8a')
    except Exception:
        pass
    im.save(out, quality=82, optimize=True, progressive=True)
    return '/img/og/' + name + '.jpg'


def og_book(page, out, name, bold, reg):
    """Imagem de compartilhamento da resenha: título à esquerda, capa do livro à direita."""
    from PIL import Image, ImageDraw
    pr = page.get('produto')
    bk = page.get('book') or {'capa': pr['imagem'], 'autor': pr['marca']}
    im = Image.new('RGB', (1200, 630), '#000000'); d = ImageDraw.Draw(im)
    d.rounded_rectangle([760, 60, 1140, 570], radius=24, fill='#FFFFFF' if pr else '#F1EEE8')
    cv = Image.open(ROOT / bk['capa'].lstrip('/')).convert('RGBA'); cv.thumbnail((340, 440) if pr else (260, 440))
    im.paste(cv, (950 - cv.width // 2, 315 - cv.height // 2), cv)
    d.text((80, 90), 'INDICAÇÃO · CUPOM ' + pr['cupom'] if pr else 'LIVROS · RESENHA', font=reg(24), fill='#BF1E2D')
    font = bold(58); lines = []; cur = ''
    for w in page['title'].split():
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=font) > 620: lines.append(cur); cur = w
        else: cur = t
    lines.append(cur)
    y = 140
    for l in lines[:5]:
        d.text((80, y), l, font=font, fill='#ffffff'); y += 68
    d.text((80, y + 10), f"Cupom {pr['cupom']}: {pr['desconto']} na {pr['marca']}" if pr else f"{bk['autor']} · nota {bk['nota']} de 5".replace('.5 de', ',5 de'), font=reg(24), fill='#a3a3a3')
    try:
        av = Image.open(ROOT / 'img' / 'avatar-216.webp').convert('RGB').resize((72, 72))
        m = Image.new('L', (72, 72), 0); ImageDraw.Draw(m).ellipse([0, 0, 71, 71], fill=255); im.paste(av, (80, 510), m)
        d.text((168, 516), 'João Bêrnardino', font=bold(28), fill='#ffffff'); d.text((168, 552), 'joaobernardino.com.br', font=reg(20), fill='#8a8a8a')
    except Exception:
        pass
    im.save(out, quality=84, optimize=True, progressive=True)
    return '/img/og/' + name + '.jpg'


def versiona_estaticos():
    """Home e /linktree/ ficam fora do gerador: atualiza neles a versão do validador de e-mail (cache longo sem arquivo velho)."""
    for f in (ROOT / 'index.html', ROOT / 'linktree' / 'index.html'):
        s = f.read_text(encoding='utf-8')
        s2 = re.sub(r'<script src="/js/valida-email\.js(\?v=\w+)?"( defer)?></script>', f'<script src="{asset_v("/js/valida-email.js")}" defer></script>', s)
        if s2 != s:
            f.write_text(s2, encoding='utf-8')


def main():
    pages = []
    for path in sorted(CONTENT.rglob('*.md')):
        p = parse(path)
        if p.get('draft') and not INCLUDE_DRAFTS:
            continue
        pages.append(p)
    by_url = {p['url']: p for p in pages}
    hubs_by_folder = {p['own_folder']: p for p in pages if p['type'] == 'hub'}

    def hub_name(h):
        return h.get('name') or CLUSTERS.get(h['slug']) or h['title']

    for p in pages:
        p['words'] = len(re.findall(r'\w+', p['body']))
        p['reading'] = max(1, round(p['words'] / 200))
        p['date_br'] = date_br(p['date']); p['updated_br'] = date_br(p['updated'])
        p['title_tag'] = p['title'] if 'Bêrnardino' in p['title'] else f"{p['title']} · João Bêrnardino"
        p['faq'] = extract_faq(p['body'])
        if p.get('book'):
            from PIL import Image
            bk = p['book']
            p['cover_w'], p['cover_h'] = Image.open(ROOT / bk['capa'].lstrip('/')).size
            p['short_title'] = bk.get('curto') or SHORT_TITLES.get(bk['titulo']) or bk['titulo'].split(':')[0].strip()
        if p.get('produto'):
            from PIL import Image
            p['prod_w'], p['prod_h'] = Image.open(ROOT / p['produto']['imagem'].lstrip('/')).size
            p['buybox_top'] = buybox(p, 'topo')
        parent = hubs_by_folder.get(p['folder']) if p['type'] != 'hub' else hubs_by_folder.get(p['folder'])
        p['parent'] = parent
        if p['type'] == 'post' and parent:
            p['cluster_name'], p['cluster_url'] = hub_name(parent), parent['url']
        else:
            p['cluster_name'], p['cluster_url'] = None, None
    for h in hubs_by_folder.values():
        h['name'] = hub_name(h)

    # breadcrumbs: Início > Seção > (temas...) > página
    section_root = {'blog': ('Blog', '/blog/'), 'produtos': ('Produtos', '/produtos/'), 'sobre': ('Sobre', '/sobre/')}
    for p in pages:
        chain = []
        cur = p['parent']
        while cur is not None:
            chain.insert(0, {'name': cur['name'], 'url': cur['url']})
            cur = cur['parent']
        crumbs = [{'name': 'Início', 'url': '/'}]
        sec = section_root.get(p['section'])
        if sec and p['url'] != sec[1] and not (chain and chain[0]['url'] == sec[1]):
            crumbs.append({'name': sec[0], 'url': sec[1]})
        crumbs += chain
        crumbs.append({'name': p['title'], 'url': p['url'], 'short': p.get('name') if p['type'] == 'hub' else ('Blog' if p['type'] == 'blog' else p.get('short_title'))})
        p['crumbs'] = crumbs

    posts = [p for p in pages if p['type'] == 'post']
    items = [p for p in pages if p['type'] in ('post', 'page', 'lp')]  # o que um índice pode listar
    newest = lambda lst: sorted(lst, key=lambda c: (str(c['date']), c['title']), reverse=True)

    # índices: filhas diretas + subtemas + modo (cards ou lista)
    def under(h):
        return [c for c in items if c['url'].startswith(h['url']) and c['url'] != h['url']]
    for h in hubs_by_folder.values():
        direct = newest([c for c in items if c['parent'] is h])
        start = by_url.get(h['start']) if h.get('start') else None
        if start in direct:
            direct.remove(start)
        h['start'] = start
        h['subhubs'] = [s for s in hubs_by_folder.values() if s['parent'] is h]
        h['all_posts'] = newest(under(h))
        h['total'] = len(h['all_posts'])
        h['direct_count'] = len(direct) + (1 if start else 0)
        if h.get('secoes'):
            h['mode'], h['posts'] = 'secoes', direct
            h['secoes'] = [dict(s, posts=[c for c in direct if s.get('tipo') and c.get('indicacao') == s['tipo']]) for s in h['secoes']]
        elif len(direct) <= CARDS_MAX:
            h['mode'], h['posts'] = 'cards', direct
        else:
            feat_urls = [f if f.startswith('/') else h['url'] + f + '/' for f in (h.get('featured') or [])]
            featured = [by_url[u] for u in feat_urls if u in by_url][:4] or direct[:4]
            rest = [c for c in direct if c not in featured]
            groups = {}
            for c in rest:
                key = c.get('subtopic') or str(datetime.date.fromisoformat(str(c['date'])).year)
                groups.setdefault(key, []).append(c)
            order = h.get('subtopics') or sorted(groups, reverse=True)
            h['mode'], h['featured'] = 'list', featured
            h['groups'] = [{'name': k, 'posts': groups[k]} for k in order if k in groups]
    # livros: prateleiras do índice (ordem do frontmatter `estantes`) e prateleira do fim de cada resenha
    for h in hubs_by_folder.values():
        if h.get('template') == 'livros' and isinstance(h.get('estantes'), dict):
            kids = {c['slug']: c for c in h['all_posts'] if c.get('book')}
            listed = set()
            h['shelves'] = []
            for name, slugs in h['estantes'].items():
                books = [kids[x] for x in slugs if x in kids]
                listed.update(slugs)
                for b in books: b['group'] = name
                h['shelves'].append({'name': name, 'books': books})
            loose = [c for c in kids.values() if c['slug'] not in listed]
            if loose:
                h['shelves'].append({'name': 'Outros', 'books': loose})
                for b in loose: b['group'] = 'Outros'
            for g in h['shelves']:
                for b in g['books']:
                    b['shelf'] = [x for x in g['books'] if x is not b][:3]
            h['art_covers'] = [dict(zip(('w', 'h'), thumb_wh(kids[x]['book']['capa'])), src=thumb(kids[x]['book']['capa'])) for x in (h.get('art_books') or []) if x in kids]
    # seções que puxam de outro índice (ex.: Indicações > Livros vem da estante de /blog/livros/, na ordem das prateleiras)
    for h in hubs_by_folder.values():
        for sc in h.get('secoes') or []:
            if isinstance(sc, dict) and sc.get('fonte') in by_url:
                src = by_url[sc['fonte']]
                sc['posts'] = [b for g in src.get('shelves', []) for b in g['books']] or src.get('all_posts', [])
    # relacionados: mesmo tema primeiro (por tags em comum), depois 1 de outro tema
    for p in posts:
        same = [c for c in posts if c['parent'] is p['parent'] and c is not p]
        same.sort(key=lambda c: len(set(c.get('tags') or []) & set(p.get('tags') or [])), reverse=True)
        other = newest([c for c in posts if c['parent'] is not p['parent']])
        p['related'] = (same[:2] + other[:1])[:3]

    blog_hubs = [h for h in hubs_by_folder.values() if h['section'] == 'blog' and h['folder'] == 'blog']
    blog_hubs.sort(key=lambda h: MENU_ORDER.index(h['slug']) if h['slug'] in MENU_ORDER else 99)
    SITE['blog_hubs'] = [h for h in blog_hubs if h['total'] > 0] + [h for h in blog_hubs if h['total'] == 0]
    for p in pages:
        if p['type'] == 'blog':
            p['latest'] = newest(posts)[:7]
            p['all_posts'] = newest(posts)

    written = []
    for p in pages:
        p['html'], p['toc'] = render_md(p['body'], p)
        if p['type'] == 'hub':
            p['html_body'] = p['html']
        cover = p.get('cover') or ''
        if cover:
            from PIL import Image
            im = Image.open(ROOT / 'img' / 'blog' / pathlib.Path(cover).name)
            p['cover'] = '/img/blog/' + pathlib.Path(cover).name; p['cover_w'], p['cover_h'] = im.size
        else:
            p['cover'] = ''
        p['og_image'] = og_image(p)
        p['jsonld'] = jsonld(p)
        if p['type'] == 'hub' and p.get('template'):
            tpl = f"hub_{p['template']}.html"
        else:
            tpl = {'post': 'post.html', 'hub': 'hub.html', 'page': 'page.html', 'blog': 'blog.html'}.get(p['type']) or f"lp_{p['template']}.html"
        css = CSS + (CSS_LP if p['type'] == 'lp' else '')
        out = ROOT / p['url'].strip('/') / 'index.html'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(env.get_template(tpl).render(page=p, site=SITE, css=css), encoding='utf-8')
        written.append(p['url'])

    # limpeza: página gerada antes e que não existe mais (rascunho, tema vazio, mudou de lugar) sai do disco.
    # Nunca mexe em /blog/altive/ (seção privada feita à mão), na home nem no /linktree/.
    import shutil
    keep = set(written)
    for sec in ('blog', 'sobre', 'produtos', 'indicacoes'):
        for idx in sorted((ROOT / sec).rglob('index.html'), reverse=True):
            url = '/' + str(idx.parent.relative_to(ROOT)).replace('\\', '/') + '/'
            if url.startswith('/blog/altive/') or url in keep:
                continue
            idx.unlink()
            print(f'  removido (não existe mais): {url}')
            try: idx.parent.rmdir()
            except OSError: pass
    # feed do blog
    latest = newest(posts)
    items = ''.join(f"<item><title>{html.escape(c['title'])}</title><link>{SITE['url']}{c['url']}</link><guid>{SITE['url']}{c['url']}</guid><pubDate>{datetime.datetime.fromisoformat(str(c['date'])).strftime('%a, %d %b %Y 08:00:00 -0300')}</pubDate><description>{html.escape(c['description'])}</description></item>" for c in latest[:30])
    (ROOT / 'blog' / 'feed.xml').write_text(f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>João Bêrnardino</title><link>{SITE["url"]}/blog/</link><description>O que eu aprendo, em texto.</description><language>pt-BR</language>{items}</channel></rss>', encoding='utf-8')

    # sitemap: home + linktree + tudo que o gerador escreveu (a seção privada /blog/altive/ nunca entra)
    today = str(datetime.date.today())
    urls = [('/', today), ('/linktree/', today)] + [(p['url'], str(p['updated'])) for p in pages if not p.get('noindex')]
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(
        f'  <url><loc>{SITE["url"]}{u}</loc><lastmod>{d}</lastmod></url>\n' for u, d in urls if '/altive/' not in u) + '</urlset>\n'
    (ROOT / 'sitemap.xml').write_text(sm, encoding='utf-8')

    # redirecionamentos (Netlify lê _redirects na raiz)
    redir = list(STATIC_REDIRECTS)
    for p in pages:
        for a in p.get('aliases') or []:
            redir.append((a, p['url']))
            if a.endswith('/'):
                redir.append((a.rstrip('/'), p['url']))
    (ROOT / '_redirects').write_text('# gerado pelo build.py: endereços antigos -> páginas novas\n' + ''.join(f'{a}  {b}  301\n' for a, b in redir), encoding='utf-8')

    # llms.txt: apresentação do site pras IAs (nunca inclui /blog/altive/)
    L = ['# João Bêrnardino', '',
         '> Site pessoal de João Bernardino (João Bêrnardino, @ojoaobernardino): growth marketing e vendas, neurociência do hábito e PNL aplicada. Textos em primeira pessoa, com fonte, e resenhas completas de livros de vendas, liderança e mente.', '',
         'Empreendedor, criador de conteúdo, atleta e Growth Marketing & Sales. Engenheiro de Produção (Mackenzie), pós-graduado em Neurociências e Comportamento (PUCRS) e Master Trainer em PNL (SBPNL). Criou o Zero Nóia (como parou de fumar em 2024) e a Comunidade A Obra.', '',
         '## Sobre', '', f"- [Sobre João Bêrnardino]({SITE['url']}/sobre/): quem é, serviços, produtos, canal do YouTube e blog.", '']
    livros = [p for p in posts if p.get('book')]
    if livros:
        L += ['## Livros (resenhas completas)', ''] + [f"- [{p['title']}]({SITE['url']}{p['url']}): {p['description']}" for p in sorted(livros, key=lambda x: x['title'])] + ['']
    outros = [p for p in newest(posts) if not p.get('book')]
    L += ['## Textos', ''] + [f"- [{p['title']}]({SITE['url']}{p['url']}): {p['description']}" for p in outros] + ['']
    L += ['## Seções', ''] + [f"- [{h['name']}]({SITE['url']}{h['url']})" for h in SITE['blog_hubs']] + ['']
    (ROOT / 'llms.txt').write_text('\n'.join(l for l in L if '/altive/' not in l), encoding='utf-8')
    print(f'ok: {len(pages)} páginas + feed + sitemap ({len(urls)} URLs) + {len(redir)} redirecionamentos')
    for p in pages:
        extra = f" [{p['mode']}, {p['total']} textos]" if p['type'] == 'hub' else ''
        print(f"  {p['type']:4s} {p['theme']:5s} {p['url']:50s} {p['words']:5d} palavras{extra}")
    if PENDING:
        (ROOT / '.cache').mkdir(exist_ok=True)
        (ROOT / '.cache' / 'CONFIRMAR.md').write_text('# Fatos a confirmar com o João (saem do HTML, ficam no Markdown)\n\n' + '\n'.join(f'- `{u}`: {t}' for u, t in PENDING), encoding='utf-8')
        print(f'  {len(PENDING)} marcações CONFIRMAR listadas em .cache/CONFIRMAR.md')


if __name__ == '__main__':
    main()
    versiona_estaticos()
