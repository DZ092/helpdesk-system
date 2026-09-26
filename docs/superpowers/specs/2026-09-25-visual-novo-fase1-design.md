# Visual novo do helpdesk-system — Fase 1: fundação + dashboard

Data: 2026-09-25 · Autor: Eduardo Jr. Coelho · Status: aprovado em conversa, aguardando revisão do spec escrito

## 1. Objetivo

Trocar a identidade visual do sistema — hoje monocromática (preto/cinza/branco), sem cor de marca e com interação "só cor, sem movimento" — por uma identidade com acento azul, navegação por abas no topo e um dashboard com indicadores de verdade (gráficos), usando como referência de linguagem visual o case do Behance "Help Desk — chamados do registro à resolução":
https://www.behance.net/gallery/254937531/Help-Desk-chamados-do-registro-a-resolucao

O projeto é dividido em três fases, cada uma com seu próprio ciclo spec → plano → implementação. Este documento cobre só a Fase 1.

| Fase | Conteúdo |
|---|---|
| **1 (este spec)** | tokens visuais novos nos temas, `base.html` + topbar, dashboard com 4 KPIs e 4 gráficos, coluna `resolvido_em` |
| 2 | migrar as páginas internas para o layout novo (`chamados`, `detalhe_chamado`, `meus_chamados`, `acompanhar_chamado`, `admin_usuarios`, `admin_logs`, `meu_token`, `alterar_senha`) |
| 3 | migrar as páginas públicas e de autenticação (`index`, `apresentacao`, `como_funciona`, `recursos`, `login`, `cadastro`, `esqueci_senha`, `redefinir_senha`, `chamado`, `chamado_confirmacao`, `erro`) |

### O que se aproveita da referência

Fundo quase preto com viés azul; cartões com borda sutil e elevação; abas em pílula na barra superior; cartões de KPI com ícone; barras horizontais por departamento, donut, evolução semanal e status; badges coloridos de prioridade e status.

### O que NÃO se aproveita

O logo, o nome/marca e qualquer asset do autor do case (é trabalho de outra pessoa — serve só como referência de linguagem visual). O gradiente roxo → azul da referência também fica de fora: a cor de marca é azul sólido (decisão abaixo).

## 2. Decisões tomadas

| Tema | Decisão |
|---|---|
| Navegação | barra superior com abas em pílula (sem sidebar) |
| Cor de marca | azul sólido `#2D8CF0` |
| Temas | escuro (padrão) + claro + seguir sistema; **tema âmbar removido** |
| Tipografia | mantém Manrope (+ JetBrains Mono só em IDs/token) |
| Interação | elevação/sombra sutil no hover; sem `translateY`/`scale` |
| Estrutura de templates | `base.html` + `base_app.html` + partial `_topbar.html` (herança Jinja) |
| Gráficos | SVG gerado no servidor, sem biblioteca JS |
| Métricas | status ao longo do tempo, por setor, por prioridade, tempo médio de resolução |
| Tempo de resolução | coluna nova `resolvido_em` (migração), não aproximação por `atualizado_em` |
| Período | seletor 7 / 30 / 90 dias / tudo via `?periodo=`, padrão 30 |

## 3. Tokens visuais (`static/css/style.css`)

Os tokens novos valem para as 20 páginas já nesta fase, porque todas carregam `style.css`. As páginas ainda não migradas (Fases 2 e 3) ficam com a paleta nova e o layout antigo até serem migradas.

### Tema escuro (`:root`, padrão)

| Token | Valor | Uso | Contraste |
|---|---|---|---|
| `--bg` | `#0B0D12` | fundo da página | — |
| `--superficie` | `#12151C` | cartões, tabela, topbar | — |
| `--superficie-alt` | `#1A1E27` | hover de linha, input | — |
| `--borda` | `rgba(255,255,255,0.08)` | contorno de cartão | — |
| `--texto` | `#F2F4F8` | texto principal | 16.6:1 sobre `--superficie` |
| `--texto-muted` | `#A3AAB8` | texto secundário | 7.8:1 |
| `--texto-fraco` | `#8B93A3` | legenda, data | 5.9:1 |
| `--acento` | `#2D8CF0` | aba ativa, link, ícone, marca de gráfico | 5.3:1 sobre `--superficie` |
| `--acento-solido` | `#1F6FD1` | fundo de botão primário com texto branco | 4.9:1 (branco sobre ele) |

Motivo do `--acento-solido`: texto branco sobre `#2D8CF0` dá 3.43:1 e reprova o mínimo de 4.5:1 para texto normal. O botão usa `#1F6FD1` (visualmente quase igual); `#2D8CF0` fica para texto, indicador e gráfico, onde passa.

### Tema claro (`[data-theme="light"]`)

