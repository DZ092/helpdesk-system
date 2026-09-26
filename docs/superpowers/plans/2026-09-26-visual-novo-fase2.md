# Visual novo — Fase 2 (páginas internas) Implementation Plan

**Goal:** Levar as 7 páginas internas (lista de chamados, detalhe, meus chamados, usuários e logs do admin, token de API e alterar senha) para `base_app.html` com topbar, cartões e badges sem emoji, e dar ao detalhe a trilha de "estado atual" — sem mudar nenhuma regra de negócio.

**Architecture:** Cada página passa a estender `base_app.html` (Fase 1) e só preenche `titulo` e `conteudo`. Os if/elif de badge repetidos viram duas macros em `templates/_badges.html`; as sub-abas do admin ficam num partial `templates/_abas_admin.html`. O CSS novo entra no fim de `static/css/style.css`, numa seção "PÁGINAS INTERNAS (visual novo, Fase 2)" que cada task estende. Rotas, formulários, URLs e permissões não mudam.

**Tech Stack:** Python 3.10+, Flask 3.1, Jinja2, pytest. Sem dependência nova.

**Spec:** `docs/superpowers/specs/2026-09-26-visual-novo-fase2-design.md`

## Global Constraints

- **Git só leitura, e sempre com `--no-optional-locks`.** Na VM, `git status`/`git diff` sem essa flag criam `.git/index.lock`, que a VM não consegue apagar. Use `git --no-optional-locks status --short` e `git --no-optional-locks diff ...`.
- **Git é do Edu.** Quem executa este plano **só edita arquivos**; nunca roda `git add`, `git commit`, `git push`, `git switch` nem cria branch. Os passos "Arquivos do commit" só listam o que o Edu vai commitar.
- **Nenhuma marca de geração automatizada** em código, comentário, mensagem de commit sugerida ou PR.
- **Onde editar:** a pasta do projeto fica em `$HOME/mnt/helpdesk-system` na VM (no Windows: `C:\dev\helpdesk-system`). Os scripts auxiliares deste plano ficam **fora** do repo, em `$HOME/fase2-scripts/`.
- **Nunca abrir o app com a configuração real:** nada de `flask run`, `flask db`, `create_app()` sem `CONFIG_DE_TESTE`, nem leitura/escrita em `instance/`. Dados de exemplo só pelo cliente de teste (banco em memória).
- **Fim de linha:** o repo normaliza (`.gitattributes` com `* text=auto`; o índice guarda LF). No disco os arquivos estão em CRLF. Arquivo reescrito por inteiro (template novo ou reescrito, teste novo) pode ser gravado em LF. Arquivo editado em parte (`style.css`, `dashboard.html`, `README.md`, `docs/index.html`, `apresentacao.html`, `recursos.html`) só com os scripts do plano, que leem e gravam em bytes preservando o terminador — nunca misturar CRLF e LF no mesmo arquivo.
- **Rodar testes (VM):** `cd $HOME/mnt/helpdesk-system && $HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider <alvo> -q`. Se `$HOME/venv-helpdesk` não existir: `python3 -m venv $HOME/venv-helpdesk && $HOME/venv-helpdesk/bin/pip install -q -r $HOME/mnt/helpdesk-system/requirements.txt pytest`. Baseline antes da Fase 2: **249 passed**. Esperado no fim: **296 passed**.
- **CSP:** nada de atributo `style="…"` nem `<style>` inline; todo `<script>` inline leva `nonce="{{ csp_nonce() }}"`.
- **Cores só por token.** Nenhuma cor literal no CSS novo. Fundo de elemento preenchido usa `--acento-solido`, nunca `--acento` (o teste `test_botoes_usam_acento_solido_como_fundo` barra `background: var(--acento);` no arquivo inteiro).
- **Sem emoji** em página interna: badges de status viram bolinha em CSS; títulos perdem o emoji.
- **Nada muda em `rotas/`, `models.py`, formulários (`action`, `method`, `name`, `enctype`) ou permissões.**
- **Textos preservados:** "Mostrando X de Y chamado(s) — página P de N", "Mostrando X de Y registro(s) — página P de N", "← Anterior", "Próxima →", "Nenhum chamado encontrado com os filtros selecionados.", "Painel Administrativo" (é por ele que `test_app.py` reconhece a página do admin).
- **Assinatura:** `Eduardo Jr. Coelho` (vem do `base_app.html`, não mexer).

## Review Focus

1. **Chamado reaberto com `resolvido_em` antigo** (dado legado, status Aberto com a data preenchida) → a etapa Resolvido não pode mostrar data. Teste na Task 3.
2. **Status ou prioridade fora da lista** ("Cancelado", vazio, `None`) → badge cai em Resolvido/Média, e a trilha trata o status como Resolvido. Testes nas Tasks 1 e 3.
3. **Página além do fim da lista** (`/chamados?pagina=9` com 1 chamado) → 200, "Mostrando 0 de 1 chamado(s)", sem tabela vazia quebrada. Teste na Task 2.
4. **Descrição muito longa** → o corte em uma linha é só visual; o texto inteiro continua no HTML. Teste na Task 2.
5. **Exportação a partir de uma lista filtrada** → os links de Excel/PDF levam os filtros atuais. Teste na Task 2.

## Mapa de arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `templates/_badges.html` | criar | macros `badge_status` e `badge_prioridade` |
| `templates/_abas_admin.html` | criar | sub-abas Usuários \| Logs |
| `templates/dashboard.html` | modificar | usar as macros de badge |
| `templates/chamados.html` | reescrever | lista geral no layout novo |
| `templates/meus_chamados.html` | reescrever | meus chamados no layout novo |
| `templates/detalhe_chamado.html` | reescrever | duas colunas + trilha de estado |
| `templates/admin_usuarios.html`, `templates/admin_logs.html` | reescrever | admin com sub-abas |
| `templates/meu_token.html`, `templates/alterar_senha.html` | reescrever | cartão estreito |
| `static/css/style.css` | modificar (anexar) | seção "PÁGINAS INTERNAS (visual novo, Fase 2)" |
| `tests/test_badges.py`, `tests/test_listas_chamados.py`, `tests/test_detalhe_chamado.py`, `tests/test_admin_paginas.py`, `tests/test_conta_paginas.py` | criar | testes novos (47) |
| `README.md`, `docs/index.html`, `templates/apresentacao.html`, `templates/recursos.html` | modificar | contagem de testes (Task 6) |

Ordem: Task 1 (macros e CSS dos badges) → Tasks 2, 3 (usam as macros) → Tasks 4, 5 (independentes) → Task 6 (contagem e verificação). Cada task anexa seu trecho de CSS ao fim do arquivo, depois do trecho da task anterior.

## Scripts auxiliares (criar uma vez, antes da Task 1)

Crie a pasta `$HOME/fase2-scripts/` e salve nela o script abaixo como `anexar_css.py`. Ele anexa um trecho ao fim de `style.css` mantendo o fim de linha do arquivo. Rode sempre a partir da raiz do repo.

```python
"""Anexa um trecho ao fim de static/css/style.css preservando o fim de linha
do arquivo. Uso: python anexar_css.py caminho/do/trecho.css"""
import sys
from pathlib import Path

caminho = Path("static/css/style.css")
bruto = caminho.read_bytes()
eol = b"\r\n" if b"\r\n" in bruto else b"\n"
trecho = Path(sys.argv[1]).read_text(encoding="utf-8").replace("\r\n", "\n").strip("\n")
if not bruto.endswith(eol):
    bruto += eol
caminho.write_bytes(bruto + eol + trecho.replace("\n", eol.decode()).encode("utf-8") + eol)
print("style.css: trecho anexado")
```

---

### Task 1: Macros de badge e bolinha de status

**Files:**
- Create: `templates/_badges.html`
- Modify: `templates/dashboard.html` (import + os dois blocos de badge da tabela "Chamados recentes")
- Modify: `static/css/style.css` (anexar ao fim)
- Test: `tests/test_badges.py`

**Interfaces:**
- Produces: `{% from "_badges.html" import badge_status, badge_prioridade %}`. `badge_status(status)` devolve exatamente `<span class="status status-aberto|status-andamento|status-resolvido">Aberto|Em andamento|Resolvido</span>`; `badge_prioridade(prioridade)` devolve `<span class="prioridade prioridade-baixa|prioridade-media|prioridade-alta|prioridade-critica">Baixa|Média|Alta|Crítica</span>`. Sem espaço em volta (as macros usam `{%- -%}`).
- Produces (CSS): cabeçalho da seção "PÁGINAS INTERNAS (visual novo, Fase 2)" e a regra `.status::before` com `background: currentColor`.

- [ ] **Step 1: Escrever o teste** — criar `tests/test_badges.py`:

```python
"""Badges de status e prioridade (visual novo, Fase 2)."""

import re
from pathlib import Path

import pytest

from extensions import db
from models import Chamado

RAIZ = Path(__file__).resolve().parent.parent
SENHA = "senha-de-teste"
EMOJIS_DE_STATUS = ("🔴", "🟡", "🟢")


def _macros(app):
    return app.jinja_env.get_template("_badges.html").module


@pytest.mark.parametrize(
    "status, classe",
    [
        ("Aberto", "status-aberto"),
        ("Em andamento", "status-andamento"),
        ("Resolvido", "status-resolvido"),
    ],
)
def test_badge_status_tem_classe_e_texto_certos(app, status, classe):
    html = str(_macros(app).badge_status(status))

    assert html == f'<span class="status {classe}">{status}</span>'


@pytest.mark.parametrize("status", ["Cancelado", "", None])
def test_status_desconhecido_cai_em_resolvido(app, status):
    html = str(_macros(app).badge_status(status))

    assert html == '<span class="status status-resolvido">Resolvido</span>'


@pytest.mark.parametrize(
    "prioridade, classe",
    [
        ("Baixa", "prioridade-baixa"),
        ("Média", "prioridade-media"),
        ("Alta", "prioridade-alta"),
        ("Crítica", "prioridade-critica"),
    ],
)
def test_badge_prioridade_tem_classe_e_texto_certos(app, prioridade, classe):
    html = str(_macros(app).badge_prioridade(prioridade))

    assert html == f'<span class="prioridade {classe}">{prioridade}</span>'


@pytest.mark.parametrize("prioridade", ["Urgente", "", None])
def test_prioridade_desconhecida_cai_em_media(app, prioridade):
    html = str(_macros(app).badge_prioridade(prioridade))

    assert html == '<span class="prioridade prioridade-media">Média</span>'


def test_bolinha_do_status_vem_do_css():
    css = (RAIZ / "static" / "css" / "style.css").read_text(encoding="utf-8")
    regra = re.search(r"\.status::before\s*\{([^}]*)\}", css)

    assert regra, "falta a regra .status::before"
    assert "background: currentColor" in regra.group(1)


def test_dashboard_usa_os_badges_sem_emoji(client, criar_usuario):
    criar_usuario(nome="Ana Admin", email="admin@teste.com", tipo="Administrador")
    client.post("/login", data={"email": "admin@teste.com", "senha": SENHA})
    for status in ("Aberto", "Em andamento", "Resolvido"):
        db.session.add(
            Chamado(usuario="Maria", setor="TI", titulo=f"Chamado {status}",
                    descricao="Teste", status=status, prioridade="Crítica")
        )
    db.session.commit()

    html = client.get("/dashboard").get_data(as_text=True)

    assert '<span class="status status-andamento">Em andamento</span>' in html
    assert '<span class="prioridade prioridade-critica">Crítica</span>' in html
    for emoji in EMOJIS_DE_STATUS:
        assert emoji not in html
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider tests/test_badges.py -q`
Expected: FAIL — os testes de macro com `TemplateNotFound: _badges.html`; `test_bolinha_do_status_vem_do_css` com "falta a regra .status::before"; `test_dashboard_usa_os_badges_sem_emoji` porque o dashboard ainda tem 🔴🟡🟢.

