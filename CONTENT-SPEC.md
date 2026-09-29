# Especificação de conteúdo do joaobernardino.com.br

> **Atualização 29/09/2026 (site v2):** o gerador agora monta o site inteiro. O caminho do arquivo em `content/` é o endereço: `content/blog/zero-noia/como-parar-de-fumar.md` → `/blog/zero-noia/como-parar-de-fumar/`. Seções: `blog/` (off-white), `sobre/` e `produtos/` (padrão LP preto). Tipos: `post`, `page`, `hub`, `blog`, `lp`.
> **Resenha de livro** = `post` em `content/blog/livros/<slug>.md` com o bloco `book:` (titulo, autor, editora, pra_quem, capa `/img/livros/<slug>.webp`, afiliado, nota, e `curto` opcional) e `group:`; a ordem das prateleiras fica em `estantes:` no `content/blog/livros/index.md`. Estrutura obrigatória: ver o piloto `spin-selling.md` (capítulos reais com fonte, FAQ começando por "Quais são os capítulos de X?", Fontes). Livro só vende o livro ou captura e-mail (nunca A Obra).
> **Assinatura padrão (quadro do autor):** "Empreendedor, criador de conteúdo, atleta e Growth Marketing & Sales. Pós em Neurociências e Comportamento (PUCRS), Master Trainer em PNL (SBPNL), Engenheiro de Produção (Mackenzie)."
> **Serviços:** a seção de serviços da /sobre foi publicada por decisão do João em 29/09/2026, ciente da regra de exclusividade abaixo (risco assumido por ele). Nos textos do blog a regra continua valendo.
> **Fatos:** Koin = só BNPL (nunca antifraude). Heineken = off-premise, supermercados, venda futura.
> Publicação: `python3 build.py && python3 check.py` (0 erros) → PR no GitHub → prévia do Netlify → merge.

(Abaixo, a especificação original do blog, que continua valendo pro texto.)


Todo texto do blog é um arquivo Markdown em `content/`. O caminho do arquivo define a URL:

| Arquivo | URL |
|---|---|
| `content/sobre.md` | `/blog/sobre/` |
| `content/zero-noia/index.md` | `/blog/zero-noia/` (hub do cluster) |
| `content/zero-noia/como-parar-de-fumar.md` | `/blog/zero-noia/como-parar-de-fumar/` |
| `content/vendas/index.md` | `/blog/vendas/` (hub) |
| `content/vendas/pnl-em-vendas.md` | `/blog/vendas/pnl-em-vendas/` |

## Frontmatter (YAML, obrigatório)

```yaml
---
title: "Título da página (≤ 60 caracteres, caixa normal, sem travessão)"
description: "Meta description (≤ 155 caracteres). Sempre 'João Bernardino' sem acento quando citar o nome."
type: post            # post | hub | page
cluster: vendas       # vendas | lideranca | neurociencia | treino | zero-noia | livros | uso | parceiros | wjr | dieta | (vazio para page)
date: 2026-09-11      # publicação
updated: 2026-09-11
tags: [pnl, vendas, neurociencia]
summary: "3 a 4 linhas de 'Em resumo' que abrem a página. Frases curtas. Um número entre parênteses."
cta:                  # opcional. Onde a página manda o leitor no fim.
  label: "Comunidade A Obra"
  url: "/blog/a-obra/"
cover: ""             # opcional, caminho em content/img/. Vazio = sem imagem (padrão).
cover_alt: ""
draft: false
---
```

## Corpo (Markdown)

- H1 NÃO vai no corpo: vem do `title`.
- Comece com `## ` (H2). Use H2 para seções e H3 para subseções. Nada de H4.
- Citação em destaque: `> texto` (vira bloco com filete vermelho).
- Callout: linha começando com `!!! ` (ex.: `!!! Regra: pipeline é atividade, não esperança.`).
- Link interno sempre com caminho absoluto e barra final: `[texto](/blog/vendas/)`.
- Link externo de parceiro/afiliado: `[texto](URL){sponsored}` (o build coloca `rel="sponsored noopener"`).
- Link externo comum: `[texto](URL)`.
- Imagem: `![alt descritivo](img/nome.webp)` só quando for foto real. Sem stock, sem IA, sem texto na imagem.
- Tabela em Markdown padrão quando houver número comparável.
- Tamanho: post 800-1.500 palavras; hub 400-700 + a lista de filhas (o build gera a lista automaticamente); page (sobre) 800-1.200.

## Voz do João (regras duras)

1. **PROIBIDO travessão "—" e seta "→"** em qualquer lugar do arquivo (frontmatter incluso). O build reprova.
2. Abre direto, com cena ou fato. Nunca "Nos dias de hoje", nunca pergunta retórica fraca.
3. Pelo menos um número entre parênteses colado na afirmação: "liderei 3 times (400 clientes ativos)".
4. Um reframe "não X, virou Y" onde couber.
5. Fecha com uma regra em uma frase, não com resumo.
6. Jargão de vendas em inglês sem traduzir: pipeline, hunter, closer, ramp, champion, ownership.
7. Verbo forte em 1ª pessoa, voz ativa: assumi, montei, apliquei, cortei.
8. Frases de tamanhos diferentes. Nenhuma tríade simétrica. Um erro do próprio João por texto ("o primeiro teste deu morno").
9. Nenhuma promessa terapêutica, nenhum "segredo", nenhum "método infalível". Saúde: fonte com autor e ano, e "por que eu não te prometo o mesmo".
10. Nome: "João Bêrnardino" só no title das páginas de identidade; "João Bernardino" (sem acento) na description e no corpo quando citar em 3ª pessoa. Nome completo (João Pedro Vendramini Bernardino de Souza) só no `/blog/sobre/`, na 1ª frase.

## Regra de exclusividade (Altive)

**NUNCA** escrever que o João presta consultoria, tem clientes de consultoria, "Work of Sales", "consultor comercial", nem citar a Altive. Motivo: contrato de exclusividade. O que ele faz hoje, em texto público: "Vendedor & Neurotreinador. Estruturo vendas, estudo o cérebro e escrevo aqui." Números de entrevista (TPV, receita, % de conversão, tamanho de carteira, cadeiras, nomes de clientes de empregadores) também ficam FORA do blog: empresas e cargos em uma linha, prova por vivência.

## Regras de link e produto

- Artigo nunca linka checkout. CTA de artigo = nome do produto sem preço, apontando para a página do produto (`/blog/a-obra/`, `/blog/zero-noia/`, `/blog/neurociencia/21-leis/`).
- Exceção decidida pelo João: o HUB `/blog/zero-noia/` linka direto o checkout `https://pay.kiwify.com.br/y0iIDtj` (R$ 19,90) porque não há página de vendas.
- Afiliado (Mercado Livre, Growth, Ultra Mel, Apex, Padrão Puro) só DEPOIS do primeiro CTA, sempre `{sponsored}`, com uma linha de disclosure no início da seção: "Alguns links são de parceiros. Se comprar por eles, eu ganho uma comissão e você paga o mesmo."
- Nunca afiliado nas filhas do Zero Nóia.
- Selva Club: link externo com UTM completa `?utm_source=joaobernardino&utm_medium=blog&utm_campaign=<cluster>&utm_content=<slug>` e disclosure "sou coprodutor do Selva Club".
- WJR: DUAS relações na 1ª dobra (cliente desde 05/03/2024; amigo do Lucas Brito há mais de 20 anos). Nenhum número da WJR sem autorização escrita.