Fundo `#F6F7F9`, superfície `#FFFFFF`, texto `#1F2430` (14.5:1), texto secundário `#5B6475` (6.0:1 sobre branco), acento `#1A66C7` (5.6:1 sobre branco, serve para texto e para fundo de botão com texto branco). O cobre atual sai.

Os valores do tema claro que não estão listados aqui (superfície alternativa, bordas, semânticas) devem ser calibrados na implementação e ter o contraste conferido com o mesmo critério (4.5:1 texto normal, 3:1 texto grande e elementos gráficos).

### Semânticas

Mantém a família atual e só recalibra para o fundo novo, conferindo contraste: verde = resolvido; âmbar = prioridade média; laranja = alta; vermelho = crítica; âmbar = em andamento (mesma cor do badge atual). Os tokens `--sucesso-*`, `--erro-*`, `--aviso-*`, `--info-*`, `--prioridade-*` continuam com os mesmos nomes.

### Elevação e raio

- `--sombra-1` (cartão em repouso) e `--sombra-2` (hover): hover = sombra 2 + borda um pouco mais clara. Sem deslocamento nem escala.
- `@media (prefers-reduced-motion: reduce)` → sem transição.
- Raio mantém a escala atual (`--raio-controle` 6px, `--raio-superficie` 10px). Única exceção: abas da topbar em pílula (`999px`).

### Compatibilidade

Os nomes de token antigos usados por páginas ainda não migradas (`--marca`, `--marca-rgb`, `--acento-forte`, `--acento-hover`, `--acento-legivel`, `--cta-*`, `--texto-botao` etc.) viram alias dos novos, para nada quebrar entre as fases. A limpeza dos aliases fica para o fim da Fase 3.

### Remoção do tema âmbar

- CSS: sai o bloco `[data-theme="ambar"]`.
- `static/js/tema.js`: `TEMAS = ["dark", "light"]`; somem as entradas `ambar` de ícone e nome.
- Script inline anti-flash (no `base.html`): só aceita `"dark"` ou `"light"` do `localStorage`; qualquer outro valor salvo (inclusive `"ambar"` de quem escolheu antes) é tratado como "sem escolha" → segue a preferência do sistema → escuro.
- As páginas não migradas ainda têm o botão `data-tema="ambar"` no HTML; o `tema.js` deve ignorar botão de tema desconhecido (não quebrar). O botão some quando cada página for migrada.

## 4. Estrutura de templates

### `templates/base.html`

Único lugar com: `<!DOCTYPE>`, `<meta>`, `<title>{% block titulo %}Help Desk{% endblock %}</title>` (cada página escreve o título inteiro, ex.: `Dashboard · Help Desk`), script inline anti-flash com `nonce="{{ csp_nonce() }}"`, `style.css`, `tema.js`. Blocos: `titulo`, `head_extra`, `corpo`.

### `templates/base_app.html` (estende `base.html`)

Para páginas com usuário logado: inclui `_topbar.html`, envolve o conteúdo em `<main class="app-conteudo">`, mensagens flash e o rodapé atual (`v1.2.0 · by Eduardo Jr. Coelho`, link para o GitHub). Bloco: `conteudo`.

### `templates/_topbar.html`

- Esquerda: marca do próprio projeto ("Help Desk", com ícone próprio simples em SVG — nada da referência).
- Centro, abas em pílula:
  - `Dashboard` → `/dashboard` (todo usuário logado)
  - `Chamados` → `/chamados` (todo usuário logado)
  - `Meus chamados` → `/meus-chamados` (só se `usuario_logado.eh_tecnico`)
  - `Admin` → `/admin/usuarios` (só se `usuario_logado.eh_admin`)
- Aba ativa decidida dentro do partial por `request.endpoint` (a página não passa variável). A aba ativa tem `aria-current="page"`.
- Direita: botão primário `+ Novo chamado` (`/chamado`), seletor de tema (escuro/claro), menu do usuário (nome + tipo) com `Alterar senha` (`/senha`), `Meu token de API` (`/meu-token`) e `Sair` (formulário POST para `/logout` com `csrf_token`, igual ao atual).
- Menu do usuário: `<details>/<summary>` nativo (sem JS novo, acessível por teclado).
- Abaixo de 768px: as abas viram uma faixa com rolagem horizontal; o nome do usuário vira só a inicial.

### Fase 1 migra só `dashboard.html`

O bloco `.acoes` do rodapé do dashboard (Ver chamados / Alterar senha / Meu token / Meus chamados / Painel Admin) é absorvido pela topbar e removido.

## 5. Dados: `resolvido_em`