- [ ] **Step 3: Criar `templates/_badges.html`**

```jinja
{# Badges de status e prioridade (visual novo, Fase 2). Um lugar só para o
   mapeamento valor → classe, usado pelo dashboard, pelas listas e pelo
   detalhe. A bolinha colorida do status é CSS (.status::before), não emoji.
   Valor fora da lista cai no mesmo padrão dos if/elif antigos: status vira
   "Resolvido" e prioridade vira "Média". #}
{% macro badge_status(status) -%}
{%- if status == "Aberto" -%}
<span class="status status-aberto">Aberto</span>
{%- elif status == "Em andamento" -%}
<span class="status status-andamento">Em andamento</span>
{%- else -%}
<span class="status status-resolvido">Resolvido</span>
{%- endif -%}
{%- endmacro %}

{% macro badge_prioridade(prioridade) -%}
{%- if prioridade == "Baixa" -%}
<span class="prioridade prioridade-baixa">Baixa</span>
{%- elif prioridade == "Alta" -%}
<span class="prioridade prioridade-alta">Alta</span>
{%- elif prioridade == "Crítica" -%}
<span class="prioridade prioridade-critica">Crítica</span>
{%- else -%}
<span class="prioridade prioridade-media">Média</span>
{%- endif -%}
{%- endmacro %}
```

- [ ] **Step 4: Trocar os badges do dashboard** — salvar como `$HOME/fase2-scripts/t1_dashboard.py` e rodar `cd $HOME/mnt/helpdesk-system && python3 $HOME/fase2-scripts/t1_dashboard.py`:

```python
import re
from pathlib import Path

caminho = Path("templates/dashboard.html")
bruto = caminho.read_bytes()
eol = b"\r\n" if b"\r\n" in bruto else b"\n"
texto = bruto.decode("utf-8").replace("\r\n", "\n")

texto, n = re.subn(
    r'\{% import "_graficos.html" as g %\}\n',
    '{% import "_graficos.html" as g %}\n{% from "_badges.html" import badge_status, badge_prioridade %}\n',
    texto,
    count=1,
)
assert n == 1, "import do _graficos.html não encontrado"

texto, n = re.subn(
    r'\{% if chamado\.prioridade == "Baixa" %\}.*?\{% endif %\}',
    "{{ badge_prioridade(chamado.prioridade) }}",
    texto,
    count=1,
    flags=re.S,
)
assert n == 1, "bloco de prioridade não encontrado"

texto, n = re.subn(
    r'\{% if chamado\.status == "Aberto" %\}\s*<span class="status status-aberto">.*?\{% endif %\}',
    "{{ badge_status(chamado.status) }}",
    texto,
    count=1,
    flags=re.S,
)
assert n == 1, "bloco de status não encontrado"

caminho.write_bytes(texto.replace("\n", eol.decode()).encode("utf-8"))
print("dashboard.html atualizado")
```

Expected: `dashboard.html atualizado`. Conferir com `grep -n "badge_" templates/dashboard.html`: 3 linhas (import, prioridade, status). As colunas de ação (▶/✓) da tabela ficam como estão.

- [ ] **Step 5: Anexar o CSS** — salvar o trecho abaixo como `$HOME/fase2-scripts/css_t1.css` e rodar `python3 $HOME/fase2-scripts/anexar_css.py $HOME/fase2-scripts/css_t1.css` na raiz do repo:

```css
/* ==============================
   PÁGINAS INTERNAS (visual novo, Fase 2) — listas, detalhe, admin e conta
   Páginas que estendem base_app.html. Cor só por token; hover troca cor e
   sombra, nada se desloca.
   ============================== */

/* BADGES — a bolinha herda a cor do texto do status (currentColor), então
   acompanha os tokens de cada tema sem regra extra. Substitui os emoji. */
.status {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    white-space: nowrap;
}

.status::before {
    content: "";
    flex: none;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: currentColor;
}

.prioridade {
    white-space: nowrap;
}
```

- [ ] **Step 6: Rodar e ver passar**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider tests/test_badges.py tests/test_dashboard.py -q`
Expected: `22 passed`.

- [ ] **Step 7: Suíte inteira** — Expected: `264 passed`.

- [ ] **Step 8: Arquivos do commit** (o Edu commita): `templates/_badges.html`, `templates/dashboard.html`, `static/css/style.css`, `tests/test_badges.py`. Mensagem sugerida: `feat(ui): badges de status e prioridade em macro, com bolinha em CSS`.

---

### Task 2: Lista geral e "Meus chamados"

**Files:**
- Rewrite: `templates/chamados.html`, `templates/meus_chamados.html`
- Modify: `static/css/style.css` (anexar ao fim)
- Test: `tests/test_listas_chamados.py`

**Interfaces:**
- Consumes: `badge_status`, `badge_prioridade` (Task 1); `base_app.html` com o bloco `conteudo` e a mensagem flash; classes da Fase 1 `.pagina-cabecalho`, `.pagina-rotulo`, `.pagina-titulo`, `.cartao`, `.estado-vazio`.
- Produces (CSS, usadas pelas Tasks 3–5): `.pagina-pilha` (coluna com gap 20px), `.cartao-bloco` (padding 20px), `.pagina-acoes`, `.botao-contorno`, `.lista-rodape` (contagem + `.paginacao`), `.cartao .tabela-chamados` alinhada à esquerda.
- Variáveis de template (vindas de `rotas/chamados.py`, sem mudança): `chamados`, `busca`, `status_filtro`, `prioridade_filtro`, `setor_filtro`, `responsavel_filtro`, `data_inicio`, `data_fim`, `tecnicos`, `setores`, `paginacao`; em `meus_chamados.html`, só `chamados`.

- [ ] **Step 1: Escrever o teste** — criar `tests/test_listas_chamados.py`:

```python
"""Lista geral e "Meus chamados" no layout novo (visual novo, Fase 2)."""

import re

from extensions import db
from models import Chamado

SENHA = "senha-de-teste"
EMOJIS_DE_STATUS = ("🔴", "🟡", "🟢")


def _entrar(client, criar_usuario, tipo="Usuário"):
    email = {"Usuário": "usuario@teste.com", "Técnico": "tecnico@teste.com"}[tipo]
    usuario = criar_usuario(nome=f"Pessoa {tipo}", email=email, tipo=tipo)
    client.post("/login", data={"email": email, "senha": SENHA})
    return usuario


def _chamado(titulo="Computador não liga", descricao="Tela preta ao ligar", status="Aberto", responsavel=None):
    chamado = Chamado(
        usuario="Maria",
        setor="Financeiro",
        titulo=titulo,
        descricao=descricao,
        status=status,
        prioridade="Alta",
        responsavel_id=responsavel.id if responsavel else None,
    )
    db.session.add(chamado)
    db.session.commit()
    return chamado


def _layout_novo(html):
    assert 'class="topbar"' in html
    assert 'class="usuario-logado"' not in html
    assert 'style="' not in html
    assert "Voltar" not in html
    for emoji in EMOJIS_DE_STATUS:
        assert emoji not in html


def test_lista_usa_o_layout_novo_com_titulo_e_descricao(client, criar_usuario):
    _entrar(client, criar_usuario)
    chamado = _chamado()

    html = client.get("/chamados").get_data(as_text=True)

    _layout_novo(html)
    assert '<h1 class="pagina-titulo">Chamados</h1>' in html
    assert f'<a class="chamado-titulo" href="/chamados/{chamado.id}">Computador não liga</a>' in html
    assert '<span class="chamado-descricao">Tela preta ao ligar</span>' in html
    assert '<span class="prioridade prioridade-alta">Alta</span>' in html
    assert '<span class="status status-aberto">Aberto</span>' in html


def test_lista_nao_repete_atalhos_que_estao_na_topbar(client, criar_usuario):
    _entrar(client, criar_usuario, tipo="Técnico")
    _chamado()

    html = client.get("/chamados").get_data(as_text=True)

    assert html.count("Novo chamado") == 1  # só o botão da topbar
    assert "Novo Chamado" not in html
    assert html.count('href="/meus-chamados"') == 1  # só a aba da topbar


def test_exportacao_so_para_tecnico_e_preserva_os_filtros(client, criar_usuario):
    _entrar(client, criar_usuario, tipo="Técnico")

    html = client.get("/chamados?status=Aberto").get_data(as_text=True)
    links = re.findall(r'href="(/chamados/exportar\?[^"]*)"', html)

    assert len(links) == 2
    assert all("status=Aberto" in link for link in links)
    assert any("formato=excel" in link for link in links)
    assert any("formato=pdf" in link for link in links)


def test_usuario_comum_nao_ve_exportacao(client, criar_usuario):
    _entrar(client, criar_usuario)

    html = client.get("/chamados").get_data(as_text=True)

    assert "/chamados/exportar" not in html
    assert "Exportar" not in html


def test_filtros_mantem_os_mesmos_campos_e_valores(client, criar_usuario):
    _entrar(client, criar_usuario)

    html = client.get("/chamados?busca=impressora&status=Resolvido").get_data(as_text=True)

    assert '<form method="GET" action="/chamados" class="filtros">' in html
    for nome in ("busca", "status", "prioridade", "setor", "responsavel", "data_inicio", "data_fim"):
        assert f'name="{nome}"' in html
    assert 'value="impressora"' in html
    assert '<option value="Resolvido" selected>' in html
    assert ">Aplicar</button>" in html
    assert 'href="/chamados" class="limpar-filtro"' in html


def test_paginacao_mantem_textos_e_marca_a_pagina_atual(client, criar_usuario):
    _entrar(client, criar_usuario)
    for i in range(16):  # 15 por página
        _chamado(titulo=f"Chamado {i}")

    pagina_1 = client.get("/chamados").get_data(as_text=True)
    pagina_2 = client.get("/chamados?pagina=2").get_data(as_text=True)

    assert "Mostrando 15 de 16 chamado(s) — página 1 de 2" in pagina_1
    assert "Próxima →" in pagina_1
    assert '<span class="pagina-atual" aria-current="page">1</span>' in pagina_1
    assert "← Anterior" in pagina_2
    assert "Mostrando 1 de 16 chamado(s) — página 2 de 2" in pagina_2


def test_lista_vazia_mostra_a_mensagem_sem_tabela(client, criar_usuario):
    _entrar(client, criar_usuario)

    html = client.get("/chamados?busca=nada-com-isso").get_data(as_text=True)

    assert "Nenhum chamado encontrado com os filtros selecionados." in html
    assert 'class="tabela-chamados"' not in html


def test_pagina_alem_do_fim_mantem_contagem_e_navegacao(client, criar_usuario):
    _entrar(client, criar_usuario)
    _chamado()

    resposta = client.get("/chamados?pagina=9")
    html = resposta.get_data(as_text=True)

    assert resposta.status_code == 200
    assert "Mostrando 0 de 1 chamado(s)" in html


