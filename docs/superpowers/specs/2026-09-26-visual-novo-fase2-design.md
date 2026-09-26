# Visual novo do helpdesk-system — Fase 2: páginas internas

Data: 2026-09-26 · Autor: Eduardo Jr. Coelho · Status: aprovado

Continuação de `2026-09-25-visual-novo-fase1-design.md`. A Fase 1 criou os tokens azuis, `base.html` + `base_app.html` + topbar e o dashboard novo. A Fase 2 leva o mesmo layout para as demais páginas de quem está logado.

## 1. Objetivo

Migrar as 7 páginas internas para `base_app.html` (topbar, tokens, cartões com elevação) e aplicar os padrões visuais da referência já previstos na Fase 1: lista de chamados com título + descrição curta na mesma linha e detalhe do chamado com "estado atual" em trilha de etapas. **Nenhuma regra de negócio muda**: rotas, parâmetros de URL, formulários, permissões, exportação e paginação continuam iguais.

| Página | Template | Rota |
|---|---|---|
| Lista geral | `chamados.html` | `/chamados` |
| Detalhe | `detalhe_chamado.html` | `/chamados/<id>` |
| Meus chamados | `meus_chamados.html` | `/meus-chamados` |
| Usuários (admin) | `admin_usuarios.html` | `/admin/usuarios` |
| Logs (admin) | `admin_logs.html` | `/admin/logs` |
| Token de API | `meu_token.html` | `/meu-token` |
| Alterar senha | `alterar_senha.html` | `/senha` |

## 2. Decisões tomadas

| Tema | Decisão |
|---|---|
| `acompanhar_chamado` | sai da Fase 2 e vai para a Fase 3: é pública (acesso pelo código de acompanhamento, sem login), não tem `usuario_logado` e não pode usar a topbar |
| Emoji nos badges de status (🔴🟡🟢) | trocados por uma bolinha em CSS com a cor do status, em todo lugar que usa badge (inclusive a tabela do dashboard) |
| Alternância lista/grade da referência | fora; só lista |
| Data de início do atendimento | não é criada; a etapa "Em andamento" aparece sem data |
| Links "← Voltar para..." | removidos (a topbar navega); o detalhe mantém "← Chamados" como trilha |

## 3. Peças compartilhadas

### `templates/_badges.html` (novo)

Macros usadas por `dashboard.html`, `chamados.html`, `meus_chamados.html` e `detalhe_chamado.html`, substituindo os blocos `if/elif` de badge repetidos em cada template:

```
{% macro badge_status(status) %}      → <span class="status status-aberto|status-andamento|status-resolvido">Aberto|Em andamento|Resolvido</span>
{% macro badge_prioridade(prioridade) %} → <span class="prioridade prioridade-baixa|prioridade-media|prioridade-alta|prioridade-critica">Baixa|Média|Alta|Crítica</span>
```

- Status fora da lista conhecida cai no visual de "Resolvido" (mesmo comportamento do `else` atual); prioridade desconhecida cai em "Média" (idem).
- A bolinha é `::before` do badge (círculo de 8px, `background: currentColor`), sem emoji e sem `style="…"`.
- Classes `status-*`/`prioridade-*` já existem em `style.css` e continuam valendo.

### Sub-abas do admin

`admin_usuarios.html` e `admin_logs.html` mostram, abaixo do título **Administração**, um par de abas em pílula **Usuários | Logs** (mesmo visual das abas da topbar), com `aria-current="page"` na ativa, decidido por `request.endpoint`. Pode ser um partial `templates/_abas_admin.html` incluído pelas duas páginas.

### CSS

Nova seção "PÁGINAS INTERNAS (visual novo, Fase 2)" no fim de `static/css/style.css` (CRLF — editar só com leitura/escrita em bytes). Cor só por token. Reaproveita `.cartao`, `.pagina-cabecalho`, `.pagina-rotulo`, `.pagina-titulo`, `.sr-only` da Fase 1.

## 4. Páginas

### `chamados.html`
- Cabeçalho: rótulo "Operação de suporte", título **Chamados**; à direita, "Exportar Excel" e "Exportar PDF" só para técnico/admin (mesmas URLs de hoje, que preservam os filtros).
- Filtros num cartão: busca em largura total; embaixo, status, prioridade, setor, responsável, data inicial e data final; botões **Aplicar** e **Limpar** (`/chamados`). Mesmos `name=` de hoje.
- Tabela: colunas "Título" e "Descrição" viram uma coluna "Chamado" — título em negrito com link para o detalhe e, embaixo, a descrição cortada em uma linha com reticências (CSS `text-overflow`; o texto completo continua no HTML). Demais colunas mantidas: ID, Usuário, Setor, Prioridade (badge), Status (badge), Responsável, Ação.
- Saem: botão "Novo chamado" (está na topbar) e atalho "Meus chamados" (é aba).
- Paginação restilizada com os mesmos links e textos ("Mostrando X de Y chamado(s) — página P de N", "← Anterior", "Próxima →").
- Estado vazio: mensagem atual mantida, dentro do cartão.