- `models.py`: `Chamado.resolvido_em = db.Column(db.DateTime, nullable=True, index=True)` — UTC naive, mesmo padrão de `obter_data_utc`.
- Método `Chamado.definir_status(novo_status)`:
  - passou a `"Resolvido"` vindo de outro status → `resolvido_em = obter_data_utc()`;
  - saiu de `"Resolvido"` (reabertura) → `resolvido_em = None`;
  - mesmo status → não mexe.
- Os dois pontos que hoje atribuem status direto passam a usar o método: `rotas/chamados.py` (`atualizar_status_chamado`, hoje `chamado.status = form.status.data`) e `rotas/api.py` (hoje `chamado.status = novo_status`).
- Migração Alembic nova em `migrations/versions/`: adiciona a coluna e faz backfill — chamados já com `status = 'Resolvido'` recebem `resolvido_em = atualizado_em` (melhor dado disponível). `downgrade` remove a coluna.

## 6. Agregação: `metricas.py` (módulo novo)

Funções que consultam o banco e devolvem estruturas simples (dict/list), sem nada de HTML. Todas recebem o instante de referência como parâmetro (`agora`, UTC naive) para os testes controlarem o tempo.

```
PERIODOS = {"7": 7, "30": 30, "90": 90, "tudo": None}
PERIODO_PADRAO = "30"

inicio_do_periodo(chave, agora) -> datetime | None     # chave inválida → PERIODO_PADRAO
kpis(desde) -> dict
    total, abertos, em_andamento, em_aberto (= abertos + em_andamento),
    resolvidos, pct_resolvidos (int 0–100, 0 se total = 0),
    tempo_medio (timedelta | None)
evolucao_semanal(agora, semanas=8) -> list[dict(inicio: date, criados: int, resolvidos: int)]
por_setor(desde, limite=6) -> list[tuple[str, int]]      # maior → menor
por_prioridade(desde) -> list[tuple[str, int]]         # ordem de PRIORIDADES, zeros incluídos
por_status(desde) -> list[tuple[str, int]]             # ordem de STATUS_CHAMADO, zeros incluídos
formatar_duracao(td) -> str                            # None → "—"; < 1h → "45min"; < 24h → "6h20"; senão "2d 4h"
```

Regras:
- `desde = None` significa "tudo".
- Contagens de `kpis`, `por_setor`, `por_prioridade` e `por_status` consideram chamados **criados** no período, com o status atual de cada um.
- `tempo_medio` considera chamados com `resolvido_em` **dentro** do período: média de `resolvido_em − criado_em`.
- `evolucao_semanal` ignora o seletor e mostra sempre as últimas 8 semanas: por semana, quantos foram criados e quantos foram resolvidos (por `resolvido_em`). Semana começa na segunda-feira, calculada no fuso `FUSO_EXIBICAO` de `constantes.py`. O agrupamento por semana é feito em Python (não em SQL), para dar o mesmo resultado no SQLite dos testes e no Postgres de produção.

## 7. Gráficos: `graficos.py` + `templates/_graficos.html`

### `graficos.py` (módulo novo, só geometria, sem banco)

```
barras(itens) -> list[dict(rotulo, valor, pct)]                 # pct relativo ao maior valor, 0–100
donut(itens, raio=...) -> list[dict(rotulo, valor, dasharray, dashoffset)]
linha(valores, largura, altura, margem, teto) -> dict            # pontos (atributo "points"), marcas e grade
empilhada(itens) -> list[dict(rotulo, valor, x_pct, largura_pct)]
```

Toda conta de posição/tamanho fica aqui, testável em Python; o Jinja só imprime valores prontos.

### `templates/_graficos.html` (macros)

`grafico_linhas`, `grafico_barras`, `grafico_donut`, `grafico_empilhado`.

- Tamanhos e posições vão como **atributos SVG** (`width="42%"`, `points="…"`), nunca `style="…"` — o CSP atual (`style-src 'self' https://fonts.googleapis.com`) bloqueia estilo inline.
- Cor por classe CSS com token (`.serie-criados { stroke: var(--acento) }`) → troca de tema sem JS.
- Cores: setor → `--acento`; prioridade → cores semânticas dos badges; status → cores dos badges de status; evolução → criados `--acento`, resolvidos `--sucesso-solido`.
- Acessibilidade: cada `<svg>` com `role="img"` e `aria-label` com um resumo em texto; logo depois, uma `<table class="sr-only">` com os números exatos.
- Estado vazio: se o período não tem chamados, cada cartão mostra "Nenhum chamado neste período" em vez de gráfico zerado.

## 8. Dashboard (`/dashboard`)

Rota continua `@login_required` e visível para todo usuário logado (mesma regra de hoje). Passa a ler `?periodo=` e montar os dados via `metricas.py`.

Layout (`dashboard.html` estendendo `base_app.html`):