def test_descricao_longa_continua_inteira_no_html(client, criar_usuario):
    _entrar(client, criar_usuario)
    descricao = "Linha de descrição comprida " * 20
    _chamado(descricao=descricao.strip())

    html = client.get("/chamados").get_data(as_text=True)

    assert descricao.strip() in html


def test_meus_chamados_usa_o_layout_novo(client, criar_usuario):
    tecnico = _entrar(client, criar_usuario, tipo="Técnico")
    _chamado(titulo="Meu chamado", descricao="Mouse sem resposta", responsavel=tecnico)
    _chamado(titulo="Chamado de outra pessoa")

    html = client.get("/meus-chamados").get_data(as_text=True)

    _layout_novo(html)
    assert '<h1 class="pagina-titulo">Meus chamados</h1>' in html
    assert '<span class="chamado-descricao">Mouse sem resposta</span>' in html
    assert "Chamado de outra pessoa" not in html
    assert "Exportar" not in html
    assert re.search(r'href="/meus-chamados"\s+aria-current="page"', html)


def test_meus_chamados_vazio_mostra_orientacao(client, criar_usuario):
    _entrar(client, criar_usuario, tipo="Técnico")

    html = client.get("/meus-chamados").get_data(as_text=True)

    assert "Você ainda não é responsável por nenhum chamado." in html
    assert 'class="tabela-chamados"' not in html
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider tests/test_listas_chamados.py -q`
Expected: 6 FAIL (`test_lista_usa_o_layout_novo_com_titulo_e_descricao`, `test_lista_nao_repete_atalhos_que_estao_na_topbar`, `test_filtros_mantem_os_mesmos_campos_e_valores`, `test_paginacao_mantem_textos_e_marca_a_pagina_atual`, `test_lista_vazia_mostra_a_mensagem_sem_tabela`, `test_meus_chamados_usa_o_layout_novo`). Os outros 5 já passam: são guardas de comportamento que precisa continuar igual.

- [ ] **Step 3: Reescrever `templates/chamados.html`** (arquivo inteiro):

```jinja
{% extends "base_app.html" %}
{% from "_badges.html" import badge_status, badge_prioridade %}

{% block titulo %}Chamados · Help Desk{% endblock %}

{% block conteudo %}
<div class="pagina-cabecalho">
    <div>
        <p class="pagina-rotulo">Operação de suporte</p>
        <h1 class="pagina-titulo">Chamados</h1>
    </div>
    {% if usuario_logado.eh_tecnico %}
    <div class="pagina-acoes">
        <a class="botao-contorno" href="{{ url_for('chamados.exportar_chamados', **dict(request.args, formato='excel')) }}">Exportar Excel</a>
        <a class="botao-contorno" href="{{ url_for('chamados.exportar_chamados', **dict(request.args, formato='pdf')) }}">Exportar PDF</a>
    </div>
    {% endif %}
</div>

<div class="pagina-pilha">
    <section class="cartao cartao-bloco" aria-label="Filtros">
        <form method="GET" action="/chamados" class="filtros">
            <div class="filtro-campo">
                <label for="filtro-busca">Buscar</label>
                <input type="text" id="filtro-busca" name="busca" placeholder="Buscar por título..." value="{{ busca }}">
            </div>
            <div class="filtros-campos">
                <div class="filtro-campo">
                    <label for="filtro-status">Status</label>
                    <select id="filtro-status" name="status">
                        <option value="">Todos os status</option>
                        <option value="Aberto" {% if status_filtro == "Aberto" %}selected{% endif %}>Aberto</option>
                        <option value="Em andamento" {% if status_filtro == "Em andamento" %}selected{% endif %}>Em andamento</option>
                        <option value="Resolvido" {% if status_filtro == "Resolvido" %}selected{% endif %}>Resolvido</option>
                    </select>
                </div>
                <div class="filtro-campo">
                    <label for="filtro-prioridade">Prioridade</label>
                    <select id="filtro-prioridade" name="prioridade">
                        <option value="">Todas as prioridades</option>
                        <option value="Baixa" {% if prioridade_filtro == "Baixa" %}selected{% endif %}>Baixa</option>
                        <option value="Média" {% if prioridade_filtro == "Média" %}selected{% endif %}>Média</option>
                        <option value="Alta" {% if prioridade_filtro == "Alta" %}selected{% endif %}>Alta</option>
                        <option value="Crítica" {% if prioridade_filtro == "Crítica" %}selected{% endif %}>Crítica</option>
                    </select>
                </div>
                <div class="filtro-campo">
                    <label for="filtro-setor">Setor</label>
                    <select id="filtro-setor" name="setor">
                        <option value="">Todos os setores</option>
                        {% for setor in setores %}
                        <option value="{{ setor }}" {% if setor_filtro == setor %}selected{% endif %}>{{ setor }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="filtro-campo">
                    <label for="filtro-responsavel">Responsável</label>
                    <select id="filtro-responsavel" name="responsavel">
                        <option value="">Todos os responsáveis</option>
                        <option value="nenhum" {% if responsavel_filtro == "nenhum" %}selected{% endif %}>Aguardando atribuição</option>
                        {% for tecnico in tecnicos %}
                        <option value="{{ tecnico.id }}" {% if responsavel_filtro == tecnico.id|string %}selected{% endif %}>{{ tecnico.nome }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="filtro-campo">
                    <label for="filtro-data-inicio">De</label>
                    <input type="date" id="filtro-data-inicio" name="data_inicio" value="{{ data_inicio }}">
                </div>
                <div class="filtro-campo">
                    <label for="filtro-data-fim">Até</label>
                    <input type="date" id="filtro-data-fim" name="data_fim" value="{{ data_fim }}">
                </div>
            </div>
            <div class="filtros-acoes">
                <button class="botao-filtro" type="submit">Aplicar</button>
                <a href="/chamados" class="limpar-filtro">Limpar</a>
            </div>
        </form>
    </section>

    <section class="cartao cartao-bloco" aria-label="Lista de chamados">
        {% if chamados %}
        <div class="tabela-rolavel">
            <table class="tabela-chamados">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Chamado</th>
                        <th>Usuário</th>
                        <th>Setor</th>
                        <th>Prioridade</th>
                        <th>Status</th>
                        <th>Responsável</th>
                        <th>Ação</th>
                    </tr>
                </thead>
                <tbody>
                    {% for chamado in chamados %}
                    <tr>
                        <td data-label="ID">{{ chamado.id }}</td>
                        <td data-label="Chamado" class="coluna-chamado">
                            <div class="chamado-resumo">
                                <a class="chamado-titulo" href="/chamados/{{ chamado.id }}">{{ chamado.titulo }}</a>
                                <span class="chamado-descricao">{{ chamado.descricao }}</span>
                            </div>
                        </td>
                        <td data-label="Usuário">{{ chamado.usuario }}</td>
                        <td data-label="Setor">{{ chamado.setor }}</td>
                        <td data-label="Prioridade">{{ badge_prioridade(chamado.prioridade) }}</td>
                        <td data-label="Status">{{ badge_status(chamado.status) }}</td>
                        <td data-label="Responsável">
                            {% if chamado.responsavel %}
                            {{ chamado.responsavel.nome }}
                            {% else %}
                            <span class="finalizado">Aguardando atribuição</span>
                            {% endif %}
                        </td>
                        <td data-label="Ação">
                            {% if usuario_logado.eh_tecnico %}
                                {% if chamado.status == "Aberto" %}
                                <a class="acao" href="/chamados/{{ chamado.id }}" title="Iniciar atendimento">▶</a>
                                {% elif chamado.status == "Em andamento" %}
                                <a class="acao" href="/chamados/{{ chamado.id }}" title="Marcar como resolvido">✓</a>
                                {% else %}
                                <span class="acao acao-finalizado" title="Chamado finalizado">✓</span>
                                {% endif %}
                            {% else %}
                            <span class="finalizado">—</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}

        {% if paginacao.total > 0 %}
        <div class="lista-rodape">
            <p class="vazio">Mostrando {{ chamados|length }} de {{ paginacao.total }} chamado(s) — página {{ paginacao.page }} de {{ paginacao.pages }}</p>
            {% if paginacao.pages > 1 %}
            <nav class="paginacao" aria-label="Páginas">
                {% if paginacao.has_prev %}
                <a class="pagina-link" href="{{ url_for('chamados.lista_chamados', **dict(request.args, pagina=paginacao.prev_num)) }}">← Anterior</a>
                {% endif %}
                {% for numero in paginacao.iter_pages(left_edge=1, right_edge=1, left_current=2, right_current=2) %}
                    {% if numero %}
                        {% if numero == paginacao.page %}
                        <span class="pagina-atual" aria-current="page">{{ numero }}</span>
                        {% else %}
                        <a class="pagina-link" href="{{ url_for('chamados.lista_chamados', **dict(request.args, pagina=numero)) }}">{{ numero }}</a>
                        {% endif %}
                    {% else %}
                    <span class="pagina-reticencias">…</span>
                    {% endif %}
                {% endfor %}
                {% if paginacao.has_next %}
                <a class="pagina-link" href="{{ url_for('chamados.lista_chamados', **dict(request.args, pagina=paginacao.next_num)) }}">Próxima →</a>
                {% endif %}
            </nav>
            {% endif %}
        </div>
        {% else %}
        <p class="estado-vazio">Nenhum chamado encontrado com os filtros selecionados.</p>
        {% endif %}
    </section>
</div>
{% endblock %}
```

- [ ] **Step 4: Reescrever `templates/meus_chamados.html`** (arquivo inteiro):

```jinja
{% extends "base_app.html" %}
{% from "_badges.html" import badge_status, badge_prioridade %}

{% block titulo %}Meus chamados · Help Desk{% endblock %}

{% block conteudo %}
<div class="pagina-cabecalho">
    <div>
        <p class="pagina-rotulo">Seu atendimento</p>
        <h1 class="pagina-titulo">Meus chamados</h1>
    </div>
</div>

<section class="cartao cartao-bloco" aria-label="Chamados sob sua responsabilidade">
    {% if chamados %}
    <div class="tabela-rolavel">
        <table class="tabela-chamados">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Chamado</th>
                    <th>Usuário</th>
                    <th>Setor</th>
                    <th>Prioridade</th>
                    <th>Status</th>
                    <th>Ação</th>
                </tr>
            </thead>
            <tbody>
                {% for chamado in chamados %}
                <tr>
                    <td data-label="ID">{{ chamado.id }}</td>
                    <td data-label="Chamado" class="coluna-chamado">
                        <div class="chamado-resumo">
                            <a class="chamado-titulo" href="/chamados/{{ chamado.id }}">{{ chamado.titulo }}</a>
                            <span class="chamado-descricao">{{ chamado.descricao }}</span>
                        </div>
                    </td>
                    <td data-label="Usuário">{{ chamado.usuario }}</td>
                    <td data-label="Setor">{{ chamado.setor }}</td>
                    <td data-label="Prioridade">{{ badge_prioridade(chamado.prioridade) }}</td>
                    <td data-label="Status">{{ badge_status(chamado.status) }}</td>
                    <td data-label="Ação">
                        {% if chamado.status == "Resolvido" %}
                        <span class="acao acao-finalizado" title="Chamado finalizado">✓</span>
                        {% else %}
                        <a class="acao acao-texto" href="/chamados/{{ chamado.id }}">Ver detalhes</a>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% else %}
    <p class="estado-vazio">Você ainda não é responsável por nenhum chamado. Assuma um chamado na lista geral para que ele apareça aqui.</p>
    {% endif %}