### `meus_chamados.html`
Mesmo padrão visual da lista geral (coluna "Chamado" com título + descrição curta, badges), sem filtros e sem exportação, como hoje. Cabeçalho: rótulo "Seu atendimento", título **Meus chamados**.

### `detalhe_chamado.html`
Duas colunas (uma só abaixo de 900px):
- **Principal:** trilha "← Chamados"; rótulo "Chamado #N"; título; cartão **Descrição** (texto + galeria de anexos); cartão **Histórico** com os comentários em linha do tempo vertical (autor, data, mensagem, anexos do comentário) e, no fim, o formulário "Adicionar atualização" (mesmos campos, `action`, `enctype` e regra de exibição de hoje — só técnico).
- **Lateral:**
  - Cartão **Estado atual**: badge do status; trilha de 3 etapas Aberto → Em andamento → Resolvido, com as etapas já alcançadas marcadas e a atual destacada (`aria-current="step"`); datas: Aberto = `criado_em|data_local`, Resolvido = `resolvido_em|data_local` quando existir, Em andamento sem data. Abaixo, o botão de atendimento (Iniciar atendimento / Marcar como resolvido) com a mesma regra de hoje (técnico e status ≠ Resolvido), sem emoji.
  - Cartão **Informações**: solicitante, setor, prioridade (badge), responsável (ou "Aguardando atribuição"), aberto em, última atualização.
- Mensagem flash continua no topo (vem do `base_app`).

### `admin_usuarios.html` e `admin_logs.html`
Cabeçalho "Painel administrativo" / **Administração** + sub-abas Usuários | Logs. Conteúdo atual dentro de cartões, restilizado: em Usuários, a tabela com o formulário de alterar tipo e o de excluir (CSRF e a confirmação em JavaScript com `nonce`, que já existem); em Logs, a tabela e a paginação atual ("Mostrando X de Y registro(s) — página P de N", "← Anterior", "Próxima →"). Nenhum formulário muda de `action`, método ou campos.

### `meu_token.html` e `alterar_senha.html`
Cartão centralizado (largura máxima ~560px) dentro do `app-conteudo`, título sem emoji ("Meu token de API", "Alterar senha"). Campos, mensagens, fluxo de geração/cópia do token e regras de senha iguais aos de hoje. Scripts inline existentes mantêm o `nonce`.

## 5. Testes (TDD)

Novos:
- `badge_status` e `badge_prioridade`: classe e texto certos para cada valor; valor desconhecido cai no padrão; nenhum emoji no HTML gerado.
- As 7 páginas renderizam com `class="topbar"` e sem `class="usuario-logado"`.
- Nenhuma das 7 páginas tem `style="`.
- Sub-abas do admin: `aria-current="page"` em Usuários em `/admin/usuarios` e em Logs em `/admin/logs`.
- Trilha de estado: chamado Aberto marca só a primeira etapa como atual; Em andamento marca a segunda; Resolvido marca a terceira e mostra a data de `resolvido_em`.
- Lista: a descrição aparece na linha do chamado; o botão "Novo chamado" duplicado não existe mais na página.
- Nenhum badge com emoji de status em `/dashboard`, `/chamados`, `/meus-chamados` e no detalhe.

Existentes: testes presos a texto antigo (ex.: "Painel Administrativo", "Voltar") são ajustados para verificar o mesmo comportamento no HTML novo — nunca apagados sem substituto.

## 6. Verificação antes de dizer "pronto"

- Suíte inteira verde; contagem nova atualizada em todos os lugares que citam o número de testes (hoje 249: README ×2, `docs/index.html` ×3, `templates/apresentacao.html`, `templates/recursos.html`, landing comercial, README do repo de perfil, "Sobre" do LinkedIn).
- Capturas das 7 páginas nos temas escuro e claro e em ~400px, com dados de exemplo gerados pelo cliente de teste (nunca com o banco real); sem rolagem horizontal da página.
- CRLF preservado nos arquivos que já usam CRLF.
- Nenhuma mudança de rota, parâmetro, formulário ou permissão (conferir no diff que `rotas/` só muda se for estritamente necessário para o template).

## 7. Entrega e git

Mesmo formato da Fase 1: quem implementa só edita arquivos; o Edu commita. Nenhuma marca de geração automatizada em código, commit ou PR. Uma issue para a Fase 2, branch `feat/visual-novo-paginas-internas`, PR com `Closes #N`. Comandos git na VM só com `--no-optional-locks`; o app nunca é aberto com a configuração real.

## 8. Fora do escopo

`acompanhar_chamado` e demais páginas públicas/autenticação (Fase 3); alternância lista/grade; coluna de data de início do atendimento; limpeza de CSS morto e dos aliases de token antigos (Fase 3); qualquer mudança de backend.

## 9. Riscos

- **Testes presos a texto do HTML antigo** (56 asserções de texto em `test_app.py`/`test_rotas.py`): rodar a suíte cedo e ajustar mantendo a intenção.
- **Formulários do admin e do detalhe** (CSRF, confirmação de exclusão, upload): o HTML muda de lugar, os atributos não. Revisão compara `action`, `method`, `name` e `enctype` antes/depois.
- **Tabelas largas no celular**: manter o padrão atual de `.tabela-rolavel` / cartões por linha em telas estreitas.