1. Cabeçalho: rótulo "Visão geral", título **Dashboard**, seletor de período (links 7 dias / 30 dias / 90 dias / Tudo, o ativo com `aria-current`).
2. Linha de 4 KPIs com ícone SVG (sem emoji): **Total de chamados** · **Resolvidos** (com "x% do total") · **Tempo médio de resolução** (`formatar_duracao`) · **Em aberto** (com "n abertos · m em andamento").
3. Evolução semanal (2/3 da largura) + Status (1/3, barra empilhada com legenda).
4. Por setor (1/2, barras horizontais, top 6) + Por prioridade (1/2, donut com total no centro e legenda).
5. Chamados recentes: a tabela atual dos 5 últimos, restilizada, com link "Ver todos" → `/chamados`.

Abaixo de 900px, os painéis ficam em uma coluna e os KPIs em 2×2 (uma coluna abaixo de 480px). Números com `font-variant-numeric: tabular-nums`.

## 9. Testes (TDD, padrão do `tests/conftest.py`)

Novos (nomes indicativos):
- `test_definir_status_grava_resolvido_em_ao_resolver`
- `test_definir_status_limpa_resolvido_em_ao_reabrir`
- `test_definir_status_mesmo_status_nao_altera_data`
- `test_atualizar_status_pela_rota_grava_resolvido_em`
- `test_atualizar_status_pela_api_grava_resolvido_em`
- `metricas`: `kpis` com dados fixos; `kpis` com banco vazio; período filtra por `criado_em`; `tempo_medio` usa `resolvido_em`; `evolucao_semanal` agrupa na semana certa no fuso de Brasília; `por_prioridade`/`por_status` incluem zeros e respeitam a ordem; `por_setor` respeita o limite; `inicio_do_periodo` com chave inválida cai no padrão; `formatar_duracao` nas quatro faixas.
- `graficos`: `barras` com maior valor = 100%; `barras` com todos zero não divide por zero; `donut` soma o perímetro inteiro; `linha` com valores iguais não divide por zero; `empilhada` soma 100%.
- Rota: `/dashboard` responde 200 e contém os quatro `<svg role="img">` e as tabelas `sr-only`; `/dashboard?periodo=xyz` responde 200 com o padrão; banco vazio mostra o estado vazio; a topbar mostra `Admin` só para admin e `Meus chamados` só para técnico/admin.
- Testes existentes que dependam do HTML antigo do dashboard (texto dos botões `.acoes`, emoji do título, botão âmbar) devem ser ajustados para o comportamento novo — nunca apagados sem substituto.

## 10. Verificação antes de dizer "pronto"

- `python -m pytest -v` com a suíte **inteira** verde.
- Se o número de testes mudou: `grep -rn "<número antigo>"` no repo (fora de `venv/`) e atualizar cada ocorrência real no mesmo PR — hoje: `README.md` (duas frases), `docs/index.html` (meta description, régua do hero, cartão de qualidade), `templates/apresentacao.html` (`.hero-regua-item`), `templates/recursos.html` (cartão de qualidade).
- Abrir o dashboard no Chrome real nos dois temas e em ~400px de largura; screenshot como evidência.
- Conferir o contraste dos tokens do tema claro que foram calibrados na implementação.
- `git diff --ignore-space-at-eol` para garantir que só mudou o necessário (`style.css` usa CRLF: editar com patch cirúrgico preservando `\r\n`).

## 11. Entrega e git

- Quem implementa **só edita arquivos** na pasta do projeto; **não roda** `git add`, `commit` nem `push`. O Edu confere com `git status`/`git diff` e commita.
- Nenhuma marca de geração automatizada em commit, PR ou código (sem assinatura de coautoria automática, sem notas de sessão).
- Uma issue para a Fase 1; branch `feat/visual-novo-fundacao-dashboard` a partir do `main` atualizado; commits pequenos no imperativo (`feat(ui):`, `feat(dados):`, `test:`…); PR com `Closes #N`.
- Ao final, entregar o bloco de comandos em passos (issue → branch → commits → push → PR), um comando por bloco.

## 12. Fora do escopo da Fase 1

- Layout novo de qualquer página além do dashboard.
- Página de Relatórios separada (a exportação PDF/Excel continua onde está).
- Busca/filtros novos na lista de chamados, linha do tempo no detalhe (Fase 2).
- Tempo real, notificações, assistente virtual integrado.

## 13. Riscos

- **Paleta nova em páginas com layout antigo** durante a transição: mitigado pelos aliases de token; conferir visualmente pelo menos `chamados`, `login` e `index` depois da Fase 1.
- **Testes presos ao HTML antigo** do dashboard: ajustar junto, com o mesmo comportamento verificado.
- **Backfill de `resolvido_em`** usa `atualizado_em`, que pode ter mudado depois da resolução em chamados antigos — distorção limitada a dados históricos; chamados novos ficam exatos.