</section>
{% endblock %}
```

- [ ] **Step 5: Anexar o CSS** — salvar como `$HOME/fase2-scripts/css_t2.css` e rodar `python3 $HOME/fase2-scripts/anexar_css.py $HOME/fase2-scripts/css_t2.css`:

```css
/* ESTRUTURA COMUM — pilha de cartões com espaçamento por gap, sem margem
   solta entre blocos. */
.pagina-pilha {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.cartao-bloco {
    min-width: 0;
    padding: 20px;
}

.pagina-acoes {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

.botao-contorno {
    display: inline-flex;
    align-items: center;
    padding: 8px 14px;
    border: 1px solid var(--borda-forte);
    border-radius: var(--raio-controle);
    background: var(--superficie);
    color: var(--texto);
    font-size: 14px;
    font-weight: 700;
    text-decoration: none;
    white-space: nowrap;
    transition: background-color 0.15s ease, border-color 0.15s ease;
}

.botao-contorno:hover {
    background: var(--superficie-alt);
    border-color: var(--acento);
}

/* FILTROS DA LISTA — busca em largura total; os demais campos se ajeitam em
   quantas colunas couberem. */
.filtros {
    display: flex;
    flex-direction: column;
    gap: 14px;
}

.filtros-campos {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 12px;
}

.filtro-campo {
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-width: 0;
}

.filtro-campo label {
    color: var(--texto-muted);
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

.filtro-campo input,
.filtro-campo select {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid var(--borda);
    border-radius: var(--raio-controle);
    background: var(--superficie-alt);
    color: var(--texto);
    font-family: inherit;
    font-size: 14px;
}

.filtro-campo input::placeholder {
    color: var(--texto-fraco);
}

.filtros-acoes {
    display: flex;
    align-items: center;
    gap: 16px;
}

/* TABELAS DENTRO DE CARTÃO — alinhadas à esquerda, sem a margem de cima
   que a tabela antiga usava para se afastar do título. */
.cartao .tabela-rolavel {
    margin-top: 0;
}

.cartao .tabela-chamados th,
.cartao .tabela-chamados td {
    text-align: left;
}

/* COLUNA "CHAMADO" — título com link e, embaixo, a descrição cortada numa
   linha só. O texto inteiro continua no HTML (leitor de tela e busca da
   página); só a exibição é cortada. */
.chamado-resumo {
    display: flex;
    flex-direction: column;
    gap: 3px;
    min-width: 0;
    max-width: 42ch;
}

.chamado-titulo {
    color: var(--texto);
    font-weight: 700;
    text-decoration: none;
}

.chamado-titulo:hover {
    color: var(--acento);
    text-decoration: underline;
}

.chamado-descricao {
    overflow: hidden;
    color: var(--texto-muted);
    font-size: 13px;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* RODAPÉ DA LISTA — contagem de um lado, paginação do outro. */
.lista-rodape {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-top: 16px;
}

.lista-rodape .paginacao {
    flex-wrap: wrap;
    margin-top: 0;
}

.pagina-link:hover {
    border-color: var(--acento);
}

.botao-contorno:focus-visible,
.chamado-titulo:focus-visible,
.pagina-link:focus-visible,
.limpar-filtro:focus-visible,
.filtro-campo input:focus-visible,
.filtro-campo select:focus-visible {
    outline: 2px solid var(--acento);
    outline-offset: 2px;
}

@media (max-width: 900px) {
    .cartao .tabela-chamados td {
        text-align: right;
    }

    .chamado-resumo {
        max-width: 65%;
        text-align: right;
    }

    .filtros-acoes .botao-filtro {
        flex: 1;
    }
}

@media (prefers-reduced-motion: reduce) {
    .botao-contorno {
        transition: none;
    }
}
```

- [ ] **Step 6: Rodar e ver passar**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider tests/test_listas_chamados.py tests/test_rotas.py -q`
Expected: tudo passa.

- [ ] **Step 7: Suíte inteira** — Expected: `275 passed`.

- [ ] **Step 8: Arquivos do commit:** `templates/chamados.html`, `templates/meus_chamados.html`, `static/css/style.css`, `tests/test_listas_chamados.py`. Mensagem sugerida: `feat(ui): lista de chamados e meus chamados no layout novo`.

---

### Task 3: Detalhe do chamado com trilha de estado

**Files:**
- Rewrite: `templates/detalhe_chamado.html`
- Modify: `static/css/style.css` (anexar ao fim)
- Test: `tests/test_detalhe_chamado.py`

**Interfaces:**
- Consumes: `badge_status`, `badge_prioridade` (Task 1); `.pagina-pilha`, `.cartao-bloco` (Task 2); `.painel-cabecalho`, `.painel-titulo` (Fase 1); `.formulario`, `.formulario-comentario`, `.galeria-anexos`, `.botao`, `.botao-sucesso`, `.descricao-detalhe` (CSS antigo, mantido).
- Variáveis de template (sem mudança na rota): `chamado`, `comentarios`, `anexos_chamado`; `comentario.autor.nome`, `comentario.anexos`, `anexo.url`, `anexo.nome_original`; `chamado.resolvido_em` (Fase 1).
- Produces: marcação da trilha `<li class="etapa[ etapa-concluida| etapa-atual]"[ aria-current="step"]>`, uma por etapa, na ordem Aberto, Em andamento, Resolvido.

- [ ] **Step 1: Escrever o teste** — criar `tests/test_detalhe_chamado.py`:

```python
"""Detalhe do chamado no layout novo (visual novo, Fase 2)."""

import re
from datetime import datetime

from extensions import db
from models import Chamado

SENHA = "senha-de-teste"
EMOJIS_DE_STATUS = ("🔴", "🟡", "🟢")
ETAPA = re.compile(r'<li class="(etapa[^"]*)"( aria-current="step")?>')


def _entrar(client, criar_usuario, tipo="Usuário"):
    email = {"Usuário": "usuario@teste.com", "Técnico": "tecnico@teste.com"}[tipo]
    usuario = criar_usuario(nome=f"Pessoa {tipo}", email=email, tipo=tipo)
    client.post("/login", data={"email": email, "senha": SENHA})
    return usuario


def _chamado(status="Aberto", resolvido_em=None):
    chamado = Chamado(
        usuario="Maria",
        setor="Financeiro",
        titulo="Computador não liga",
        descricao="Tela preta ao ligar",
        status=status,
        prioridade="Crítica",
        resolvido_em=resolvido_em,
    )
    db.session.add(chamado)
    db.session.commit()
    return chamado


def _etapas(html):
    return [(classe, bool(atual)) for classe, atual in ETAPA.findall(html)]


def test_detalhe_usa_o_layout_novo(client, criar_usuario):
    _entrar(client, criar_usuario)
    chamado = _chamado()

    html = client.get(f"/chamados/{chamado.id}").get_data(as_text=True)

    assert 'class="topbar"' in html
    assert 'class="usuario-logado"' not in html
    assert 'style="' not in html
    assert "Voltar" not in html
    for emoji in EMOJIS_DE_STATUS:
        assert emoji not in html
    assert '<a href="/chamados">← Chamados</a>' in html
    assert f'<p class="pagina-rotulo">Chamado #{chamado.id}</p>' in html
    assert '<h1 class="pagina-titulo">Computador não liga</h1>' in html
    assert re.search(r'href="/chamados"\s+aria-current="page"', html)  # aba Chamados


def test_informacoes_mostram_badge_e_responsavel_pendente(client, criar_usuario):
    _entrar(client, criar_usuario)
    chamado = _chamado()

    html = client.get(f"/chamados/{chamado.id}").get_data(as_text=True)

    assert "<dt>Prioridade</dt><dd><span class=\"prioridade prioridade-critica\">Crítica</span></dd>" in html
    assert "<dt>Responsável</dt><dd>Aguardando atribuição</dd>" in html


def test_trilha_de_chamado_aberto_marca_a_primeira_etapa(client, criar_usuario):
    _entrar(client, criar_usuario)
    chamado = _chamado("Aberto")

    html = client.get(f"/chamados/{chamado.id}").get_data(as_text=True)

    assert _etapas(html) == [("etapa etapa-atual", True), ("etapa", False), ("etapa", False)]


def test_trilha_de_chamado_em_andamento_marca_a_segunda_etapa(client, criar_usuario):
    _entrar(client, criar_usuario)
    chamado = _chamado("Em andamento")

    html = client.get(f"/chamados/{chamado.id}").get_data(as_text=True)

    assert _etapas(html) == [
        ("etapa etapa-concluida", False),
        ("etapa etapa-atual", True),
        ("etapa", False),
    ]


def test_trilha_de_chamado_resolvido_mostra_a_data_de_resolucao(client, criar_usuario):
    _entrar(client, criar_usuario)
    chamado = _chamado("Resolvido", resolvido_em=datetime(2026, 3, 10, 15, 0))

    html = client.get(f"/chamados/{chamado.id}").get_data(as_text=True)

    assert _etapas(html) == [
        ("etapa etapa-concluida", False),
        ("etapa etapa-concluida", False),
        ("etapa etapa-atual", True),
    ]
    assert '<span class="etapa-data">10/03/2026 às 12:00</span>' in html  # UTC-3


def test_resolvido_em_antigo_nao_aparece_em_chamado_reaberto(client, criar_usuario):
    """Dado legado: status Aberto com resolvido_em preenchido não pode mostrar
    data na etapa Resolvido, que ainda não foi alcançada."""
    _entrar(client, criar_usuario)
    chamado = _chamado("Aberto", resolvido_em=datetime(2026, 3, 10, 15, 0))

    html = client.get(f"/chamados/{chamado.id}").get_data(as_text=True)

    assert "10/03/2026 às 12:00" not in html


def test_status_desconhecido_conta_como_resolvido_na_trilha(client, criar_usuario):
    _entrar(client, criar_usuario)
    chamado = _chamado("Cancelado")

    html = client.get(f"/chamados/{chamado.id}").get_data(as_text=True)

    assert _etapas(html)[2] == ("etapa etapa-atual", True)


def test_tecnico_ve_o_botao_de_atendimento_sem_emoji(client, criar_usuario):
    _entrar(client, criar_usuario, tipo="Técnico")
    aberto = _chamado("Aberto")
    andamento = _chamado("Em andamento")

    html_aberto = client.get(f"/chamados/{aberto.id}").get_data(as_text=True)
    html_andamento = client.get(f"/chamados/{andamento.id}").get_data(as_text=True)

    assert f'action="/chamados/{aberto.id}/status"' in html_aberto
    assert '<input type="hidden" name="status" value="Em andamento">' in html_aberto
    assert ">Iniciar atendimento</button>" in html_aberto
    assert '<input type="hidden" name="status" value="Resolvido">' in html_andamento
    assert ">Marcar como resolvido</button>" in html_andamento
    assert "▶" not in html_aberto
    assert "✓ Marcar" not in html_andamento


def test_sem_botao_de_atendimento_para_usuario_comum(client, criar_usuario):
    _entrar(client, criar_usuario)
    aberto = _chamado("Aberto")

    html = client.get(f"/chamados/{aberto.id}").get_data(as_text=True)

    assert "/status" not in html
    assert "/comentarios" not in html


def test_sem_botao_de_atendimento_em_chamado_resolvido(client, criar_usuario):
    _entrar(client, criar_usuario, tipo="Técnico")
    resolvido = _chamado("Resolvido")

    html = client.get(f"/chamados/{resolvido.id}").get_data(as_text=True)

    assert f'action="/chamados/{resolvido.id}/status"' not in html
    assert f'action="/chamados/{resolvido.id}/comentarios"' in html  # técnico ainda comenta


def test_historico_mostra_comentarios_e_formulario_do_tecnico(client, criar_usuario):
    _entrar(client, criar_usuario, tipo="Técnico")
    chamado = _chamado("Em andamento")

    vazio = client.get(f"/chamados/{chamado.id}").get_data(as_text=True)
    client.post(f"/chamados/{chamado.id}/comentarios", data={"mensagem": "Troquei o cabo de energia"})
    html = client.get(f"/chamados/{chamado.id}").get_data(as_text=True)

    assert "Ainda não há atualizações neste chamado." in vazio
    assert re.search(r'<li class="historico-item">.*Troquei o cabo de energia', html, re.S)
    assert f'action="/chamados/{chamado.id}/comentarios"' in html
    assert 'enctype="multipart/form-data"' in html
    assert 'name="mensagem"' in html and 'name="anexos"' in html


def test_resolver_pelo_detalhe_continua_funcionando(client, criar_usuario):
    _entrar(client, criar_usuario, tipo="Técnico")
    chamado = _chamado("Em andamento")

    client.post(f"/chamados/{chamado.id}/status", data={"status": "Resolvido"})
    html = client.get(f"/chamados/{chamado.id}").get_data(as_text=True)

    assert _etapas(html)[2] == ("etapa etapa-atual", True)
    assert html.count('class="etapa-data"') == 2
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider tests/test_detalhe_chamado.py -q`
Expected: 9 FAIL (layout, informações, as trilhas de Aberto, Em andamento, Resolvido e de status desconhecido, botão do técnico, histórico, resolver pelo detalhe). Passam já: `test_resolvido_em_antigo_nao_aparece_em_chamado_reaberto`, `test_sem_botao_de_atendimento_para_usuario_comum`, `test_sem_botao_de_atendimento_em_chamado_resolvido` (guardas).

- [ ] **Step 3: Reescrever `templates/detalhe_chamado.html`** (arquivo inteiro):

```jinja
{% extends "base_app.html" %}
{% from "_badges.html" import badge_status, badge_prioridade %}

{% block titulo %}Chamado #{{ chamado.id }} · Help Desk{% endblock %}

{% macro galeria(anexos) -%}
<div class="galeria-anexos">
    {% for anexo in anexos %}
    <a href="{{ anexo.url }}" target="_blank" rel="noopener" title="{{ anexo.nome_original }}"><img src="{{ anexo.url }}" alt="{{ anexo.nome_original }}" loading="lazy"></a>
    {% endfor %}
</div>
{%- endmacro %}

{% block conteudo %}
{# Etapa atual da trilha: 0 = Aberto, 1 = Em andamento, 2 = Resolvido. Status
   desconhecido conta como Resolvido, igual ao badge. #}
{% set etapa_atual = {"Aberto": 0, "Em andamento": 1}.get(chamado.status, 2) %}

<nav class="trilha" aria-label="Trilha de navegação">
    <a href="{{ url_for('chamados.lista_chamados') }}">← Chamados</a>
</nav>

<div class="pagina-cabecalho">
    <div>
        <p class="pagina-rotulo">Chamado #{{ chamado.id }}</p>
        <h1 class="pagina-titulo">{{ chamado.titulo }}</h1>
    </div>
</div>

<div class="detalhe-grade">
    <div class="pagina-pilha">
        <section class="cartao cartao-bloco" aria-labelledby="titulo-descricao">
            <h2 class="painel-titulo" id="titulo-descricao">Descrição</h2>
            <p class="descricao-detalhe">{{ chamado.descricao }}</p>
            {% if anexos_chamado %}{{ galeria(anexos_chamado) }}{% endif %}
        </section>

        <section class="cartao cartao-bloco" aria-labelledby="titulo-historico">
            <h2 class="painel-titulo" id="titulo-historico">Histórico</h2>
            {% if comentarios %}
            <ol class="historico">
                {% for comentario in comentarios %}
                <li class="historico-item">
                    <div class="historico-cabecalho">
                        <strong>{{ comentario.autor.nome }}</strong>
                        <time>{{ comentario.criado_em|data_local }}</time>
                    </div>
                    <p class="historico-mensagem">{{ comentario.mensagem }}</p>
                    {% if comentario.anexos %}{{ galeria(comentario.anexos) }}{% endif %}
                </li>
                {% endfor %}
            </ol>
            {% else %}
            <p class="estado-vazio">Ainda não há atualizações neste chamado.</p>
            {% endif %}

            {% if usuario_logado.eh_tecnico %}
            <form method="POST" action="/chamados/{{ chamado.id }}/comentarios" class="formulario formulario-comentario" enctype="multipart/form-data">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                <label for="mensagem">Adicionar atualização</label>
                <textarea id="mensagem" name="mensagem" rows="4" placeholder="Descreva o que foi feito ou o próximo passo..." required></textarea>
                <label for="anexos-comentario">Anexar imagens (opcional)</label>
                <input type="file" id="anexos-comentario" name="anexos" accept="image/png,image/jpeg,image/webp" multiple>
                <button class="botao" type="submit">Adicionar atualização</button>
            </form>
            {% endif %}
        </section>
    </div>

    <aside class="pagina-pilha" aria-label="Estado e informações do chamado">
        <section class="cartao cartao-bloco" aria-labelledby="titulo-estado">
            <div class="painel-cabecalho">
                <h2 class="painel-titulo" id="titulo-estado">Estado atual</h2>
                {{ badge_status(chamado.status) }}
            </div>
            <ol class="etapas">
                {% for nome in ["Aberto", "Em andamento", "Resolvido"] %}
                {% set indice = loop.index0 %}
                <li class="etapa{% if indice < etapa_atual %} etapa-concluida{% elif indice == etapa_atual %} etapa-atual{% endif %}"{% if indice == etapa_atual %} aria-current="step"{% endif %}>
                    <span class="etapa-marcador" aria-hidden="true"></span>
                    <span class="etapa-texto">
                        <span class="etapa-nome">{{ nome }}</span>
                        {% if indice == 0 %}
                        <span class="etapa-data">{{ chamado.criado_em|data_local }}</span>
                        {% elif indice == 2 and etapa_atual == 2 and chamado.resolvido_em %}
                        <span class="etapa-data">{{ chamado.resolvido_em|data_local }}</span>
                        {% endif %}
                    </span>
                </li>
                {% endfor %}
            </ol>

            {% if usuario_logado.eh_tecnico and chamado.status != 'Resolvido' %}
            <form method="POST" action="/chamados/{{ chamado.id }}/status" class="estado-acao">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                {% if chamado.status == 'Aberto' %}
                <input type="hidden" name="status" value="Em andamento">
                <button class="botao botao-largo" type="submit">Iniciar atendimento</button>
                {% else %}
                <input type="hidden" name="status" value="Resolvido">
                <button class="botao botao-sucesso botao-largo" type="submit">Marcar como resolvido</button>
                {% endif %}
            </form>
            {% endif %}
        </section>

        <section class="cartao cartao-bloco" aria-labelledby="titulo-informacoes">
            <h2 class="painel-titulo" id="titulo-informacoes">Informações</h2>
            <dl class="informacoes">
                <div><dt>Solicitante</dt><dd>{{ chamado.usuario }}</dd></div>
                <div><dt>Setor</dt><dd>{{ chamado.setor }}</dd></div>
                <div><dt>Prioridade</dt><dd>{{ badge_prioridade(chamado.prioridade) }}</dd></div>
                <div><dt>Responsável</dt><dd>{{ chamado.responsavel.nome if chamado.responsavel else 'Aguardando atribuição' }}</dd></div>
                <div><dt>Aberto em</dt><dd>{{ chamado.criado_em|data_local }}</dd></div>
                <div><dt>Última atualização</dt><dd>{{ chamado.atualizado_em|data_local }}</dd></div>
            </dl>
        </section>
    </aside>
</div>
{% endblock %}
```

- [ ] **Step 4: Anexar o CSS** — salvar como `$HOME/fase2-scripts/css_t3.css` e rodar `python3 $HOME/fase2-scripts/anexar_css.py $HOME/fase2-scripts/css_t3.css`:

```css
/* DETALHE DO CHAMADO — coluna principal (descrição e histórico) e lateral
   (estado atual e informações). Uma coluna só abaixo de 900px. */
.trilha {
    margin-bottom: 8px;
    font-size: 14px;
}

.trilha a {
    color: var(--texto-muted);
    font-weight: 600;
    text-decoration: none;
}

.trilha a:hover {
    color: var(--acento);
    text-decoration: underline;
}

.detalhe-grade {
    display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(260px, 1fr);
    gap: 20px;
    align-items: start;
}

.detalhe-grade .painel-titulo {
    margin-bottom: 12px;
}

.detalhe-grade .painel-cabecalho {
    align-items: center;
}

.detalhe-grade .painel-cabecalho .painel-titulo {
    margin-bottom: 0;
}

/* Histórico em linha do tempo: um trilho vertical com um ponto por
   atualização. */
.historico {
    display: flex;
    flex-direction: column;
    gap: 16px;
    margin: 0 0 8px;
    padding: 0 0 0 20px;
    border-left: 2px solid var(--borda);
    list-style: none;
}

.historico-item {
    position: relative;
    padding: 14px;
    border-radius: var(--raio-controle);
    background: var(--superficie-alt);
}

.historico-item::before {
    content: "";
    position: absolute;
    top: 18px;
    left: -27px;
    width: 12px;
    height: 12px;
    border: 2px solid var(--superficie);
    border-radius: 50%;
    background: var(--acento-solido);
}

.historico-cabecalho {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 4px 12px;
    margin-bottom: 6px;
}

.historico-cabecalho time {
    color: var(--texto-fraco);
    font-size: 13px;
}

.historico-mensagem {
    line-height: 1.6;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
}

.descricao-detalhe {
    overflow-wrap: anywhere;
}

/* Trilha de etapas do estado atual. A etapa atual ganha o marcador cheio
   com anel; as já passadas, o marcador cheio; as futuras, só o contorno. */
.etapas {
    display: flex;
    flex-direction: column;
    margin: 16px 0 0;
    padding: 0;
    list-style: none;
}

.etapa {
    position: relative;
    display: flex;
    gap: 12px;
    padding-bottom: 18px;
}

.etapa:last-child {
    padding-bottom: 0;
}

.etapa:not(:last-child)::after {
    content: "";
    position: absolute;
    top: 16px;
    bottom: 0;
    left: 6px;
    width: 2px;
    background: var(--borda);
}

.etapa-concluida:not(:last-child)::after {
    background: var(--acento-solido);
}

.etapa-marcador {
    flex: none;
    width: 14px;
    height: 14px;
    margin-top: 2px;
    border: 2px solid var(--borda-forte);
    border-radius: 50%;
    background: var(--superficie);
}

.etapa-concluida .etapa-marcador {
    border-color: var(--acento);
    background: var(--acento-solido);
}

.etapa-atual .etapa-marcador {
    border-color: var(--acento);
    background: var(--acento-solido);
    box-shadow: 0 0 0 4px var(--acento-suave);
}

.etapa-texto {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.etapa-nome {
    color: var(--texto-muted);
    font-weight: 600;
}

.etapa-concluida .etapa-nome,
.etapa-atual .etapa-nome {
    color: var(--texto);
}

.etapa-atual .etapa-nome {
    font-weight: 700;
}

.etapa-data {
    color: var(--texto-fraco);
    font-size: 13px;
}

.estado-acao {
    margin-top: 20px;
}

.botao-largo {
    width: 100%;
}

/* Informações em pares rótulo/valor, cada par numa linha. */
.informacoes {
    display: flex;
    flex-direction: column;
    margin: 0;
}

.informacoes > div {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid var(--borda);
}

.informacoes > div:last-child {
    border-bottom: none;
    padding-bottom: 0;
}

.informacoes dt {
    color: var(--texto-muted);
    font-size: 13px;
}

.informacoes dd {
    margin: 0;
    font-weight: 600;
    text-align: right;
    overflow-wrap: anywhere;
}

.trilha a:focus-visible {
    outline: 2px solid var(--acento);
    outline-offset: 2px;
}

@media (max-width: 900px) {
    .detalhe-grade {
        grid-template-columns: minmax(0, 1fr);
    }
}
```

- [ ] **Step 5: Rodar e ver passar**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider tests/test_detalhe_chamado.py tests/test_rotas.py tests/test_tema.py -q`
Expected: tudo passa (o `test_tema.py` confirma que nenhum fundo usa `var(--acento)`).

- [ ] **Step 6: Suíte inteira** — Expected: `287 passed`.

- [ ] **Step 7: Arquivos do commit:** `templates/detalhe_chamado.html`, `static/css/style.css`, `tests/test_detalhe_chamado.py`. Mensagem sugerida: `feat(ui): detalhe do chamado em duas colunas com trilha de estado`.

---

### Task 4: Administração com sub-abas

**Files:**
- Create: `templates/_abas_admin.html`
- Rewrite: `templates/admin_usuarios.html`, `templates/admin_logs.html`
- Modify: `static/css/style.css` (anexar ao fim)
- Test: `tests/test_admin_paginas.py`

**Interfaces:**
- Consumes: `.cartao-bloco`, `.lista-rodape` (Task 2); `.form-tipo-usuario`, `.botao-perigo`, `.botao-filtro`, `.finalizado` (CSS antigo).
- Variáveis de template (sem mudança): `usuarios` (admin_usuarios), `logs` e `paginacao` (admin_logs).
- Produces: `<nav class="abas-secundarias">` com `aria-current="page"` na aba do endpoint atual (`admin.admin_usuarios` ou `admin.admin_logs`). Atenção: a topbar também tem `href="/admin/usuarios" aria-current="page"` (aba Admin) em toda página do admin — por isso os testes procuram só dentro do `<nav class="abas-secundarias">`.

- [ ] **Step 1: Escrever o teste** — criar `tests/test_admin_paginas.py`:

```python
"""Páginas da administração no layout novo (visual novo, Fase 2)."""

import re

SENHA = "senha-de-teste"
SUB_ABAS = re.compile(r'<nav class="abas-secundarias".*?</nav>', re.S)


def _entrar_como_admin(client, criar_usuario):
    admin = criar_usuario(nome="Ana Admin", email="admin@teste.com", tipo="Administrador")
    client.post("/login", data={"email": "admin@teste.com", "senha": SENHA})
    return admin


def _sub_abas(html):
    bloco = SUB_ABAS.search(html)
    assert bloco, "sub-abas da administração não encontradas"
    return bloco.group(0)


def _layout_novo(html):
    assert 'class="topbar"' in html
    assert 'class="usuario-logado"' not in html
    assert 'style="' not in html
    assert "Voltar" not in html
    assert '<h1 class="pagina-titulo">Administração</h1>' in html


def test_usuarios_usa_o_layout_novo_com_a_sub_aba_ativa(client, criar_usuario):
    _entrar_como_admin(client, criar_usuario)

    html = client.get("/admin/usuarios").get_data(as_text=True)
    abas = _sub_abas(html)

    _layout_novo(html)
    assert re.search(r'href="/admin/usuarios"\s+aria-current="page">Usuários</a>', abas)
    assert re.search(r'href="/admin/logs"\s*>Logs</a>', abas)


def test_logs_usa_o_layout_novo_com_a_sub_aba_ativa(client, criar_usuario):
    _entrar_como_admin(client, criar_usuario)

    html = client.get("/admin/logs").get_data(as_text=True)
    abas = _sub_abas(html)

    _layout_novo(html)
    assert re.search(r'href="/admin/logs"\s+aria-current="page">Logs</a>', abas)
    assert re.search(r'href="/admin/usuarios"\s*>Usuários</a>', abas)
    assert "Mostrando 1 de 1 registro(s) — página 1 de 1" in html


def test_formularios_do_admin_nao_mudam(client, criar_usuario):
    admin = _entrar_como_admin(client, criar_usuario)
    outro = criar_usuario(nome="Bruno", email="bruno@teste.com", tipo="Usuário")

    html = client.get("/admin/usuarios").get_data(as_text=True)

    assert f'<form method="POST" action="/admin/usuarios/{outro.id}/tipo" class="form-tipo-usuario">' in html
    assert f'action="/admin/usuarios/{outro.id}/excluir"' in html
    assert 'data-nome="Bruno"' in html
    assert f'action="/admin/usuarios/{admin.id}/excluir"' not in html  # não se exclui
    assert re.search(r'<script nonce="[^"]+">\s*document\.querySelectorAll\("\.form-excluir"\)', html)


def test_trocar_perfil_pelo_painel_continua_funcionando(client, criar_usuario):
    _entrar_como_admin(client, criar_usuario)
    outro = criar_usuario(nome="Bruno", email="bruno@teste.com", tipo="Usuário")

    resposta = client.post(
        f"/admin/usuarios/{outro.id}/tipo",
        data={"tipo_usuario": "Técnico"},
        follow_redirects=True,
    )
    html = resposta.get_data(as_text=True)

    assert '<p class="sucesso">' in html  # a mensagem vem do base_app
    assert re.search(r'<option value="Técnico" selected>Técnico</option>', html)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider tests/test_admin_paginas.py -q`
Expected: 2 FAIL (`test_usuarios_usa_o_layout_novo_com_a_sub_aba_ativa`, `test_logs_usa_o_layout_novo_com_a_sub_aba_ativa`: sub-abas não encontradas). Os 2 de formulário já passam (guardas).

- [ ] **Step 3: Criar `templates/_abas_admin.html`**

```jinja
{# Sub-abas da administração (visual novo, Fase 2). A aba ativa vem do
   endpoint da requisição, como na topbar. #}
{% set endpoint_admin = request.endpoint or "" %}
<nav class="abas-secundarias" aria-label="Seções da administração">
    <a class="aba" href="{{ url_for('admin.admin_usuarios') }}" {% if endpoint_admin == 'admin.admin_usuarios' %}aria-current="page"{% endif %}>Usuários</a>
    <a class="aba" href="{{ url_for('admin.admin_logs') }}" {% if endpoint_admin == 'admin.admin_logs' %}aria-current="page"{% endif %}>Logs</a>
</nav>
```

- [ ] **Step 4: Reescrever `templates/admin_usuarios.html`** (arquivo inteiro). O rótulo continua "Painel Administrativo" (o CSS o mostra em caixa alta); `test_app.py` usa esse texto para saber se a página do admin abriu.

```jinja
{% extends "base_app.html" %}

{% block titulo %}Usuários · Administração · Help Desk{% endblock %}

{% block conteudo %}
{# O rótulo é exibido em caixa alta pelo CSS; o texto fica em "Painel
   Administrativo" porque é por ele que os testes de permissão reconhecem
   esta página. #}
<div class="pagina-cabecalho">
    <div>
        <p class="pagina-rotulo">Painel Administrativo</p>
        <h1 class="pagina-titulo">Administração</h1>
    </div>
</div>

{% include "_abas_admin.html" %}

<section class="cartao cartao-bloco" aria-label="Usuários cadastrados">
    <div class="tabela-rolavel">
        <table class="tabela-chamados">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Nome</th>
                    <th>E-mail</th>
                    <th>Perfil</th>
                    <th>Ações</th>
                </tr>
            </thead>
            <tbody>
                {% for usuario in usuarios %}
                <tr>
                    <td data-label="ID">{{ usuario.id }}</td>
                    <td data-label="Nome">{{ usuario.nome }}</td>
                    <td data-label="E-mail">{{ usuario.email }}</td>
                    <td data-label="Perfil">
                        <form method="POST" action="/admin/usuarios/{{ usuario.id }}/tipo" class="form-tipo-usuario">
                            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                            <select name="tipo_usuario" aria-label="Perfil de {{ usuario.nome }}">
                                <option value="Usuário" {% if usuario.tipo_usuario == "Usuário" %}selected{% endif %}>Usuário</option>
                                <option value="Técnico" {% if usuario.tipo_usuario == "Técnico" %}selected{% endif %}>Técnico</option>
                                <option value="Administrador" {% if usuario.tipo_usuario == "Administrador" %}selected{% endif %}>Administrador</option>
                            </select>
                            <button class="botao-filtro" type="submit">Salvar</button>
                        </form>
                    </td>
                    <td data-label="Ações">
                        {% if usuario.id != usuario_logado.id %}
                        {# O nome vai num data-attribute e é lido pelo JS.
                           Interpolar direto dentro do onsubmit permitia que um
                           nome com aspas escapasse da string e virasse código. #}
                        <form method="POST"
                              action="/admin/usuarios/{{ usuario.id }}/excluir"
                              class="form-excluir"
                              data-nome="{{ usuario.nome }}">
                            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                            <button class="botao-perigo" type="submit">Excluir</button>
                        </form>
                        {% else %}
                        <span class="finalizado">Você</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</section>

<script nonce="{{ csp_nonce() }}">
document.querySelectorAll(".form-excluir").forEach(function (form) {
    form.addEventListener("submit", function (evento) {
        var nome = form.dataset.nome;
        if (!confirm("Tem certeza que deseja excluir " + nome + "?")) {
            evento.preventDefault();
        }
    });
});
</script>
{% endblock %}
```

- [ ] **Step 5: Reescrever `templates/admin_logs.html`** (arquivo inteiro):

```jinja
{% extends "base_app.html" %}

{% block titulo %}Logs · Administração · Help Desk{% endblock %}

{% block conteudo %}
<div class="pagina-cabecalho">
    <div>
        <p class="pagina-rotulo">Painel Administrativo</p>
        <h1 class="pagina-titulo">Administração</h1>
    </div>
</div>

{% include "_abas_admin.html" %}

<section class="cartao cartao-bloco" aria-label="Logs de auditoria">
    {% if logs %}
    <div class="tabela-rolavel">
        <table class="tabela-chamados">
            <thead>
                <tr>
                    <th>Data/Hora</th>
                    <th>Usuário</th>
                    <th>Ação</th>
                    <th>Detalhes</th>
                </tr>
            </thead>
            <tbody>
                {% for log in logs %}
                <tr>
                    <td data-label="Data/Hora">{{ log.criado_em|data_local("%d/%m/%Y %H:%M") }}</td>
                    <td data-label="Usuário">{{ log.usuario_nome }}</td>
                    <td data-label="Ação">{{ log.acao }}</td>
                    <td data-label="Detalhes">{{ log.detalhes or "—" }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}

    {% if paginacao.total > 0 %}
    <div class="lista-rodape">
        <p class="vazio">Mostrando {{ logs|length }} de {{ paginacao.total }} registro(s) — página {{ paginacao.page }} de {{ paginacao.pages }}</p>
        {% if paginacao.pages > 1 %}
        <nav class="paginacao" aria-label="Páginas">
            {% if paginacao.has_prev %}
            <a class="pagina-link" href="{{ url_for('admin.admin_logs', pagina=paginacao.prev_num) }}">← Anterior</a>
            {% endif %}
            {% for numero in paginacao.iter_pages(left_edge=1, right_edge=1, left_current=2, right_current=2) %}
                {% if numero %}
                    {% if numero == paginacao.page %}
                    <span class="pagina-atual" aria-current="page">{{ numero }}</span>
                    {% else %}
                    <a class="pagina-link" href="{{ url_for('admin.admin_logs', pagina=numero) }}">{{ numero }}</a>
                    {% endif %}
                {% else %}
                <span class="pagina-reticencias">…</span>
                {% endif %}
            {% endfor %}
            {% if paginacao.has_next %}
            <a class="pagina-link" href="{{ url_for('admin.admin_logs', pagina=paginacao.next_num) }}">Próxima →</a>
            {% endif %}
        </nav>
        {% endif %}
    </div>
    {% else %}
    <p class="estado-vazio">Nenhum registro de auditoria encontrado.</p>
    {% endif %}
</section>
{% endblock %}
```

- [ ] **Step 6: Anexar o CSS** — salvar como `$HOME/fase2-scripts/css_t4.css` e rodar `python3 $HOME/fase2-scripts/anexar_css.py $HOME/fase2-scripts/css_t4.css`:

```css
/* SUB-ABAS DA ADMINISTRAÇÃO — mesmo desenho das abas da topbar, abaixo do
   título da página. */
.abas-secundarias {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 20px;
}

.abas-secundarias .aba {
    padding: 7px 14px;
    border-radius: var(--raio-pilula);
    color: var(--texto-muted);
    font-size: 14px;
    font-weight: 600;
    text-decoration: none;
    white-space: nowrap;
    transition: background-color 0.15s ease, color 0.15s ease;
}

.abas-secundarias .aba:hover {
    color: var(--texto);
    background: var(--superficie-alt);
}

.abas-secundarias .aba[aria-current="page"] {
    color: var(--texto);
    background: var(--acento-suave);
    box-shadow: inset 0 0 0 1px rgba(var(--acento-rgb), 0.35);
}

.abas-secundarias .aba:focus-visible {
    outline: 2px solid var(--acento);
    outline-offset: 2px;
}

.cartao .form-tipo-usuario {
    justify-content: flex-start;
}

@media (max-width: 900px) {
    .cartao .form-tipo-usuario {
        justify-content: flex-end;
    }
}

@media (prefers-reduced-motion: reduce) {
    .abas-secundarias .aba {
        transition: none;
    }
}
```

- [ ] **Step 7: Rodar e ver passar**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider tests/test_admin_paginas.py tests/test_app.py tests/test_rotas.py -q`
Expected: tudo passa — inclusive `test_admin_acessa_painel_admin`, o teste de `data-nome` com aspas (sem `onsubmit=`) e a paginação dos logs em `test_rotas.py`.

- [ ] **Step 8: Suíte inteira** — Expected: `291 passed`.

- [ ] **Step 9: Arquivos do commit:** `templates/_abas_admin.html`, `templates/admin_usuarios.html`, `templates/admin_logs.html`, `static/css/style.css`, `tests/test_admin_paginas.py`. Mensagem sugerida: `feat(ui): administração no layout novo com sub-abas`.

---

### Task 5: Token de API e alterar senha

**Files:**
- Rewrite: `templates/meu_token.html`, `templates/alterar_senha.html`
- Modify: `static/css/style.css` (anexar ao fim)
- Test: `tests/test_conta_paginas.py`

**Interfaces:**
- Consumes: `.pagina-rotulo`, `.pagina-titulo` (Fase 1); `.token-gerado`, `.botao-copiar`, `.formulario`, `.campo`, `.botao`, `.erro`, `.sucesso`, `.vazio` (CSS antigo).
- Variáveis de template (sem mudança): `token_gerado`, `tem_token` (meu_token); `form` (`senha_atual`, `nova_senha`, `confirmacao`) e `erro` (alterar_senha).
- Produces (CSS): `.cartao-estreito` (máx. 560px, centralizado), `.cartao-subtitulo`.

- [ ] **Step 1: Escrever o teste** — criar `tests/test_conta_paginas.py`:

```python
"""Token de API e troca de senha no layout novo (visual novo, Fase 2)."""

import re

SENHA = "senha-de-teste"


def _entrar(client, criar_usuario):
    criar_usuario(nome="Fulano", email="fulano@teste.com")
    client.post("/login", data={"email": "fulano@teste.com", "senha": SENHA})


def _layout_novo(html, titulo):
    assert 'class="topbar"' in html
    assert 'class="usuario-logado"' not in html
    assert 'style="' not in html
    assert "Voltar" not in html
    assert 'class="cartao cartao-estreito"' in html
    assert re.search(rf'<h1 class="pagina-titulo"[^>]*>{titulo}</h1>', html)


def test_meu_token_usa_o_layout_novo(client, criar_usuario):
    _entrar(client, criar_usuario)

    html = client.get("/meu-token").get_data(as_text=True)

    _layout_novo(html, "Meu token de API")
    assert "🔗" not in html
    assert "Você ainda não gerou nenhum token." in html
    assert ">Gerar token</button>" in html


def test_gerar_token_mostra_valor_e_scripts_com_nonce(client, criar_usuario):
    _entrar(client, criar_usuario)

    html = client.post("/meu-token").get_data(as_text=True)

    _layout_novo(html, "Meu token de API")
    assert 'id="botao-copiar-token"' in html
    assert 'id="botao-baixar-token"' in html
    assert re.search(r'<script nonce="[^"]+">\s*\(function \(\) \{\s*var botao = document\.getElementById\("botao-copiar-token"\)', html)


def test_quem_ja_tem_token_ve_gerar_novo(client, criar_usuario):
    _entrar(client, criar_usuario)
    client.post("/meu-token")

    html = client.get("/meu-token").get_data(as_text=True)

    assert "Você já tem um token gerado." in html
    assert ">Gerar novo token</button>" in html


def test_alterar_senha_usa_o_layout_novo(client, criar_usuario):
    _entrar(client, criar_usuario)

    html = client.get("/senha").get_data(as_text=True)

    _layout_novo(html, "Alterar senha")
    assert "🔑" not in html
    for nome in ("senha_atual", "nova_senha", "confirmacao"):
        assert f'name="{nome}"' in html


def test_alterar_senha_mostra_o_erro_no_cartao(client, criar_usuario):
    _entrar(client, criar_usuario)

    html = client.post(
        "/senha",
        data={"senha_atual": "errada-123", "nova_senha": "OutraSenha#2026", "confirmacao": "OutraSenha#2026"},
    ).get_data(as_text=True)

    assert '<p class="erro">Senha atual incorreta.</p>' in html
    _layout_novo(html, "Alterar senha")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider tests/test_conta_paginas.py -q`
Expected: 5 FAIL (sem topbar, sem `cartao-estreito`).

- [ ] **Step 3: Reescrever `templates/meu_token.html`** (arquivo inteiro; os dois scripts são os mesmos de hoje, com `nonce`):

```jinja
{% extends "base_app.html" %}

{% block titulo %}Meu token de API · Help Desk{% endblock %}

{% block conteudo %}
<section class="cartao cartao-estreito" aria-labelledby="titulo-token">
    <p class="pagina-rotulo">Sua conta</p>
    <h1 class="pagina-titulo" id="titulo-token">Meu token de API</h1>
    <p class="cartao-subtitulo">Usado por scripts e aplicativos externos para ler seus chamados sem passar pelo navegador</p>

    {% if token_gerado %}
    <p class="sucesso">Token gerado. Copie agora — ele só aparece esta vez, e gerar um novo substitui este.</p>

    <p class="token-gerado">
        <code>{{ token_gerado }}</code>
        <button type="button" class="botao-copiar" id="botao-copiar-token" data-token="{{ token_gerado }}">Copiar</button>
        <button type="button" class="botao-copiar" id="botao-baixar-token" data-token="{{ token_gerado }}">Baixar .txt</button>
    </p>

    <p class="vazio">Envie-o no cabeçalho <code>Authorization: Bearer {{ token_gerado }}</code> das requisições à API.</p>
    {% else %}
    {% if tem_token %}
    <p class="vazio">Você já tem um token gerado. O valor não pode ser mostrado de novo — gere um novo se precisar dele outra vez, o que invalida o atual.</p>
    {% else %}
    <p class="vazio">Você ainda não gerou nenhum token.</p>
    {% endif %}

    <form method="POST" class="formulario">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <button class="botao" type="submit">{{ "Gerar novo token" if tem_token else "Gerar token" }}</button>
    </form>
    {% endif %}
</section>

<script nonce="{{ csp_nonce() }}">
(function () {
    var botao = document.getElementById("botao-copiar-token");
    if (!botao) {
        return;
    }
    var textoOriginal = botao.textContent;
    botao.addEventListener("click", function () {
        var token = botao.getAttribute("data-token");
        function avisar() {
            botao.textContent = "Copiado!";
            botao.classList.add("copiado");
            setTimeout(function () {
                botao.textContent = textoOriginal;
                botao.classList.remove("copiado");
            }, 2000);
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(token).then(avisar, function () {
                window.prompt("Copie o token:", token);
            });
        } else {
            window.prompt("Copie o token:", token);
        }
    });
})();

(function () {
    // Baixa o token como .txt local — mesma ideia do botao de copiar: o
    // token so existe nesta resposta, entao quem preferir guardar um
    // arquivo em vez de colar em algum lugar tambem tem essa opcao.
    var botao = document.getElementById("botao-baixar-token");
    if (!botao) {
        return;
    }
    botao.addEventListener("click", function () {
        var token = botao.getAttribute("data-token");
        var blob = new Blob([token], { type: "text/plain" });
        var url = URL.createObjectURL(blob);
        var link = document.createElement("a");
        link.href = url;
        link.download = "token-api-helpdesk.txt";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    });
})();
</script>
{% endblock %}
```

- [ ] **Step 4: Reescrever `templates/alterar_senha.html`** (arquivo inteiro):

```jinja
{% extends "base_app.html" %}

{% block titulo %}Alterar senha · Help Desk{% endblock %}

{% block conteudo %}
<section class="cartao cartao-estreito" aria-labelledby="titulo-senha">
    <p class="pagina-rotulo">Sua conta</p>
    <h1 class="pagina-titulo" id="titulo-senha">Alterar senha</h1>
    <p class="cartao-subtitulo">Trocar a senha encerra as sessões abertas em outros dispositivos</p>

    {% if erro %}
    <p class="erro">{{ erro }}</p>
    {% endif %}

    <form method="POST" class="formulario" autocomplete="off">
        {{ form.hidden_tag() }}

        <div class="campo">
            {{ form.senha_atual.label }}
            {{ form.senha_atual(autocomplete="current-password", required=True) }}
        </div>

        <div class="campo">
            {{ form.nova_senha.label }}
            {{ form.nova_senha(placeholder="Mínimo de 8 caracteres", minlength="8", maxlength="128", autocomplete="new-password", required=True) }}
        </div>

        <div class="campo">
            {{ form.confirmacao.label(text="Repita a nova senha") }}
            {{ form.confirmacao(minlength="8", maxlength="128", autocomplete="new-password", required=True) }}
        </div>

        <p class="vazio">A senha precisa ter no mínimo 8 caracteres, misturar letras com números ou símbolos, e não pode conter seu nome nem seu e-mail.</p>

        <button class="botao" type="submit">Alterar senha</button>
    </form>
</section>
{% endblock %}
```

- [ ] **Step 5: Anexar o CSS** — salvar como `$HOME/fase2-scripts/css_t5.css` e rodar `python3 $HOME/fase2-scripts/anexar_css.py $HOME/fase2-scripts/css_t5.css`:

```css
/* PÁGINAS DA CONTA (token de API, alterar senha) — um cartão só, estreito e
   centralizado. */
.cartao-estreito {
    width: 100%;
    max-width: 560px;
    margin: 0 auto;
    padding: 28px;
}

.cartao-estreito .pagina-titulo {
    margin-bottom: 6px;
}

.cartao-subtitulo {
    margin-bottom: 24px;
    color: var(--texto-muted);
}

.cartao-estreito .token-gerado {
    justify-content: flex-start;
}

.cartao-estreito .botao {
    align-self: flex-start;
}

@media (max-width: 480px) {
    .cartao-estreito {
        padding: 20px;
    }

    .cartao-estreito .botao {
        align-self: stretch;
    }
}
```

- [ ] **Step 6: Rodar e ver passar**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider tests/test_conta_paginas.py tests/test_app.py -q`
Expected: tudo passa (os testes de troca de senha de `test_app.py` seguem verdes).

- [ ] **Step 7: Suíte inteira** — Expected: `296 passed`.

- [ ] **Step 8: Arquivos do commit:** `templates/meu_token.html`, `templates/alterar_senha.html`, `static/css/style.css`, `tests/test_conta_paginas.py`. Mensagem sugerida: `feat(ui): token de API e troca de senha no layout novo`.

---

### Task 6: Contagem de testes e verificação final

**Files:**
- Modify: `README.md`, `docs/index.html`, `templates/apresentacao.html`, `templates/recursos.html`

- [ ] **Step 1: Confirmar o número** — rodar a suíte inteira. Expected: `296 passed`. Se der outro número, usar o número real nos passos seguintes.

- [ ] **Step 2: Atualizar a contagem** — salvar como `$HOME/fase2-scripts/t6_contagem.py` e rodar `cd $HOME/mnt/helpdesk-system && python3 $HOME/fase2-scripts/t6_contagem.py 249 296`:

```python
"""Atualiza a contagem de testes (e a lista de arquivos de teste do README).
Uso: python t6_contagem.py 249 296"""
import sys
from pathlib import Path

antigo, novo = sys.argv[1], sys.argv[2]

TROCAS = {
    "README.md": [
        (f"Suíte com {antigo} testes em pytest, dividida em onze arquivos:",
         f"Suíte com {novo} testes em pytest, dividida em dezesseis arquivos:"),
        ("`test_topbar.py` (barra superior por perfil) e `test_dashboard.py` (KPIs, gráficos e período).",
         "`test_topbar.py` (barra superior por perfil), `test_dashboard.py` (KPIs, gráficos e período), "
         "`test_badges.py` (badges de status e prioridade), `test_listas_chamados.py` (lista geral e meus chamados), "
         "`test_detalhe_chamado.py` (detalhe e trilha de estado), `test_admin_paginas.py` (páginas da administração) "
         "e `test_conta_paginas.py` (token de API e troca de senha)."),
        (f"Esperado: **{antigo} passed**.", f"Esperado: **{novo} passed**."),
    ],
    "docs/index.html": [
        (f"API REST e {antigo} testes automatizados.", f"API REST e {novo} testes automatizados."),
        (f'<span class="n">{antigo}</span><span class="l">testes automatizados</span>',
         f'<span class="n">{novo}</span><span class="l">testes automatizados</span>'),
        (f'<span class="numero-inline">{antigo}</span> testes automatizados',
         f'<span class="numero-inline">{novo}</span> testes automatizados'),
    ],
    "templates/apresentacao.html": [
        (f'<span class="n">{antigo}</span><span class="l">testes automatizados</span>',
         f'<span class="n">{novo}</span><span class="l">testes automatizados</span>'),
    ],
    "templates/recursos.html": [
        (f'<span class="numero-inline">{antigo}</span> testes automatizados',
         f'<span class="numero-inline">{novo}</span> testes automatizados'),
    ],
}

for arquivo, trocas in TROCAS.items():
    caminho = Path(arquivo)
    bruto = caminho.read_bytes()
    for velho, novo_texto in trocas:
        velho_b, novo_b = velho.encode("utf-8"), novo_texto.encode("utf-8")
        assert bruto.count(velho_b) == 1, f"{arquivo}: esperado 1 ocorrência de {velho!r}, achei {bruto.count(velho_b)}"
        bruto = bruto.replace(velho_b, novo_b)
    caminho.write_bytes(bruto)
    print(f"{arquivo}: {len(trocas)} troca(s)")
```

Expected: `README.md: 3 troca(s)`, `docs/index.html: 3 troca(s)`, `templates/apresentacao.html: 1 troca(s)`, `templates/recursos.html: 1 troca(s)`. Depois, `grep -rn "249" README.md docs/index.html templates/apresentacao.html templates/recursos.html` não deve achar nada.

- [ ] **Step 3: Conferir o que não pode ter mudado**

Run: `git --no-optional-locks diff --stat -- rotas/ models.py formularios.py app.py`
Expected: saída vazia.

Run: `grep -ln "usuario-logado" templates/chamados.html templates/detalhe_chamado.html templates/meus_chamados.html templates/admin_usuarios.html templates/admin_logs.html templates/meu_token.html templates/alterar_senha.html`
Expected: nenhum arquivo.

Run: `grep -c $'\r$' static/css/style.css` e `wc -l < static/css/style.css`
Expected: os dois números iguais (CRLF em todas as linhas).

- [ ] **Step 4: Capturas de tela** — gerar as páginas com dados de exemplo pelo cliente de teste (banco em memória) com o script abaixo, salvo como `$HOME/fase2-scripts/capturas.py` e rodado da raiz do repo: `$HOME/venv-helpdesk/bin/python $HOME/fase2-scripts/capturas.py $HOME/capturas-fase2`. Ele grava HTML estático + `style.css` numa pasta fora do repo; capturar as 7 páginas (mais o dashboard) nos temas escuro e claro (atributo `data-theme` no `<html>`) e em 1280px e 400px de largura. Conferir: sem rolagem horizontal da página em 400px, badges com bolinha, trilha de etapas legível nos dois temas.

```python
"""Gera as 7 páginas com dados de exemplo pelo cliente de teste (banco em
memória) e grava HTML estático com o CSS ao lado, para capturar tela."""
import re, shutil, sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, ".")
from tests.conftest import CONFIG_DE_TESTE
from app import create_app
from extensions import db
from models import Chamado, Comentario, Usuario
from werkzeug.security import generate_password_hash

saida = Path(sys.argv[1]); saida.mkdir(parents=True, exist_ok=True)
app = create_app(CONFIG_DE_TESTE)
with app.app_context():
    db.create_all()
    admin = Usuario(nome="Ana Ribeiro", email="ana@exemplo.com", senha=generate_password_hash("senha-de-teste"), tipo_usuario="Administrador")
    tec = Usuario(nome="Bruno Lima", email="bruno@exemplo.com", senha=generate_password_hash("x"), tipo_usuario="Técnico")
    db.session.add_all([admin, tec]); db.session.commit()
    dados = [
        ("Impressora do financeiro não imprime", "A impressora aceita o trabalho mas nada sai; já reiniciei duas vezes e o painel não mostra erro.", "Aberto", "Alta", "Financeiro", None),
        ("VPN caindo a cada 10 minutos", "Conexão cai e volta sozinha, principalmente em chamadas de vídeo.", "Em andamento", "Crítica", "Comercial", admin),
        ("Instalar Office no notebook novo", "Notebook da recepção chegou sem pacote Office.", "Resolvido", "Baixa", "Recepção", tec),
        ("Monitor piscando", "Monitor secundário pisca ao abrir planilhas grandes.", "Aberto", "Média", "TI", None),
    ]
    agora = datetime.utcnow()
    for i, (t, d, s, p, st, resp) in enumerate(dados):
        c = Chamado(usuario="Maria Souza", setor=st, titulo=t, descricao=d, status=s, prioridade=p,
                    criado_em=agora - timedelta(days=3 - i), responsavel_id=resp.id if resp else None,
                    resolvido_em=agora - timedelta(hours=5) if s == "Resolvido" else None)
        db.session.add(c)
    db.session.commit()
    db.session.add(Comentario(chamado_id=2, autor_id=admin.id, mensagem="Troquei o perfil da VPN para o servidor de São Paulo."))
    db.session.add(Comentario(chamado_id=2, autor_id=tec.id, mensagem="Aguardando retorno do usuário para confirmar."))
    db.session.commit()
    cliente = app.test_client()
    cliente.post("/login", data={"email": "ana@exemplo.com", "senha": "senha-de-teste"})
    paginas = {"chamados": "/chamados", "detalhe": "/chamados/2", "meus": "/meus-chamados",
               "usuarios": "/admin/usuarios", "logs": "/admin/logs", "token": "/meu-token", "senha": "/senha",
               "dashboard": "/dashboard"}
    for nome, url in paginas.items():
        html = cliente.get(url).get_data(as_text=True)
        html = re.sub(r'<script[^>]*src="[^"]*tema\.js"[^>]*></script>', "", html)
        html = html.replace("/static/css/style.css", "style.css")
        (saida / f"{nome}.html").write_text(html, encoding="utf-8")
    shutil.copy("static/css/style.css", saida / "style.css")
print("ok")
```

- [ ] **Step 5: Fora do repo (o Edu atualiza):** landing comercial, README do repositório de perfil (`DZ092/DZ092`) e "Sobre" do LinkedIn — trocar 249 por 296.

- [ ] **Step 6: Arquivos do commit:** `README.md`, `docs/index.html`, `templates/apresentacao.html`, `templates/recursos.html`. Mensagem sugerida: `docs: contagem de testes da fase 2 (296)`.

## Entrega

Branch `feat/visual-novo-paginas-internas`, uma issue para a Fase 2 e PR com `Closes #N` — criados e mesclados pelo Edu, no fluxo de sempre.
