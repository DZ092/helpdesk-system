# Visual novo — Fase 1 (fundação + dashboard) Implementation Plan

**Goal:** Trocar a paleta monocromática por acento azul com temas escuro/claro, criar `base.html` + topbar com abas e reconstruir o dashboard com 4 KPIs e 4 gráficos SVG alimentados por métricas reais (incluindo a coluna nova `resolvido_em`).

**Architecture:** Flask + Jinja com herança de templates (`base.html` → `base_app.html` → `dashboard.html`). Agregações em `metricas.py` (consultas SQLAlchemy + agrupamento em Python), geometria dos gráficos em `graficos.py` (Python puro), SVG impresso por macros em `templates/_graficos.html`. Cor sempre por token CSS em `static/css/style.css`; nenhum `style="…"` inline (CSP).

**Tech Stack:** Python 3.10+ (produção Windows usa 3.14), Flask 3.1, Flask-SQLAlchemy 3.1, Flask-Migrate/Alembic, Jinja2, pytest. Sem dependência nova.

**Spec:** `docs/superpowers/specs/2026-09-25-visual-novo-fase1-design.md`

## Global Constraints

- **Git só leitura, e sempre com `--no-optional-locks`.** Na VM, `git status`/`git diff` sem essa flag criam `.git/index.lock` e a VM não consegue apagar — o repo do Edu fica travado. Use `git --no-optional-locks status --short` e `git --no-optional-locks diff ...`.
- **Git é do Edu.** Quem executa este plano **só edita arquivos**; nunca roda `git add`, `git commit`, `git push`, `git switch` nem cria branch. Os passos "Arquivos do commit" só listam o que o Edu vai commitar.
- **Nenhuma marca de geração automatizada** em código, comentário, mensagem de commit sugerida ou PR (sem assinatura de coautoria automática, sem notas de sessão).
- **Onde editar:** a pasta do projeto é montada na VM do `device_bash` em `$HOME/mnt/helpdesk-system` (no Windows: `C:\dev\helpdesk-system`). Todo arquivo é lido e escrito ali.
- **Fim de linha:** `static/css/style.css`, `rotas/api.py`, `tests/test_api.py`, `constantes.py` e `docs/index.html` usam **CRLF**; os demais arquivos existentes usam LF. Editar sempre com leitura e escrita que preservam o terminador (scripts Python dos passos abaixo), nunca reescrevendo o arquivo inteiro à mão. Arquivos novos: LF.
- **Rodar testes (VM):** `cd $HOME/mnt/helpdesk-system && $HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider <alvo> -v`. Se `$HOME/venv-helpdesk` não existir: `python3 -m venv $HOME/venv-helpdesk && $HOME/venv-helpdesk/bin/pip install -q -r $HOME/mnt/helpdesk-system/requirements.txt pytest`. Baseline antes da Fase 1: **170 passed**.
- **CSP:** `style-src 'self' https://fonts.googleapis.com` → nada de atributo `style="…"` nem `<style>` inline. Todo `<script>` inline leva `nonce="{{ csp_nonce() }}"`.
- **Cores só por token.** Nenhuma cor literal fora dos blocos `:root` e `[data-theme="light"]` de `style.css`.
- **Contraste mínimo:** 4.5:1 para texto normal (inclui texto de botão).
- **Datas no banco:** UTC naive (`obter_data_utc()` em `models.py`); exibição no fuso `FUSO_EXIBICAO` de `constantes.py`.
- **Sem emoji** em elementos novos (ícones são SVG inline).
- **Temas:** só `"dark"` e `"light"`. O tema âmbar deixa de existir.
- **Assinatura do rodapé:** `Eduardo Jr. Coelho` (nome completo), link `https://github.com/DZ092`.
- Nenhum logo, nome ou asset do case de referência do Behance.

## Review Focus

1. Quem já tinha salvo o tema **âmbar** no navegador abre o dashboard → deve cair no tema do sistema (escuro por padrão), nunca num tema sem estilo. Teste na Task 5.
2. Usuário com nome começando por **letra acentuada** ("Álvaro") → a inicial no menu da topbar deve ser "Á". Teste na Task 5.
3. Todos os chamados do período na **mesma prioridade** → o donut tem uma fatia só e deve fechar o círculo inteiro. Teste na Task 3.
4. Chamado **resolvido, reaberto e resolvido de novo** → `resolvido_em` deve ser a data da última resolução. Teste na Task 1.
5. Período **"tudo"** → o tempo médio inclui resoluções antigas (nenhum corte de data). Teste na Task 2.

## Mapa de arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `models.py` | modificar | coluna `resolvido_em` e método `Chamado.definir_status` |
| `migrations/versions/e7a1c4d9b2f0_adiciona_resolvido_em_ao_chamado.py` | criar | migração + backfill de `resolvido_em` |
| `rotas/chamados.py` | modificar | status pela tela usa `definir_status`; rota `/dashboard` nova |
| `rotas/api.py` | modificar (CRLF) | status pela API usa `definir_status` |
| `metricas.py` | criar | agregações do dashboard |
| `graficos.py` | criar | geometria dos gráficos |
| `static/css/style.css` | modificar (CRLF) | tokens, remoção do âmbar, topbar, dashboard, gráficos |
| `static/css/apresentacao.css` | modificar | botão usa `--acento-solido` |
| `static/js/tema.js` | modificar | só escuro/claro |
| `templates/*.html` (20) | modificar | remover botão `data-tema="ambar"` |
| `templates/base.html` | criar | `<head>` único, script anti-flash |
| `templates/base_app.html` | criar | topbar + `<main>` + rodapé |
| `templates/_topbar.html` | criar | barra superior com abas |
| `templates/_graficos.html` | criar | macros SVG + tabela acessível |
| `templates/dashboard.html` | reescrever | layout novo |
| `README.md` | modificar | temas e contagem de testes |
| `docs/index.html`, `templates/apresentacao.html`, `templates/recursos.html` | modificar | contagem de testes (Task 7) |
| `tests/test_resolvido_em.py`, `tests/test_metricas.py`, `tests/test_graficos.py`, `tests/test_tema.py`, `tests/test_topbar.py`, `tests/test_dashboard.py` | criar | testes novos |
| `tests/test_app.py` | modificar | 1 asserção presa ao título antigo do dashboard |

Ordem de dependência: Task 1 → Task 2 (usa `resolvido_em`) → Task 3 (independente) → Task 4 (independente) → Task 5 (usa tokens da Task 4) → Task 6 (usa Tasks 2, 3, 5) → Task 7.

---

### Task 1: Coluna `resolvido_em` e regra única de troca de status

**Files:**
- Modify: `models.py` (classe `Chamado`, depois de `codigo_acompanhamento_hash`)
- Create: `migrations/versions/e7a1c4d9b2f0_adiciona_resolvido_em_ao_chamado.py`
- Modify: `rotas/chamados.py` (função `atualizar_status_chamado`)
- Modify: `rotas/api.py` (função `atualizar_status_chamado_api`, CRLF)
- Test: `tests/test_resolvido_em.py` (novo)

**Interfaces:**
- Consumes: `obter_data_utc()` de `models.py`; fixtures `app`, `client`, `criar_usuario` de `tests/conftest.py`.
- Produces: `Chamado.resolvido_em: datetime | None` (UTC naive, indexada) e `Chamado.definir_status(novo_status: str) -> None`. A Task 2 lê `resolvido_em`.

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/test_resolvido_em.py`:

```python
"""Coluna resolvido_em e a regra única de troca de status (visual novo, Fase 1)."""

from datetime import datetime

from extensions import db
from models import Chamado

SENHA = "senha-de-teste"


def _chamado(status="Aberto"):
    chamado = Chamado(
        usuario="Maria",
        setor="Financeiro",
        titulo="Computador não liga",
        descricao="Tela preta ao ligar",
        status=status,
        prioridade="Alta",
    )
    db.session.add(chamado)
    db.session.commit()
    return chamado


def _entrar_como_tecnico(client, criar_usuario):
    criar_usuario(nome="Ana Técnica", email="tecnica@teste.com", tipo="Técnico")
    client.post("/login", data={"email": "tecnica@teste.com", "senha": SENHA})


def test_definir_status_grava_resolvido_em_ao_resolver(app):
    chamado = _chamado()

    chamado.definir_status("Resolvido")

    assert chamado.status == "Resolvido"
    assert isinstance(chamado.resolvido_em, datetime)
    assert chamado.resolvido_em.tzinfo is None  # UTC naive, padrão do banco


def test_definir_status_limpa_resolvido_em_ao_reabrir(app):
    chamado = _chamado()
    chamado.definir_status("Resolvido")

    chamado.definir_status("Em andamento")

    assert chamado.status == "Em andamento"
    assert chamado.resolvido_em is None


def test_definir_status_mesmo_status_nao_altera_data(app):
    chamado = _chamado()
    chamado.definir_status("Resolvido")
    primeira = chamado.resolvido_em

    chamado.definir_status("Resolvido")

    assert chamado.resolvido_em == primeira


def test_resolver_de_novo_depois_de_reabrir_grava_a_nova_data(app):
    chamado = _chamado()
    chamado.definir_status("Resolvido")
    chamado.resolvido_em = datetime(2020, 1, 1, 12, 0)  # resolução antiga
    chamado.definir_status("Aberto")

    chamado.definir_status("Resolvido")

    assert chamado.resolvido_em > datetime(2020, 1, 1, 12, 0)


def test_atualizar_status_pela_rota_grava_resolvido_em(client, criar_usuario):
    _entrar_como_tecnico(client, criar_usuario)
    chamado = _chamado()

    client.post(f"/chamados/{chamado.id}/status", data={"status": "Resolvido"})

    db.session.refresh(chamado)
    assert chamado.status == "Resolvido"
    assert chamado.resolvido_em is not None


def test_atualizar_status_pela_api_grava_resolvido_em(client, criar_usuario):
    _entrar_como_tecnico(client, criar_usuario)
    token = client.post("/meu-token").get_data(as_text=True).split("<code>")[1].split("</code>")[0]
    chamado = _chamado()

    resposta = client.post(
        f"/api/v1/chamados/{chamado.id}/status",
        json={"status": "Resolvido"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 200
    db.session.refresh(chamado)
    assert chamado.resolvido_em is not None


def test_migracao_preenche_resolvido_em_dos_chamados_ja_resolvidos(tmp_path):
    """Chamados resolvidos antes da coluna existir recebem atualizado_em."""
    from flask_migrate import upgrade
    from sqlalchemy import text

    from app import create_app

    banco = tmp_path / "backfill.db"
    aplicacao = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{banco}",
            "SECRET_KEY": "chave-de-teste",
        }
    )

    with aplicacao.app_context():
        upgrade(revision="d835773a6a22")  # esquema antes de resolvido_em
        with db.engine.begin() as conexao:
            conexao.execute(
                text(
                    "INSERT INTO chamado (usuario, setor, titulo, descricao, status, prioridade, criado_em, atualizado_em) "
                    "VALUES ('Maria', 'TI', 'Resolvido antigo', 'd', 'Resolvido', 'Alta', "
                    "'2026-09-01 10:00:00', '2026-09-02 15:30:00')"
                )
            )
            conexao.execute(
                text(
                    "INSERT INTO chamado (usuario, setor, titulo, descricao, status, prioridade, criado_em, atualizado_em) "
                    "VALUES ('João', 'TI', 'Ainda aberto', 'd', 'Aberto', 'Baixa', "
                    "'2026-09-01 10:00:00', '2026-09-03 09:00:00')"
                )
            )

        upgrade()  # aplica a migração nova

        with db.engine.connect() as conexao:
            linhas = conexao.execute(text("SELECT titulo, resolvido_em FROM chamado ORDER BY id")).all()

    assert str(linhas[0][1]).startswith("2026-09-02 15:30:00")
    assert linhas[1][1] is None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider tests/test_resolvido_em.py -v`
Expected: FAIL — `AttributeError: 'Chamado' object has no attribute 'definir_status'` nos testes de modelo, e erro de revisão/coluna inexistente no teste de migração.

- [ ] **Step 3: Coluna e método no modelo**

Em `models.py`, logo depois da linha `    codigo_acompanhamento_hash = db.Column(db.String(64), unique=True, nullable=True, index=True)` (fim dos campos de `Chamado`), inserir:

```python

    # Momento em que o chamado passou a "Resolvido" (UTC naive, como as demais
    # datas). Volta a None se ele for reaberto. Só `definir_status` escreve
    # aqui — é dela que o tempo médio de resolução do dashboard depende.
    resolvido_em = db.Column(db.DateTime, nullable=True, index=True)

    def definir_status(self, novo_status):
        """Troca o status e mantém `resolvido_em` coerente com ele.

        Único caminho para mudar o status de um chamado existente (tela e API
        passam por aqui): decide quando o relógio de resolução para (passou a
        Resolvido) e quando ele zera (reaberto). Repetir o mesmo status não
        mexe na data.
        """
        if novo_status == self.status:
            return
        if novo_status == "Resolvido":
            self.resolvido_em = obter_data_utc()
        elif self.status == "Resolvido":
            self.resolvido_em = None
        self.status = novo_status
```

- [ ] **Step 4: Migração**

Criar `migrations/versions/e7a1c4d9b2f0_adiciona_resolvido_em_ao_chamado.py`:

```python
"""adiciona resolvido_em ao chamado

Revision ID: e7a1c4d9b2f0
Revises: d835773a6a22
Create Date: 2026-09-26 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7a1c4d9b2f0'
down_revision = 'd835773a6a22'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('chamado', schema=None) as batch_op:
        batch_op.add_column(sa.Column('resolvido_em', sa.DateTime(), nullable=True))
        batch_op.create_index(batch_op.f('ix_chamado_resolvido_em'), ['resolvido_em'], unique=False)

    # Backfill: chamados já resolvidos não têm registro de quando isso
    # aconteceu. atualizado_em é o melhor dado disponível — pode ter mudado
    # depois da resolução, mas é o limite superior mais próximo.
    op.execute("UPDATE chamado SET resolvido_em = atualizado_em WHERE status = 'Resolvido'")


def downgrade():
    with op.batch_alter_table('chamado', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_chamado_resolvido_em'))
        batch_op.drop_column('resolvido_em')
```

- [ ] **Step 5: Tela e API usam `definir_status`**

Rodar na VM (preserva CRLF de `rotas/api.py`):

```bash
cd $HOME/mnt/helpdesk-system && python3 - <<'PY'
import pathlib

def trocar(caminho, antigo, novo):
    arquivo = pathlib.Path(caminho)
    texto = arquivo.read_bytes().decode("utf-8")
    assert texto.count(antigo) == 1, (caminho, texto.count(antigo))
    arquivo.write_bytes(texto.replace(antigo, novo).encode("utf-8"))

trocar("rotas/chamados.py", "    chamado.status = form.status.data\n", "    chamado.definir_status(form.status.data)\n")
trocar("rotas/api.py", "    chamado.status = novo_status\r\n", "    chamado.definir_status(novo_status)\r\n")
PY
```

- [ ] **Step 6: Rodar os testes novos e a suíte de migração**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider tests/test_resolvido_em.py "tests/test_app.py::test_migracoes_reproduzem_o_esquema_dos_modelos" -v`
Expected: 8 passed.

- [ ] **Step 7: Suíte inteira**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider -q`
Expected: 177 passed.

- [ ] **Step 8: Arquivos do commit (o Edu commita)**

`models.py`, `migrations/versions/e7a1c4d9b2f0_adiciona_resolvido_em_ao_chamado.py`, `rotas/chamados.py`, `rotas/api.py`, `tests/test_resolvido_em.py` — mensagem sugerida: `feat(dados): registra resolvido_em ao resolver um chamado`

---

### Task 2: Agregações do dashboard (`metricas.py`)

**Files:**
- Create: `metricas.py`
- Test: `tests/test_metricas.py` (novo)

**Interfaces:**
- Consumes: `Chamado` (com `resolvido_em`, da Task 1), `db`, `FUSO_EXIBICAO`, `PRIORIDADES`, `STATUS_CHAMADO`.
- Produces (usado pela Task 6):
  - `PERIODOS: dict[str, int | None]` = `{"7": 7, "30": 30, "90": 90, "tudo": None}`; `PERIODO_PADRAO = "30"`
  - `chave_de_periodo_valida(chave: str | None) -> str`
  - `inicio_do_periodo(chave: str | None, agora: datetime) -> datetime | None`
  - `kpis(desde: datetime | None) -> dict` com chaves `total`, `abertos`, `em_andamento`, `em_aberto`, `resolvidos`, `pct_resolvidos` (int), `tempo_medio` (`timedelta | None`)
  - `tempo_medio_resolucao(desde: datetime | None) -> timedelta | None`
  - `por_setor(desde, limite=6) -> list[tuple[str, int]]`
  - `por_prioridade(desde) -> list[tuple[str, int]]`
  - `por_status(desde) -> list[tuple[str, int]]`
  - `evolucao_semanal(agora: datetime, semanas: int = 8) -> list[dict]` com chaves `inicio` (`date`, segunda-feira), `criados`, `resolvidos`
  - `formatar_duracao(duracao: timedelta | None) -> str`

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/test_metricas.py`:

```python
"""Agregações do dashboard (visual novo, Fase 1)."""

from datetime import date, datetime, timedelta

import pytest

import metricas
from extensions import db
from models import Chamado

# Quinta-feira, 24/09/2026, 15h UTC (12h em Brasília). A semana dela começa
# na segunda 21/09.
AGORA = datetime(2026, 9, 24, 15, 0)


def _chamado(criado_em, status="Aberto", prioridade="Média", setor="Financeiro", resolvido_em=None):
    chamado = Chamado(
        usuario="Maria",
        setor=setor,
        titulo="Computador não liga",
        descricao="Tela preta ao ligar",
        status=status,
        prioridade=prioridade,
        criado_em=criado_em,
        resolvido_em=resolvido_em,
    )
    db.session.add(chamado)
    db.session.commit()
    return chamado


# ------------------------------------------------------------------ período
def test_inicio_do_periodo_30_dias():
    assert metricas.inicio_do_periodo("30", AGORA) == AGORA - timedelta(days=30)


def test_inicio_do_periodo_tudo_nao_tem_limite():
    assert metricas.inicio_do_periodo("tudo", AGORA) is None


def test_inicio_do_periodo_chave_invalida_usa_o_padrao():
    assert metricas.chave_de_periodo_valida("abacaxi") == "30"
    assert metricas.chave_de_periodo_valida(None) == "30"
    assert metricas.inicio_do_periodo("abacaxi", AGORA) == AGORA - timedelta(days=30)


# ------------------------------------------------------------------ kpis
def test_kpis_com_banco_vazio(app):
    resultado = metricas.kpis(None)

    assert resultado["total"] == 0
    assert resultado["pct_resolvidos"] == 0
    assert resultado["tempo_medio"] is None


def test_kpis_contam_por_status(app):
    ontem = AGORA - timedelta(days=1)
    _chamado(ontem, status="Aberto")
    _chamado(ontem, status="Aberto")
    _chamado(ontem, status="Em andamento")
    _chamado(ontem, status="Resolvido", resolvido_em=ontem + timedelta(hours=2))

    resultado = metricas.kpis(None)

    assert resultado["total"] == 4
    assert resultado["abertos"] == 2
    assert resultado["em_andamento"] == 1
    assert resultado["em_aberto"] == 3
    assert resultado["resolvidos"] == 1
    assert resultado["pct_resolvidos"] == 25


def test_kpis_ignoram_chamados_criados_antes_do_periodo(app):
    _chamado(AGORA - timedelta(days=40))
    _chamado(AGORA - timedelta(days=5))

    resultado = metricas.kpis(AGORA - timedelta(days=30))

    assert resultado["total"] == 1


# ------------------------------------------------------------------ tempo médio
def test_tempo_medio_usa_resolvido_em(app):
    inicio = AGORA - timedelta(days=3)
    _chamado(inicio, status="Resolvido", resolvido_em=inicio + timedelta(hours=2))
    _chamado(inicio, status="Resolvido", resolvido_em=inicio + timedelta(hours=4))

    assert metricas.tempo_medio_resolucao(None) == timedelta(hours=3)


def test_tempo_medio_ignora_resolucoes_fora_do_periodo(app):
    antigo = AGORA - timedelta(days=60)
    _chamado(antigo, status="Resolvido", resolvido_em=antigo + timedelta(hours=10))
    recente = AGORA - timedelta(days=2)
    _chamado(recente, status="Resolvido", resolvido_em=recente + timedelta(hours=1))

    assert metricas.tempo_medio_resolucao(AGORA - timedelta(days=30)) == timedelta(hours=1)


def test_tempo_medio_no_periodo_tudo_inclui_resolucoes_antigas(app):
    antigo = AGORA - timedelta(days=400)
    _chamado(antigo, status="Resolvido", resolvido_em=antigo + timedelta(hours=10))
    recente = AGORA - timedelta(days=2)
    _chamado(recente, status="Resolvido", resolvido_em=recente + timedelta(hours=2))

    assert metricas.tempo_medio_resolucao(None) == timedelta(hours=6)


# ------------------------------------------------------------------ distribuições
def test_por_prioridade_inclui_zeros_na_ordem_oficial(app):
    _chamado(AGORA, prioridade="Alta")

    assert metricas.por_prioridade(None) == [("Baixa", 0), ("Média", 0), ("Alta", 1), ("Crítica", 0)]


def test_por_status_inclui_zeros_na_ordem_oficial(app):
    _chamado(AGORA, status="Resolvido", resolvido_em=AGORA)

    assert metricas.por_status(None) == [("Aberto", 0), ("Em andamento", 0), ("Resolvido", 1)]


def test_por_setor_ordena_do_maior_para_o_menor_e_respeita_o_limite(app):
    for setor, quantidade in [("TI", 3), ("RH", 2), ("Financeiro", 1), ("Comercial", 1),
                              ("Jurídico", 1), ("Compras", 1), ("Logística", 1)]:
        for _ in range(quantidade):
            _chamado(AGORA, setor=setor)

    resultado = metricas.por_setor(None)

    assert len(resultado) == 6
    assert resultado[0] == ("TI", 3)
    assert resultado[1] == ("RH", 2)


# ------------------------------------------------------------------ evolução
def test_evolucao_semanal_tem_8_semanas_terminando_na_atual(app):
    semanas = metricas.evolucao_semanal(AGORA)

    assert len(semanas) == 8
    assert semanas[-1]["inicio"] == date(2026, 9, 21)
    assert semanas[0]["inicio"] == date(2026, 8, 3)
    assert all(s["criados"] == 0 and s["resolvidos"] == 0 for s in semanas)


def test_evolucao_semanal_agrupa_no_fuso_de_brasilia(app):
    # 21/09 02h UTC = domingo 20/09 23h em Brasília → semana de 14/09.
    _chamado(datetime(2026, 9, 21, 2, 0))

    semanas = {s["inicio"]: s for s in metricas.evolucao_semanal(AGORA)}

    assert semanas[date(2026, 9, 14)]["criados"] == 1
    assert semanas[date(2026, 9, 21)]["criados"] == 0


def test_evolucao_semanal_conta_resolvidos_pela_data_de_resolucao(app):
    _chamado(datetime(2026, 9, 8, 15, 0), status="Resolvido", resolvido_em=datetime(2026, 9, 22, 15, 0))

    semanas = {s["inicio"]: s for s in metricas.evolucao_semanal(AGORA)}

    assert semanas[date(2026, 9, 7)]["criados"] == 1
    assert semanas[date(2026, 9, 21)]["resolvidos"] == 1
    assert semanas[date(2026, 9, 7)]["resolvidos"] == 0


# ------------------------------------------------------------------ formatação
@pytest.mark.parametrize(
    "duracao, esperado",
    [
        (None, "—"),
        (timedelta(0), "0min"),
        (timedelta(minutes=45), "45min"),
        (timedelta(hours=6, minutes=20), "6h20"),
        (timedelta(days=2, hours=4, minutes=30), "2d 4h"),
    ],
)
def test_formatar_duracao(duracao, esperado):
    assert metricas.formatar_duracao(duracao) == esperado
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider tests/test_metricas.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'metricas'`.

- [ ] **Step 3: Implementar `metricas.py`**

Criar `metricas.py` na raiz do projeto:

```python
"""Indicadores do dashboard (visual novo, Fase 1).

Funções que consultam o banco e devolvem estruturas simples — nada de HTML
aqui. Toda função que depende do "agora" recebe esse instante como parâmetro,
para os testes controlarem o tempo sem mock. As datas no banco são UTC naive
(ver `obter_data_utc` em models.py); o agrupamento por semana acontece no fuso
de exibição, em Python, para dar o mesmo resultado no SQLite dos testes e no
Postgres de produção.
"""

from datetime import timedelta, timezone

from constantes import FUSO_EXIBICAO, PRIORIDADES, STATUS_CHAMADO
from extensions import db
from models import Chamado

PERIODOS = {"7": 7, "30": 30, "90": 90, "tudo": None}
PERIODO_PADRAO = "30"


def chave_de_periodo_valida(chave):
    """A chave pedida, se existir em PERIODOS; senão o período padrão."""
    return chave if chave in PERIODOS else PERIODO_PADRAO


def inicio_do_periodo(chave, agora):
    """Instante (UTC naive) a partir do qual contar; None significa "tudo"."""
    dias = PERIODOS[chave_de_periodo_valida(chave)]
    if dias is None:
        return None
    return agora - timedelta(days=dias)


def _contagem_por(coluna, desde):
    """{valor da coluna: quantidade} dos chamados criados desde `desde`."""
    consulta = db.select(coluna, db.func.count(Chamado.id)).group_by(coluna)
    if desde is not None:
        consulta = consulta.where(Chamado.criado_em >= desde)
    return dict(db.session.execute(consulta).all())


def tempo_medio_resolucao(desde):
    """Média de (resolvido_em − criado_em) das resoluções feitas desde `desde`."""
    consulta = db.select(Chamado.criado_em, Chamado.resolvido_em).where(Chamado.resolvido_em.is_not(None))
    if desde is not None:
        consulta = consulta.where(Chamado.resolvido_em >= desde)
    duracoes = [resolvido - criado for criado, resolvido in db.session.execute(consulta).all()]
    if not duracoes:
        return None
    return sum(duracoes, timedelta()) / len(duracoes)


def kpis(desde):
    """Os quatro números do topo do dashboard.

    As contagens consideram chamados *criados* no período, com o status atual
    de cada um; o tempo médio considera resoluções *feitas* no período.
    """
    por_status_atual = _contagem_por(Chamado.status, desde)
    total = sum(por_status_atual.values())
    abertos = por_status_atual.get("Aberto", 0)
    em_andamento = por_status_atual.get("Em andamento", 0)
    resolvidos = por_status_atual.get("Resolvido", 0)
    return {
        "total": total,
        "abertos": abertos,
        "em_andamento": em_andamento,
        "em_aberto": abertos + em_andamento,
        "resolvidos": resolvidos,
        "pct_resolvidos": round(resolvidos * 100 / total) if total else 0,
        "tempo_medio": tempo_medio_resolucao(desde),
    }


def por_setor(desde, limite=6):
    """Setores com mais chamados no período, do maior para o menor."""
    contagem = _contagem_por(Chamado.setor, desde)
    ordenado = sorted(contagem.items(), key=lambda item: (-item[1], item[0]))
    return ordenado[:limite]


def por_prioridade(desde):
    """Quantidade por prioridade, na ordem de PRIORIDADES, com zeros."""
    contagem = _contagem_por(Chamado.prioridade, desde)
    return [(prioridade, contagem.get(prioridade, 0)) for prioridade in PRIORIDADES]


def por_status(desde):
    """Quantidade por status atual, na ordem de STATUS_CHAMADO, com zeros."""
    contagem = _contagem_por(Chamado.status, desde)
    return [(status, contagem.get(status, 0)) for status in STATUS_CHAMADO]


def _data_local(instante_utc):
    return instante_utc.replace(tzinfo=timezone.utc).astimezone(FUSO_EXIBICAO).date()


def _segunda_feira(dia):
    return dia - timedelta(days=dia.weekday())


def evolucao_semanal(agora, semanas=8):
    """Criados × resolvidos por semana (segunda a domingo, fuso de Brasília).

    Ignora o seletor de período de propósito: mostra sempre as últimas
    `semanas` semanas, terminando na semana de `agora`.
    """
    semana_atual = _segunda_feira(_data_local(agora))
    inicios = [semana_atual - timedelta(weeks=n) for n in range(semanas - 1, -1, -1)]
    criados = dict.fromkeys(inicios, 0)
    resolvidos = dict.fromkeys(inicios, 0)

    # Um dia de folga na consulta; o corte exato é feito abaixo, no fuso local.
    limite = agora - timedelta(weeks=semanas, days=1)

    for (criado_em,) in db.session.execute(db.select(Chamado.criado_em).where(Chamado.criado_em >= limite)).all():
        semana = _segunda_feira(_data_local(criado_em))
        if semana in criados:
            criados[semana] += 1

    for (resolvido_em,) in db.session.execute(
        db.select(Chamado.resolvido_em).where(Chamado.resolvido_em >= limite)
    ).all():
        semana = _segunda_feira(_data_local(resolvido_em))
        if semana in resolvidos:
            resolvidos[semana] += 1

    return [{"inicio": inicio, "criados": criados[inicio], "resolvidos": resolvidos[inicio]} for inicio in inicios]


def formatar_duracao(duracao):
    """"45min", "6h20", "2d 4h" — ou "—" quando não há dado."""
    if duracao is None:
        return "—"
    minutos = int(duracao.total_seconds() // 60)
    if minutos < 60:
        return f"{minutos}min"
    horas, minutos = divmod(minutos, 60)
    if horas < 24:
        return f"{horas}h{minutos:02d}"
    dias, horas = divmod(horas, 24)
    return f"{dias}d {horas}h"
```

- [ ] **Step 4: Rodar e ver passar**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider tests/test_metricas.py -v`
Expected: 20 passed.

- [ ] **Step 5: Suíte inteira**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider -q`
Expected: 197 passed.

- [ ] **Step 6: Arquivos do commit (o Edu commita)**

`metricas.py`, `tests/test_metricas.py` — mensagem sugerida: `feat(dashboard): agrega indicadores de chamados por período`

---

### Task 3: Geometria dos gráficos (`graficos.py`)

**Files:**
- Create: `graficos.py`
- Test: `tests/test_graficos.py` (novo)

**Interfaces:**
- Consumes: nada (Python puro; recebe listas `[(rotulo, valor), ...]` no formato devolvido por `metricas.por_*`).
- Produces (usado pela Task 6):
  - `barras(itens) -> list[dict]` — chaves `rotulo`, `valor`, `pct` (0–100, relativo ao maior)
  - `RAIO_DONUT = 40` (viewBox `0 0 100 100`, centro `50,50`)
  - `donut(itens, raio=RAIO_DONUT) -> list[dict]` — chaves `rotulo`, `valor`, `comprimento` (float), `dasharray` (str), `dashoffset` (str)
  - `linha(valores, largura=600, altura=200, margem=24, teto=None) -> dict` — chaves `pontos` (str para `points`), `marcas` (`list[tuple[float, float]]`), `grade` (`list[tuple[float, int]]` = (y, valor do rótulo))
  - `empilhada(itens) -> list[dict]` — chaves `rotulo`, `valor`, `x_pct`, `largura_pct`

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/test_graficos.py`:

```python
"""Geometria dos gráficos SVG do dashboard (visual novo, Fase 1)."""

import math

import graficos

CIRCUNFERENCIA = 2 * math.pi * graficos.RAIO_DONUT


def test_barras_maior_valor_ocupa_100_por_cento():
    resultado = graficos.barras([("TI", 10), ("RH", 5)])

    assert resultado[0]["pct"] == 100
    assert resultado[1]["pct"] == 50
    assert resultado[1]["rotulo"] == "RH" and resultado[1]["valor"] == 5


def test_barras_com_tudo_zero_nao_divide_por_zero():
    assert [b["pct"] for b in graficos.barras([("TI", 0), ("RH", 0)])] == [0, 0]


def test_barras_lista_vazia():
    assert graficos.barras([]) == []


def test_donut_fatias_somam_a_circunferencia():
    fatias = graficos.donut([("Baixa", 1), ("Média", 2), ("Alta", 3), ("Crítica", 4)])

    assert math.isclose(sum(f["comprimento"] for f in fatias), CIRCUNFERENCIA, rel_tol=1e-9)


def test_donut_cada_fatia_comeca_onde_a_anterior_termina():
    fatias = graficos.donut([("Baixa", 1), ("Média", 3)])

    assert fatias[0]["dashoffset"] == "-0.00"
    assert float(fatias[1]["dashoffset"]) == -round(fatias[0]["comprimento"], 2)


def test_donut_com_uma_categoria_so_fecha_o_circulo():
    fatias = graficos.donut([("Baixa", 0), ("Média", 0), ("Alta", 5), ("Crítica", 0)])

    alta = fatias[2]
    assert math.isclose(alta["comprimento"], CIRCUNFERENCIA)
    assert alta["dasharray"] == f"{CIRCUNFERENCIA:.2f} 0.00"


def test_donut_total_zero_nao_divide_por_zero():
    assert [f["comprimento"] for f in graficos.donut([("Baixa", 0), ("Alta", 0)])] == [0, 0]


def test_linha_distribui_pontos_na_largura_e_inverte_o_eixo_y():
    resultado = graficos.linha([0, 5, 10], largura=600, altura=200, margem=24)

    assert resultado["marcas"] == [(24.0, 176.0), (300.0, 100.0), (576.0, 24.0)]
    assert resultado["pontos"] == "24.0,176.0 300.0,100.0 576.0,24.0"


def test_linha_com_valores_zerados_nao_divide_por_zero():
    resultado = graficos.linha([0, 0, 0])

    assert all(y == 176.0 for _, y in resultado["marcas"])


def test_linha_com_teto_compartilhado_usa_a_mesma_escala():
    resultado = graficos.linha([5], teto=10)

    assert resultado["marcas"] == [(24.0, 100.0)]
    assert [valor for _, valor in resultado["grade"]] == [0, 5, 10]


def test_empilhada_soma_100_por_cento():
    partes = graficos.empilhada([("Aberto", 1), ("Em andamento", 1), ("Resolvido", 2)])

    assert [p["x_pct"] for p in partes] == [0, 25, 50]
    assert math.isclose(sum(p["largura_pct"] for p in partes), 100)


def test_empilhada_total_zero():
    assert [p["largura_pct"] for p in graficos.empilhada([("Aberto", 0)])] == [0]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider tests/test_graficos.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'graficos'`.

- [ ] **Step 3: Implementar `graficos.py`**

Criar `graficos.py` na raiz do projeto:

```python
"""Geometria dos gráficos SVG do dashboard (visual novo, Fase 1).

Só contas: nenhum acesso a banco e nenhum HTML. As macros de
templates/_graficos.html imprimem os valores prontos daqui como atributos SVG
(`width`, `points`, `stroke-dasharray`...) — nunca como `style="…"`, que o CSP
da aplicação (style-src sem 'unsafe-inline') bloquearia.
"""

import math

RAIO_DONUT = 40  # no viewBox 0 0 100 100, centro em 50,50


def barras(itens):
    """Barras horizontais: cada valor em % do maior valor da lista."""
    maior = max((valor for _, valor in itens), default=0)
    return [
        {"rotulo": rotulo, "valor": valor, "pct": round(valor * 100 / maior, 1) if maior else 0}
        for rotulo, valor in itens
    ]


def donut(itens, raio=RAIO_DONUT):
    """Fatias de um donut desenhado com stroke-dasharray num <circle>.

    Cada fatia é um traço de `comprimento` seguido de um vão do resto da
    circunferência; o dashoffset negativo empurra o traço para começar onde a
    fatia anterior terminou.
    """
    circunferencia = 2 * math.pi * raio
    total = sum(valor for _, valor in itens)
    fatias = []
    acumulado = 0.0
    for rotulo, valor in itens:
        comprimento = circunferencia * valor / total if total else 0
        fatias.append(
            {
                "rotulo": rotulo,
                "valor": valor,
                "comprimento": comprimento,
                "dasharray": f"{comprimento:.2f} {circunferencia - comprimento:.2f}",
                "dashoffset": f"{-acumulado:.2f}",
            }
        )
        acumulado += comprimento
    return fatias


def linha(valores, largura=600, altura=200, margem=24, teto=None):
    """Pontos de uma série num gráfico de linhas.

    `teto` é o valor que ocupa a altura útil inteira; passe o mesmo teto para
    duas séries dividirem a mesma escala. A grade traz 0, a metade (arredondada)
    e o teto, sem repetir valores.
    """
    teto = max(valores, default=0) if teto is None else teto
    teto = teto or 1
    largura_util = largura - 2 * margem
    altura_util = altura - 2 * margem
    passo = largura_util / (len(valores) - 1) if len(valores) > 1 else 0

    def y_de(valor):
        return round(altura - margem - (valor / teto) * altura_util, 1)

    marcas = [(round(margem + indice * passo, 1), y_de(valor)) for indice, valor in enumerate(valores)]
    niveis = sorted({0, round(teto / 2), teto})
    return {
        "pontos": " ".join(f"{x},{y}" for x, y in marcas),
        "marcas": marcas,
        "grade": [(y_de(nivel), nivel) for nivel in niveis],
    }


def empilhada(itens):
    """Barra única dividida em partes proporcionais (posição e largura em %)."""
    total = sum(valor for _, valor in itens)
    partes = []
    posicao = 0.0
    for rotulo, valor in itens:
        largura = valor * 100 / total if total else 0
        partes.append({"rotulo": rotulo, "valor": valor, "x_pct": round(posicao, 2), "largura_pct": round(largura, 2)})
        posicao += largura
    return partes
```

- [ ] **Step 4: Rodar e ver passar**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider tests/test_graficos.py -v`
Expected: 12 passed.

- [ ] **Step 5: Suíte inteira**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider -q`
Expected: 209 passed.

- [ ] **Step 6: Arquivos do commit (o Edu commita)**

`graficos.py`, `tests/test_graficos.py` — mensagem sugerida: `feat(dashboard): calcula a geometria dos gráficos SVG`

---

### Task 4: Tokens novos, acento azul e remoção do tema âmbar

**Files:**
- Modify: `static/css/style.css` (CRLF — comentário do topo, bloco `:root`, bloco do tema claro, bloco do âmbar, 5 regras `background: var(--acento);`)
- Modify: `static/css/apresentacao.css` (1 regra `background: var(--acento);`)
- Modify: `static/css/auth.css` (comentário que cita o âmbar)
- Modify: `static/js/tema.js` (comentário do topo, `TEMAS`, `ICONE_POR_TEMA`, `NOME_POR_TEMA`)
- Modify: os 20 `templates/*.html` (remover `<button type="button" data-tema="ambar"></button>`)
- Modify: `README.md` (item "Três temas de interface")
- Test: `tests/test_tema.py` (novo)

**Interfaces:**
- Consumes: nada.
- Produces (usado pelas Tasks 5 e 6): tokens `--bg`, `--superficie`, `--superficie-alt`, `--borda`, `--borda-forte`, `--texto`, `--texto-muted`, `--texto-fraco`, `--acento`, `--acento-rgb`, `--acento-solido`, `--acento-solido-hover`, `--acento-suave`, `--texto-botao`, `--sombra-1`, `--sombra-2`, `--raio-controle`, `--raio-superficie`, `--raio-pilula`, `--grafico-grade`, além das semânticas já existentes (`--sucesso-*`, `--erro-*`, `--aviso-*`, `--info-*`, `--prioridade-*`). `TEMAS = ["dark", "light"]` em `tema.js`.

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/test_tema.py`:

```python
"""Paleta e temas do visual novo (Fase 1): contraste medido nos próprios tokens.

Os pares abaixo são texto × fundo que aparecem de verdade na interface. O
mínimo é 4.5:1 (texto normal, WCAG AA) — inclusive texto de botão.
"""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
CSS = (RAIZ / "static" / "css" / "style.css").read_text(encoding="utf-8")


def _bloco(seletor):
    inicio = CSS.index(seletor + " {")
    return CSS[inicio : CSS.index("}", inicio)]


def _tokens(seletor):
    return dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9A-Fa-f]{6})\s*;", _bloco(seletor)))


def _luminancia(hexa):
    canais = [int(hexa[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lineares = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canais]
    return 0.2126 * lineares[0] + 0.7152 * lineares[1] + 0.0722 * lineares[2]


def contraste(a, b):
    claro, escuro = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (claro + 0.05) / (escuro + 0.05)


ESCURO = _tokens(":root")
CLARO = {**ESCURO, **_tokens('[data-theme="light"]')}

PARES = [
    ("texto", "superficie"),
    ("texto-muted", "superficie"),
    ("texto-fraco", "superficie"),
    ("acento", "superficie"),
    ("acento", "superficie-alt"),
    ("texto-botao", "acento-solido"),
]
PARES_CLARO = PARES + [
    ("texto-muted", "bg"),
    ("texto-fraco", "bg"),
    ("sucesso-texto", "superficie"),
]


@pytest.mark.parametrize("texto, fundo", PARES)
def test_contraste_do_tema_escuro(texto, fundo):
    assert contraste(ESCURO[texto], ESCURO[fundo]) >= 4.5, (texto, fundo)


@pytest.mark.parametrize("texto, fundo", PARES_CLARO)
def test_contraste_do_tema_claro(texto, fundo):
    assert contraste(CLARO[texto], CLARO[fundo]) >= 4.5, (texto, fundo)


def test_css_nao_tem_mais_o_tema_ambar():
    assert 'data-theme="ambar"' not in CSS


def test_tema_js_so_conhece_escuro_e_claro():
    js = (RAIZ / "static" / "js" / "tema.js").read_text(encoding="utf-8")
    assert 'const TEMAS = ["dark", "light"];' in js
    assert "ambar" not in js


def test_nenhum_template_oferece_o_tema_ambar():
    for arquivo in sorted((RAIZ / "templates").glob("*.html")):
        assert 'data-tema="ambar"' not in arquivo.read_text(encoding="utf-8"), arquivo.name


def test_botoes_usam_acento_solido_como_fundo():
    """Branco sobre --acento (#2D8CF0) dá 3.43:1; botão usa --acento-solido."""
    for nome in ("style.css", "apresentacao.css"):
        css = (RAIZ / "static" / "css" / nome).read_text(encoding="utf-8")
        assert "background: var(--acento);" not in css, nome
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider tests/test_tema.py -v`
Expected: FAIL — `KeyError: 'acento-solido'` na coleta (tokens novos não existem) ou falhas nos testes do âmbar.

- [ ] **Step 3: Reescrever os tokens de `style.css`**

Rodar na VM (o script normaliza para `\n`, edita e grava de volta com o terminador original do arquivo):

```bash
cd $HOME/mnt/helpdesk-system && python3 - <<'PY'
import pathlib

CABECALHO = '''/* ==============================
   SISTEMA HELP DESK - ESTILO GERAL
   Tema escuro é o padrão (:root); o claro sobrescreve as mesmas variáveis em
   [data-theme="light"]. Nenhuma regra abaixo destes blocos deveria usar cor
   literal fora das variáveis, senão ela não reage à troca de tema.
   `static/js/tema.js` decide qual atributo aplicar no <html> (escolha salva >
   preferência do sistema > escuro).

   Visual novo (2026, Fase 1): acento azul no lugar da paleta monocromática,
   cartões com elevação sutil (sombra, sem deslocamento nem escala) e uma
   escala única de raio (--raio-controle para botão/input/badge,
   --raio-superficie para container/cartão, --raio-pilula só nas abas).
   --acento é para texto, indicador e gráfico; fundo de botão com texto branco
   usa --acento-solido (branco sobre #2D8CF0 dá só 3.43:1).
   O tema âmbar saiu nesta fase. Os nomes antigos de token (--marca,
   --acento-forte, --acento-legivel...) ficam como alias até as Fases 2 e 3.
   ============================== */
'''

ESCURO = ''':root {
    color-scheme: dark;
    --bg: #0B0D12;
    --bg-gradiente-topo: #0F121A;
    --bg-gradiente-base: #0B0D12;
    --superficie: #12151C;
    --superficie-alt: #1A1E27;
    --borda: rgba(255, 255, 255, 0.08);
    --borda-forte: rgba(255, 255, 255, 0.16);
    --texto: #F2F4F8;
    --texto-muted: #A3AAB8;
    --texto-fraco: #8B93A3;
    --acento: #2D8CF0;
    --acento-rgb: 45, 140, 240;
    --acento-solido: #1F6FD1;
    --acento-solido-hover: #1A62BD;
    --acento-suave: rgba(45, 140, 240, 0.14);
    --texto-botao: #FFFFFF;
    --sombra-1: 0 1px 2px rgba(0, 0, 0, 0.4), 0 1px 1px rgba(0, 0, 0, 0.25);
    --sombra-2: 0 8px 24px rgba(0, 0, 0, 0.45), 0 2px 6px rgba(0, 0, 0, 0.3);
    --raio-controle: 6px;
    --raio-superficie: 10px;
    --raio-pilula: 999px;
    --grafico-grade: rgba(255, 255, 255, 0.06);
    /* Aliases dos nomes antigos, usados por páginas que só migram nas Fases 2
       e 3. Resolvem no mesmo elemento (<html>), então seguem o tema ativo. */
    --marca: var(--acento);
    --marca-rgb: var(--acento-rgb);
    --acento-forte: var(--acento);
    --acento-forte-rgb: var(--acento-rgb);
    --acento-hover: var(--acento-solido-hover);
    --acento-hover-forte: var(--acento-solido-hover);
    --acento-legivel: var(--acento);
    --acento-legivel-rgb: var(--acento-rgb);
    /* Faixa de CTA da apresentação: botão claro sobre a faixa escura. */
    --cta-superficie: #FFFFFF;
    --cta-superficie-hover: #E2E6EC;
    --cta-texto: #0B0D12;
    --sucesso-bg: rgba(74, 194, 122, 0.14);
    --sucesso-texto: #7fd9a0;
    --sucesso-borda: rgba(74, 194, 122, 0.28);
    --sucesso-solido: #3fae6c;
    --sucesso-solido-forte: #2f8f56;
    --sucesso-solido-hover: #4dbd7a;
    --sucesso-solido-hover-forte: #379d60;
    --erro-bg: rgba(224, 92, 92, 0.14);
    --erro-texto: #f0a3a3;
    --erro-borda: rgba(224, 92, 92, 0.28);
    --perigo-solido: #c94d4d;
    --perigo-solido-forte: #a83d3d;
    --perigo-solido-hover: #d66161;
    --perigo-solido-hover-forte: #b84747;
    --aviso-bg: rgba(214, 158, 66, 0.16);
    --aviso-texto: #e8bd7c;
    --info-bg: rgba(94, 160, 189, 0.16);
    --info-texto: #92c1da;
    --prioridade-alta-bg: rgba(224, 138, 66, 0.16);
    --prioridade-alta-texto: #eba873;
    --prioridade-critica-bg: rgba(224, 92, 92, 0.2);
    --prioridade-critica-texto: #f0a3a3;
    --sombra-linha: rgba(0, 0, 0, 0.35);
    --hover-linha: rgba(255, 255, 255, 0.04);
    --hover-pagina: rgba(255, 255, 255, 0.08);
}
'''

CLARO = '''/* TEMA CLARO — mesmas variáveis, valores diferentes. Os tons de status/
   prioridade também ganham override aqui: os do tema escuro (pensados para
   fundo escuro) somem sobre superfície clara. Os aliases (--marca etc.) não
   precisam ser repetidos: resolvem a partir dos valores abaixo. */
[data-theme="light"] {
    color-scheme: light;
    --bg: #F6F7F9;
    --bg-gradiente-topo: #FFFFFF;
    --bg-gradiente-base: #F6F7F9;
    --superficie: #FFFFFF;
    --superficie-alt: #EEF1F5;
    --borda: rgba(31, 36, 48, 0.10);
    --borda-forte: rgba(31, 36, 48, 0.20);
    --texto: #1F2430;
    --texto-muted: #5B6475;
    --texto-fraco: #646C7C;
    --acento: #1A66C7;
    --acento-rgb: 26, 102, 199;
    --acento-solido: #1A66C7;
    --acento-solido-hover: #15559F;
    --acento-suave: rgba(26, 102, 199, 0.10);
    --texto-botao: #FFFFFF;
    --sombra-1: 0 1px 2px rgba(31, 36, 48, 0.08), 0 1px 1px rgba(31, 36, 48, 0.04);
    --sombra-2: 0 8px 24px rgba(31, 36, 48, 0.12), 0 2px 6px rgba(31, 36, 48, 0.06);
    --grafico-grade: rgba(31, 36, 48, 0.08);
    --cta-superficie: var(--acento-solido);
    --cta-superficie-hover: var(--acento-solido-hover);
    --cta-texto: #FFFFFF;
    --sucesso-bg: rgba(37, 122, 72, 0.10);
    --sucesso-texto: #257A48;
    --sucesso-borda: rgba(37, 122, 72, 0.26);
    --sucesso-solido: #257A48;
    --sucesso-solido-forte: #1E643B;
    --sucesso-solido-hover: #2B8A52;
    --sucesso-solido-hover-forte: #22703F;
    --erro-bg: rgba(196, 58, 58, 0.1);
    --erro-texto: #a83d3d;
    --erro-borda: rgba(196, 58, 58, 0.26);
    --perigo-solido: #a83d3d;
    --perigo-solido-forte: #8a3131;
    --perigo-solido-hover: #b84747;
    --perigo-solido-hover-forte: #953838;
    --aviso-bg: rgba(168, 120, 40, 0.12);
    --aviso-texto: #8a611f;
    --info-bg: rgba(52, 108, 140, 0.12);
    --info-texto: #2f5d78;
    --prioridade-alta-bg: rgba(168, 97, 31, 0.14);
    --prioridade-alta-texto: #8a4f19;
    --prioridade-critica-bg: rgba(196, 58, 58, 0.14);
    --prioridade-critica-texto: #a83d3d;
    --sombra-linha: rgba(31, 36, 48, 0.08);
    --hover-linha: rgba(31, 36, 48, 0.035);
    --hover-pagina: rgba(31, 36, 48, 0.06);
}
'''

arquivo = pathlib.Path("static/css/style.css")
bruto = arquivo.read_bytes().decode("utf-8")
fim_de_linha = "\r\n" if "\r\n" in bruto else "\n"
css = bruto.replace("\r\n", "\n")

# 1. Comentário do topo (até o primeiro fechamento de bloco de comentário).
fim_cabecalho = css.index("   ============================== */\n") + len("   ============================== */\n")
assert css.startswith("/* ==============================")
css = CABECALHO + css[fim_cabecalho:]

# 2. Bloco :root.
inicio = css.index(":root {\n")
fim = css.index("\n}\n", inicio) + len("\n}\n")
css = css[:inicio] + ESCURO + css[fim:]

# 3. Comentário + bloco do tema claro, comentário + bloco do âmbar → só o claro novo.
inicio = css.index("/* TEMA CLARO")
inicio_ambar = css.index('[data-theme="ambar"] {')
fim = css.index("\n}\n", inicio_ambar) + len("\n}\n")
css = css[:inicio] + CLARO + css[fim:]

# 4. Botões: fundo sai de --acento (texto) para --acento-solido.
assert css.count("background: var(--acento);") == 5, css.count("background: var(--acento);")
css = css.replace("background: var(--acento);", "background: var(--acento-solido);")

assert "ambar" not in css
arquivo.write_bytes(css.replace("\n", fim_de_linha).encode("utf-8"))
print("style.css ok,", fim_de_linha == "\r\n" and "CRLF" or "LF")
PY
```

- [ ] **Step 4: `apresentacao.css`, `auth.css`, `tema.js`, templates e README**

```bash
cd $HOME/mnt/helpdesk-system && python3 - <<'PY'
import pathlib

def editar(caminho, trocas):
    arquivo = pathlib.Path(caminho)
    bruto = arquivo.read_bytes().decode("utf-8")
    fim_de_linha = "\r\n" if "\r\n" in bruto else "\n"
    texto = bruto.replace("\r\n", "\n")
    for antigo, novo, vezes in trocas:
        assert texto.count(antigo) == vezes, (caminho, antigo[:40], texto.count(antigo))
        texto = texto.replace(antigo, novo)
    arquivo.write_bytes(texto.replace("\n", fim_de_linha).encode("utf-8"))

editar("static/css/apresentacao.css", [
    ("background: var(--acento);", "background: var(--acento-solido);", 1),
])
editar("static/css/auth.css", [
    ('[data-theme="light"]/[data-theme="ambar"]', '[data-theme="light"]', 1),
])

# tema.js: comentário do topo inteiro + constantes.
js = pathlib.Path("static/js/tema.js").read_text(encoding="utf-8")
fim_comentario = js.index(" */\n") + len(" */\n")
novo_comentario = '''/**
 * Alternância de tema claro/escuro (issue #44). O terceiro tema, "fim de
 * tarde" (issue #79), saiu no visual novo (Fase 1): não combinava com o
 * acento azul. Quem tinha essa escolha salva cai na regra abaixo, como quem
 * nunca escolheu.
 *
 * Duas partes, de propósito separadas:
 *
 * 1. `aplicarTemaSalvo()` — roda inline, no <head>, ANTES do CSS carregar.
 *    Só ela decide qual tema pintar na tela logo de cara: sem isso, a página
 *    sempre nasceria escura (o :root de style.css) e só trocaria de cor um
 *    instante depois, quando este arquivo carregasse — um "flash" visível.
 *
 * 2. O resto deste arquivo — o seletor de tema e o listener de clique — só
 *    existe nas páginas que têm o seletor (ver `configurarSeletorDeTema`).
 *
 * Prioridade de decisão, em ordem: escolha manual salva > preferência do
 * sistema operacional > escuro (mesma prioridade nas duas partes). Valor
 * salvo que não está em TEMAS conta como "sem escolha".
 */
'''
js = novo_comentario + js[fim_comentario:]
for antigo, novo in [
    ('const TEMAS = ["dark", "light", "ambar"];', 'const TEMAS = ["dark", "light"];'),
    ('    ambar: "🌇",\n', ""),
    ('    ambar: "Tema âmbar (fim de tarde)",\n', ""),
]:
    assert js.count(antigo) == 1, antigo
    js = js.replace(antigo, novo)
assert "ambar" not in js
pathlib.Path("static/js/tema.js").write_text(js, encoding="utf-8")

# Templates: o botão do âmbar some de todas as páginas.
botao = '<button type="button" data-tema="ambar"></button>'
alterados = 0
for arquivo in sorted(pathlib.Path("templates").glob("*.html")):
    texto = arquivo.read_bytes().decode("utf-8")
    if botao in texto:
        arquivo.write_bytes(texto.replace(botao, "").encode("utf-8"))
        alterados += 1
print("templates alterados:", alterados)

editar("README.md", [(
    "- **Três temas de interface**  \n"
    "  Escuro (padrão — preto predominante, detalhes em branco e botões cinza\n"
    "  escuro), claro e âmbar, trocáveis a qualquer momento pelo seletor presente\n"
    "  em toda tela.",
    "- **Dois temas de interface**  \n"
    "  Escuro (padrão — fundo quase preto com acento azul) e claro, trocáveis a\n"
    "  qualquer momento pelo seletor presente em toda tela; sem escolha salva,\n"
    "  vale a preferência do sistema operacional.",
    1,
)])
print("ok")
PY
```

Expected: `templates alterados: 20` e `ok`.

- [ ] **Step 5: Rodar os testes de tema**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider tests/test_tema.py -v`
Expected: 19 passed.

- [ ] **Step 6: Suíte inteira**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider -q`
Expected: 228 passed.

- [ ] **Step 7: Conferir o diff**

Run: `cd $HOME/mnt/helpdesk-system && git --no-optional-locks diff --ignore-space-at-eol --stat`
Expected: só os arquivos desta task (e os das anteriores) aparecem; `style.css` com mudança concentrada no topo e em 5 linhas de `background`. Se `style.css` aparecer com o arquivo inteiro alterado, o CRLF foi perdido — refazer o Step 3 a partir do arquivo original.

- [ ] **Step 8: Arquivos do commit (o Edu commita)**

`static/css/style.css`, `static/css/apresentacao.css`, `static/css/auth.css`, `static/js/tema.js`, os 20 `templates/*.html`, `README.md`, `tests/test_tema.py` — mensagem sugerida: `feat(ui): adota acento azul e remove o tema âmbar`

---

### Task 5: `base.html`, `base_app.html` e topbar (dashboard migrado para o layout novo)

**Files:**
- Create: `templates/base.html`, `templates/base_app.html`, `templates/_topbar.html`
- Modify: `templates/dashboard.html` (passa a estender `base_app.html`; conteúdo atual preservado, sem a barra `.usuario-logado`, o título antigo, o bloco `.acoes` e o rodapé)
- Modify: `static/css/style.css` (CRLF — acrescentar seção "LAYOUT DO APP" no fim)
- Modify: `tests/test_app.py` (1 asserção presa ao título antigo)
- Test: `tests/test_topbar.py` (novo)

**Interfaces:**
- Consumes: tokens da Task 4; `usuario_logado` (context processor de `app.py`, com `.nome`, `.tipo_usuario`, `.eh_tecnico`, `.eh_admin`); `csp_nonce()`, `csrf_token()`, `request.endpoint`.
- Produces (usado pela Task 6 e pelas Fases 2 e 3):
  - `base.html` com blocos `titulo`, `head_extra`, `classe_body`, `corpo`
  - `base_app.html` (estende `base.html`) com bloco `conteudo`; mostra a primeira mensagem flash em `<p class="sucesso">`
  - classes CSS: `.sr-only`, `.topbar`, `.aba`, `.botao-primario`, `.menu-usuario`, `.app-conteudo`, `.pagina-cabecalho`, `.pagina-rotulo`, `.pagina-titulo`
  - endpoints nas abas: `chamados.dashboard`, `chamados.lista_chamados` (+ `chamados.detalhe_chamado`), `chamados.meus_chamados`, `admin.*`

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/test_topbar.py`:

```python
"""Topbar do layout novo (visual novo, Fase 1)."""

import re

SENHA = "senha-de-teste"


def _entrar(client, criar_usuario, tipo="Usuário", nome="Fulano"):
    email = f"{tipo.lower().replace('á', 'a').replace('é', 'e')}@teste.com"
    criar_usuario(nome=nome, email=email, tipo=tipo)
    client.post("/login", data={"email": email, "senha": SENHA})
    return client.get("/dashboard").get_data(as_text=True)


def test_dashboard_usa_a_topbar_com_a_aba_ativa(client, criar_usuario):
    html = _entrar(client, criar_usuario)

    assert 'class="topbar"' in html
    assert re.search(r'href="/dashboard"\s+aria-current="page"', html)
    assert not re.search(r'href="/chamados"\s+aria-current="page"', html)


def test_usuario_comum_nao_ve_abas_de_tecnico_nem_de_admin(client, criar_usuario):
    html = _entrar(client, criar_usuario, tipo="Usuário")

    assert ">Chamados</a>" in html
    assert ">Meus chamados</a>" not in html
    assert ">Admin</a>" not in html


def test_tecnico_ve_meus_chamados_mas_nao_admin(client, criar_usuario):
    html = _entrar(client, criar_usuario, tipo="Técnico")

    assert ">Meus chamados</a>" in html
    assert ">Admin</a>" not in html


def test_admin_ve_a_aba_admin(client, criar_usuario):
    html = _entrar(client, criar_usuario, tipo="Administrador")

    assert ">Meus chamados</a>" in html
    assert ">Admin</a>" in html


def test_topbar_tem_novo_chamado_menu_do_usuario_e_sair_com_csrf(client, criar_usuario):
    html = _entrar(client, criar_usuario)

    assert 'href="/chamado"' in html and "Novo chamado" in html
    assert 'href="/senha"' in html
    assert 'href="/meu-token"' in html
    assert re.search(r'<form method="POST" action="/logout">\s*<input type="hidden" name="csrf_token"', html)
    assert 'class="acoes"' not in html  # os botões antigos do rodapé do dashboard sumiram


def test_inicial_do_usuario_com_acento(client, criar_usuario):
    html = _entrar(client, criar_usuario, nome="Álvaro Souza")

    assert '<span class="menu-usuario-inicial" aria-hidden="true">Á</span>' in html


def test_script_de_tema_tem_nonce_e_ignora_tema_desconhecido(client, criar_usuario):
    """Quem tinha "ambar" salvo cai na preferência do sistema, não num tema sem estilo."""
    html = _entrar(client, criar_usuario)

    assert re.search(r'<script nonce="[^"]+">', html)
    assert 'if (tema !== "dark" && tema !== "light")' in html
    assert html.count('data-tema="') == 2
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider tests/test_topbar.py -v`
Expected: FAIL — `'class="topbar"'` não está no HTML (e as demais asserções da topbar).

- [ ] **Step 3: Criar `templates/base.html`**

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{% block titulo %}Help Desk{% endblock %}</title>
    <script nonce="{{ csp_nonce() }}">
    // Aplica o tema salvo (ou o do sistema operacional) antes do CSS carregar,
    // para não piscar no tema errado. Lógica completa e comentada em
    // static/js/tema.js — este trecho precisa ser inline e vir antes do <link>
    // do CSS. Só "dark" e "light" existem; qualquer outro valor salvo (como o
    // antigo "ambar") conta como sem escolha.
    (function () {
        var tema;
        try {
            tema = localStorage.getItem("tema-preferido");
        } catch (erro) {
            tema = null;
        }
        if (tema !== "dark" && tema !== "light") {
            var prefereClaro = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches;
            tema = prefereClaro ? "light" : "dark";
        }
        document.documentElement.setAttribute("data-theme", tema);
    })();
    </script>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <script src="{{ url_for('static', filename='js/tema.js') }}"></script>
    {% block head_extra %}{% endblock %}
</head>
<body class="{% block classe_body %}{% endblock %}">
{% block corpo %}{% endblock %}
</body>
</html>
```

- [ ] **Step 4: Criar `templates/base_app.html`**

```html
{% extends "base.html" %}

{% block classe_body %}app{% endblock %}

{% block corpo %}
{% include "_topbar.html" %}

<main class="app-conteudo" id="conteudo">
    {% with mensagens = get_flashed_messages() %}
    {% if mensagens %}
    <p class="sucesso">{{ mensagens[0] }}</p>
    {% endif %}
    {% endwith %}

    {% block conteudo %}{% endblock %}
</main>

<footer class="rodape-app">
    <span>v1.2.0</span>
    <span aria-hidden="true">·</span>
    <span>by <a href="https://github.com/DZ092" target="_blank" rel="noopener">Eduardo Jr. Coelho</a></span>
</footer>
{% endblock %}
```

- [ ] **Step 5: Criar `templates/_topbar.html`**

```html
{# Barra superior das páginas internas (visual novo, Fase 1). A aba ativa é
   decidida aqui mesmo, pelo endpoint da requisição — nenhuma página precisa
   passar variável para isso. #}
{% set endpoint = request.endpoint or "" %}
<header class="topbar">
    <div class="topbar-interna">
        <a class="topbar-marca" href="{{ url_for('chamados.dashboard') }}">
            <svg class="topbar-marca-icone" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <rect x="3" y="4" width="18" height="13" rx="3" fill="none" stroke="currentColor" stroke-width="2"/>
                <path d="M9 21h6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                <path d="M8.5 10.5l2.5 2.5 4.5-4.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span>Help Desk</span>
        </a>

        <nav class="topbar-abas" aria-label="Navegação principal">
            <a class="aba" href="{{ url_for('chamados.dashboard') }}" {% if endpoint == 'chamados.dashboard' %}aria-current="page"{% endif %}>Dashboard</a>
            <a class="aba" href="{{ url_for('chamados.lista_chamados') }}" {% if endpoint in ('chamados.lista_chamados', 'chamados.detalhe_chamado') %}aria-current="page"{% endif %}>Chamados</a>
            {% if usuario_logado.eh_tecnico %}
            <a class="aba" href="{{ url_for('chamados.meus_chamados') }}" {% if endpoint == 'chamados.meus_chamados' %}aria-current="page"{% endif %}>Meus chamados</a>
            {% endif %}
            {% if usuario_logado.eh_admin %}
            <a class="aba" href="{{ url_for('admin.admin_usuarios') }}" {% if endpoint.startswith('admin.') %}aria-current="page"{% endif %}>Admin</a>
            {% endif %}
        </nav>

        <div class="topbar-acoes">
            <a class="botao-primario" href="{{ url_for('chamados.chamado') }}">+ Novo chamado</a>
            <div id="seletor-tema" class="seletor-tema"><button type="button" data-tema="dark"></button><button type="button" data-tema="light"></button></div>
            <details class="menu-usuario">
                <summary aria-label="Menu de {{ usuario_logado.nome }}">
                    <span class="menu-usuario-inicial" aria-hidden="true">{{ usuario_logado.nome[:1] | upper }}</span>
                    <span class="menu-usuario-nome">{{ usuario_logado.nome }}</span>
                </summary>
                <div class="menu-usuario-painel">
                    <p class="menu-usuario-perfil">{{ usuario_logado.tipo_usuario }}</p>
                    <a href="{{ url_for('auth.alterar_senha') }}">Alterar senha</a>
                    <a href="{{ url_for('auth.meu_token') }}">Meu token de API</a>
                    <form method="POST" action="{{ url_for('auth.logout') }}">
                        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                        <button type="submit">Sair</button>
                    </form>
                </div>
            </details>
        </div>
    </div>
</header>
```

- [ ] **Step 6: Migrar `templates/dashboard.html` para `base_app.html`**

O conteúdo de dados (cartões + tabela) é preservado byte a byte por script — a Task 6 reescreve essa parte:

```bash
cd $HOME/mnt/helpdesk-system && python3 - <<'PY'
import pathlib

arquivo = pathlib.Path("templates/dashboard.html")
antigo = arquivo.read_text(encoding="utf-8")
inicio = antigo.index('<div class="cards">')
fim = antigo.index('<div class="acoes">')
miolo = antigo[inicio:fim].rstrip() + "\n"

novo = (
    '{% extends "base_app.html" %}\n'
    "\n"
    "{% block titulo %}Dashboard · Help Desk{% endblock %}\n"
    "\n"
    "{% block conteudo %}\n"
    '<header class="pagina-cabecalho">\n'
    "    <div>\n"
    '        <p class="pagina-rotulo">Visão geral</p>\n'
    '        <h1 class="pagina-titulo">Dashboard</h1>\n'
    "    </div>\n"
    "</header>\n"
    "\n"
    + miolo
    + "{% endblock %}\n"
)
arquivo.write_text(novo, encoding="utf-8")
print("dashboard migrado")
PY
```

- [ ] **Step 7: CSS do layout do app**

Acrescentar no fim de `static/css/style.css` (CRLF preservado pelo script):

```bash
cd $HOME/mnt/helpdesk-system && python3 - <<'PY'
import pathlib

SECAO = '''
/* ==============================
   LAYOUT DO APP (visual novo, Fase 1) — topbar + conteúdo
   Páginas que estendem base_app.html. Hover troca cor e sombra; nada se
   desloca nem muda de escala.
   ============================== */
.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}

body.app {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    background: var(--bg);
}

.topbar {
    position: sticky;
    top: 0;
    z-index: 10;
    background: var(--superficie);
    border-bottom: 1px solid var(--borda);
    box-shadow: var(--sombra-1);
}

.topbar-interna {
    max-width: 1200px;
    margin: 0 auto;
    padding: 10px 24px;
    display: flex;
    align-items: center;
    gap: 20px;
}

.topbar-marca {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: var(--texto);
    font-weight: 800;
    letter-spacing: -0.01em;
    text-decoration: none;
    white-space: nowrap;
}

.topbar-marca-icone {
    width: 22px;
    height: 22px;
    color: var(--acento);
}

.topbar-abas {
    display: flex;
    gap: 4px;
    flex: 1;
    min-width: 0;
    overflow-x: auto;
    scrollbar-width: none;
}

.topbar-abas .aba {
    padding: 7px 14px;
    border-radius: var(--raio-pilula);
    color: var(--texto-muted);
    font-size: 14px;
    font-weight: 600;
    text-decoration: none;
    white-space: nowrap;
    transition: background-color 0.15s ease, color 0.15s ease;
}

.topbar-abas .aba:hover {
    color: var(--texto);
    background: var(--superficie-alt);
}

.topbar-abas .aba[aria-current="page"] {
    color: var(--texto);
    background: var(--acento-suave);
    box-shadow: inset 0 0 0 1px rgba(var(--acento-rgb), 0.35);
}

.topbar-acoes {
    display: flex;
    align-items: center;
    gap: 12px;
}

.botao-primario {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 14px;
    border-radius: var(--raio-controle);
    background: var(--acento-solido);
    color: var(--texto-botao);
    font-size: 14px;
    font-weight: 700;
    text-decoration: none;
    white-space: nowrap;
    box-shadow: var(--sombra-1);
    transition: background-color 0.15s ease, box-shadow 0.15s ease;
}

.botao-primario:hover {
    background: var(--acento-solido-hover);
    box-shadow: var(--sombra-2);
}

.topbar-abas .aba:focus-visible,
.botao-primario:focus-visible,
.topbar-marca:focus-visible,
.menu-usuario summary:focus-visible,
.menu-usuario-painel a:focus-visible,
.menu-usuario-painel button:focus-visible {
    outline: 2px solid var(--acento);
    outline-offset: 2px;
}

.menu-usuario {
    position: relative;
}

.menu-usuario summary {
    list-style: none;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 10px 4px 4px;
    border-radius: var(--raio-pilula);
    color: var(--texto);
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
}

.menu-usuario summary::-webkit-details-marker {
    display: none;
}

.menu-usuario summary:hover {
    background: var(--superficie-alt);
}

.menu-usuario-inicial {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    background: var(--acento-solido);
    color: var(--texto-botao);
    font-weight: 800;
}

.menu-usuario-painel {
    position: absolute;
    right: 0;
    top: calc(100% + 8px);
    min-width: 210px;
    padding: 8px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    background: var(--superficie);
    border: 1px solid var(--borda);
    border-radius: var(--raio-superficie);
    box-shadow: var(--sombra-2);
}

.menu-usuario-perfil {
    padding: 6px 10px;
    font-size: 12px;
    color: var(--texto-fraco);
}

.menu-usuario-painel a,
.menu-usuario-painel button {
    display: block;
    width: 100%;
    padding: 8px 10px;
    border: 0;
    border-radius: var(--raio-controle);
    background: none;
    color: var(--texto);
    font: inherit;
    font-size: 14px;
    text-align: left;
    text-decoration: none;
    cursor: pointer;
}

.menu-usuario-painel a:hover,
.menu-usuario-painel button:hover {
    background: var(--superficie-alt);
}

.app-conteudo {
    flex: 1;
    width: 100%;
    max-width: 1200px;
    margin: 0 auto;
    padding: 28px 24px 40px;
}

.pagina-cabecalho {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 24px;
}

.pagina-rotulo {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--acento);
}

.pagina-titulo {
    text-align: left;
    font-size: 28px;
    margin: 2px 0 0;
}

@media (max-width: 768px) {
    .topbar-interna {
        flex-wrap: wrap;
        gap: 10px;
        padding: 10px 16px;
    }

    .topbar-abas {
        order: 3;
        flex-basis: 100%;
    }

    .menu-usuario-nome {
        display: none;
    }

    .menu-usuario summary {
        padding-right: 4px;
    }

    .app-conteudo {
        padding: 20px 16px 32px;
    }
}

@media (prefers-reduced-motion: reduce) {
    .topbar-abas .aba,
    .botao-primario {
        transition: none;
    }
}
'''

arquivo = pathlib.Path("static/css/style.css")
bruto = arquivo.read_bytes().decode("utf-8")
fim_de_linha = "\r\n" if "\r\n" in bruto else "\n"
texto = bruto.replace("\r\n", "\n").rstrip("\n") + "\n" + SECAO
arquivo.write_bytes(texto.replace("\n", fim_de_linha).encode("utf-8"))
print("seção do layout acrescentada")
PY
```

- [ ] **Step 8: Ajustar a asserção presa ao título antigo**

Em `tests/test_app.py`, função `test_usuario_comum_nao_acessa_painel_admin`, trocar a linha:

```python
    assert "Dashboard Help Desk".encode() in resposta.data
```

por:

```python
    assert '<h1 class="pagina-titulo">Dashboard</h1>'.encode() in resposta.data
```

(O teste continua verificando a mesma coisa: o usuário comum é mandado para o dashboard.)

- [ ] **Step 9: Rodar e ver passar**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider tests/test_topbar.py tests/test_app.py tests/test_rotas.py -v`
Expected: tudo passa (7 novos em `test_topbar.py`).

- [ ] **Step 10: Suíte inteira**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider -q`
Expected: 235 passed.

- [ ] **Step 11: Arquivos do commit (o Edu commita)**

`templates/base.html`, `templates/base_app.html`, `templates/_topbar.html`, `templates/dashboard.html`, `static/css/style.css`, `tests/test_app.py`, `tests/test_topbar.py` — mensagem sugerida: `feat(ui): cria base.html e a topbar com abas no dashboard`

---

### Task 6: Dashboard com KPIs, gráficos e seletor de período

**Files:**
- Create: `templates/_graficos.html`
- Modify: `templates/dashboard.html` (reescrita; a tabela de chamados recentes é reaproveitada por script)
- Modify: `rotas/chamados.py` (imports e função `dashboard`)
- Modify: `static/css/style.css` (CRLF — acrescentar seção "DASHBOARD")
- Test: `tests/test_dashboard.py` (novo)

**Interfaces:**
- Consumes: `metricas.*` (Task 2), `graficos.*` (Task 3), tokens (Task 4), `base_app.html` e classes `.pagina-*`/`.sr-only` (Task 5), `obter_data_utc` de `models.py`.
- Produces: rota `/dashboard?periodo=<7|30|90|tudo>`; macros `grafico_linhas`, `grafico_empilhado`, `grafico_barras`, `grafico_donut`, `tabela_rotulo_valor`, `tabela_semanas` em `templates/_graficos.html`; classes `.cartao`, `.painel*`, `.kpi*`, `.legenda*`, `.estado-vazio`, `.seletor-periodo`.

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/test_dashboard.py`:

```python
"""Dashboard com indicadores e gráficos (visual novo, Fase 1)."""

import re
from datetime import timedelta

from extensions import db
from models import Chamado, obter_data_utc

SENHA = "senha-de-teste"


def _entrar(client, criar_usuario):
    criar_usuario(nome="Ana Admin", email="admin@teste.com", tipo="Administrador")
    client.post("/login", data={"email": "admin@teste.com", "senha": SENHA})


def _chamado(dias_atras=1, status="Aberto", prioridade="Alta", setor="Financeiro", horas_para_resolver=None):
    criado = obter_data_utc() - timedelta(days=dias_atras)
    resolvido = criado + timedelta(hours=horas_para_resolver) if horas_para_resolver is not None else None
    chamado = Chamado(
        usuario="Maria",
        setor=setor,
        titulo="Computador não liga",
        descricao="Tela preta ao ligar",
        status=status,
        prioridade=prioridade,
        criado_em=criado,
        resolvido_em=resolvido,
    )
    db.session.add(chamado)
    db.session.commit()
    return chamado


def test_dashboard_mostra_os_quatro_graficos_com_tabelas_acessiveis(client, criar_usuario):
    _entrar(client, criar_usuario)
    _chamado()
    _chamado(status="Resolvido", horas_para_resolver=2, setor="TI", prioridade="Baixa")

    html = client.get("/dashboard").get_data(as_text=True)

    assert html.count('role="img"') == 4
    assert html.count('<table class="sr-only">') == 4
    assert 'style="' not in html  # CSP: nada de estilo inline


def test_dashboard_mostra_os_kpis(client, criar_usuario):
    _entrar(client, criar_usuario)
    _chamado()
    _chamado()
    _chamado(status="Resolvido", horas_para_resolver=2)

    html = client.get("/dashboard").get_data(as_text=True)

    assert re.search(r'Total de chamados</p>\s*<p class="kpi-valor">3</p>', html)
    assert "33% do total" in html
    assert '<p class="kpi-valor">2h00</p>' in html
    assert "2 abertos · 0 em andamento" in html


def test_dashboard_sem_chamados_mostra_estado_vazio(client, criar_usuario):
    _entrar(client, criar_usuario)

    html = client.get("/dashboard").get_data(as_text=True)

    assert 'role="img"' not in html
    assert "Nenhum chamado neste período." in html
    assert "Nenhum chamado nas últimas 8 semanas." in html


def test_periodo_invalido_usa_30_dias(client, criar_usuario):
    _entrar(client, criar_usuario)

    resposta = client.get("/dashboard?periodo=xyz")

    assert resposta.status_code == 200
    assert re.search(r'href="/dashboard\?periodo=30"\s+aria-current="true"', resposta.get_data(as_text=True))


def test_periodo_filtra_os_indicadores(client, criar_usuario):
    _entrar(client, criar_usuario)
    _chamado(dias_atras=40)

    html_30 = client.get("/dashboard?periodo=30").get_data(as_text=True)
    html_tudo = client.get("/dashboard?periodo=tudo").get_data(as_text=True)

    assert "Nenhum chamado neste período." in html_30
    assert "Nenhum chamado neste período." not in html_tudo


def test_chamados_recentes_tem_link_para_a_lista(client, criar_usuario):
    _entrar(client, criar_usuario)
    _chamado()

    html = client.get("/dashboard").get_data(as_text=True)

    assert "Chamados recentes" in html
    assert '<a class="painel-link" href="/chamados">Ver todos</a>' in html
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider tests/test_dashboard.py -v`
Expected: FAIL — nenhum `role="img"` e nenhum `kpi-valor` no HTML atual.

- [ ] **Step 3: Criar `templates/_graficos.html`**

```html
{# Gráficos SVG do dashboard (visual novo, Fase 1). A geometria chega pronta
   de graficos.py; aqui só se imprime. Tamanho e posição vão como atributo
   SVG, nunca style="…" (o CSP bloqueia). Cada gráfico tem role="img" com um
   resumo em aria-label; os números exatos vão numa tabela .sr-only. Cor sempre
   por classe: .fatia-* define --cor-fatia no CSS. #}

{% macro grafico_linhas(semanas, linha_criados, linha_resolvidos) %}
<svg class="grafico grafico-linhas" viewBox="0 0 600 220" role="img"
     aria-label="Chamados criados e resolvidos por semana, nas últimas {{ semanas|length }} semanas">
    {% for y, valor in linha_criados.grade %}
    <line class="grafico-grade" x1="24" x2="576" y1="{{ y }}" y2="{{ y }}"/>
    <text class="grafico-eixo" x="0" y="{{ y }}" dominant-baseline="middle">{{ valor }}</text>
    {% endfor %}
    <polyline class="serie serie-criados" points="{{ linha_criados.pontos }}"/>
    <polyline class="serie serie-resolvidos" points="{{ linha_resolvidos.pontos }}"/>
    {% for x, y in linha_criados.marcas %}<circle class="marca serie-criados" cx="{{ x }}" cy="{{ y }}" r="3.5"/>{% endfor %}
    {% for x, y in linha_resolvidos.marcas %}<circle class="marca serie-resolvidos" cx="{{ x }}" cy="{{ y }}" r="3.5"/>{% endfor %}
    {% for semana in semanas %}
    <text class="grafico-eixo" x="{{ linha_criados.marcas[loop.index0][0] }}" y="212" text-anchor="middle">{{ semana.inicio.strftime("%d/%m") }}</text>
    {% endfor %}
</svg>
{% endmacro %}

{% macro grafico_empilhado(partes) %}
{% set classes = {"Aberto": "aberto", "Em andamento": "andamento", "Resolvido": "resolvido"} %}
<svg class="grafico grafico-empilhado" viewBox="0 0 100 10" preserveAspectRatio="none" role="img"
     aria-label="Chamados por status: {% for parte in partes %}{{ parte.rotulo }} {{ parte.valor }}{% if not loop.last %}, {% endif %}{% endfor %}">
    {% for parte in partes %}{% if parte.valor %}
    <rect class="fatia-{{ classes[parte.rotulo] }}" x="{{ parte.x_pct }}" y="0" width="{{ parte.largura_pct }}" height="10"/>
    {% endif %}{% endfor %}
</svg>
<ul class="legenda">
    {% for parte in partes %}
    <li><span class="legenda-cor fatia-{{ classes[parte.rotulo] }}" aria-hidden="true"></span>{{ parte.rotulo }} <strong>{{ parte.valor }}</strong></li>
    {% endfor %}
</ul>
{% endmacro %}

{% macro grafico_barras(barras) %}
<div class="grafico grafico-barras" role="img"
     aria-label="Chamados por setor: {% for barra in barras %}{{ barra.rotulo }} {{ barra.valor }}{% if not loop.last %}, {% endif %}{% endfor %}">
    {% for barra in barras %}
    <div class="barra-linha">
        <span class="barra-rotulo">{{ barra.rotulo }}</span>
        <svg class="barra-trilho" viewBox="0 0 100 8" preserveAspectRatio="none" aria-hidden="true" focusable="false">
            <rect class="barra-fundo" x="0" y="0" width="100" height="8"/>
            <rect class="barra-valor" x="0" y="0" width="{{ barra.pct }}" height="8"/>
        </svg>
        <span class="barra-numero">{{ barra.valor }}</span>
    </div>
    {% endfor %}
</div>
{% endmacro %}

{% macro grafico_donut(fatias) %}
{% set classes = {"Baixa": "baixa", "Média": "media", "Alta": "alta", "Crítica": "critica"} %}
<div class="donut-bloco">
    <svg class="grafico grafico-donut" viewBox="0 0 100 100" role="img"
         aria-label="Chamados por prioridade: {% for fatia in fatias %}{{ fatia.rotulo }} {{ fatia.valor }}{% if not loop.last %}, {% endif %}{% endfor %}">
        <circle class="donut-trilho" cx="50" cy="50" r="40"/>
        {% for fatia in fatias %}{% if fatia.valor %}
        <circle class="donut-fatia fatia-{{ classes[fatia.rotulo] }}" cx="50" cy="50" r="40"
                stroke-dasharray="{{ fatia.dasharray }}" stroke-dashoffset="{{ fatia.dashoffset }}"
                transform="rotate(-90 50 50)"/>
        {% endif %}{% endfor %}
        <text class="donut-total" x="50" y="47" text-anchor="middle" dominant-baseline="middle">{{ fatias | sum(attribute="valor") }}</text>
        <text class="donut-legenda-total" x="50" y="61" text-anchor="middle" dominant-baseline="middle">chamados</text>
    </svg>
    <ul class="legenda legenda-vertical">
        {% for fatia in fatias %}
        <li><span class="legenda-cor fatia-{{ classes[fatia.rotulo] }}" aria-hidden="true"></span>{{ fatia.rotulo }} <strong>{{ fatia.valor }}</strong></li>
        {% endfor %}
    </ul>
</div>
{% endmacro %}

{% macro tabela_rotulo_valor(legenda, cabecalho, itens) %}
<table class="sr-only">
    <caption>{{ legenda }}</caption>
    <thead><tr><th scope="col">{{ cabecalho }}</th><th scope="col">Chamados</th></tr></thead>
    <tbody>
    {% for item in itens %}<tr><td>{{ item.rotulo }}</td><td>{{ item.valor }}</td></tr>{% endfor %}
    </tbody>
</table>
{% endmacro %}

{% macro tabela_semanas(semanas) %}
<table class="sr-only">
    <caption>Chamados criados e resolvidos por semana</caption>
    <thead><tr><th scope="col">Semana de</th><th scope="col">Criados</th><th scope="col">Resolvidos</th></tr></thead>
    <tbody>
    {% for semana in semanas %}<tr><td>{{ semana.inicio.strftime("%d/%m/%Y") }}</td><td>{{ semana.criados }}</td><td>{{ semana.resolvidos }}</td></tr>{% endfor %}
    </tbody>
</table>
{% endmacro %}
```

- [ ] **Step 4: Reescrever `templates/dashboard.html`**

O script guarda a tabela de chamados recentes que já existe no arquivo (do `<div class="tabela-rolavel">` até o fim do conteúdo) e monta o template novo em volta dela:

```bash
cd $HOME/mnt/helpdesk-system && python3 - <<'PY'
import pathlib

arquivo = pathlib.Path("templates/dashboard.html")
atual = arquivo.read_text(encoding="utf-8")
inicio = atual.index('<div class="tabela-rolavel">')
fim = atual.index("{% endblock %}", inicio)
tabela = atual[inicio:fim].rstrip() + "\n"

ICONE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{}</svg>'

novo = '''{% extends "base_app.html" %}
{% import "_graficos.html" as g %}

{% block titulo %}Dashboard · Help Desk{% endblock %}

{% block conteudo %}
<header class="pagina-cabecalho">
    <div>
        <p class="pagina-rotulo">Visão geral</p>
        <h1 class="pagina-titulo">Dashboard</h1>
    </div>
    <nav class="seletor-periodo" aria-label="Período dos indicadores">
        {% for chave, rotulo in periodos %}
        <a href="{{ url_for('chamados.dashboard', periodo=chave) }}" {% if chave == periodo %}aria-current="true"{% endif %}>{{ rotulo }}</a>
        {% endfor %}
    </nav>
</header>

<section class="kpis" aria-label="Indicadores do período">
    <article class="cartao kpi">
        <span class="kpi-icone">ICONE_TOTAL</span>
        <p class="kpi-rotulo">Total de chamados</p>
        <p class="kpi-valor">{{ kpis.total }}</p>
        <p class="kpi-detalhe">abertos no período</p>
    </article>
    <article class="cartao kpi">
        <span class="kpi-icone">ICONE_RESOLVIDOS</span>
        <p class="kpi-rotulo">Resolvidos</p>
        <p class="kpi-valor">{{ kpis.resolvidos }}</p>
        <p class="kpi-detalhe">{{ kpis.pct_resolvidos }}% do total</p>
    </article>
    <article class="cartao kpi">
        <span class="kpi-icone">ICONE_TEMPO</span>
        <p class="kpi-rotulo">Tempo médio de resolução</p>
        <p class="kpi-valor">{{ tempo_medio }}</p>
        <p class="kpi-detalhe">por chamado resolvido no período</p>
    </article>
    <article class="cartao kpi">
        <span class="kpi-icone">ICONE_ABERTO</span>
        <p class="kpi-rotulo">Em aberto</p>
        <p class="kpi-valor">{{ kpis.em_aberto }}</p>
        <p class="kpi-detalhe">{{ kpis.abertos }} abertos · {{ kpis.em_andamento }} em andamento</p>
    </article>
</section>

<div class="dashboard-grade">
    <section class="cartao painel painel-largo" aria-labelledby="titulo-evolucao">
        <div class="painel-cabecalho">
            <div>
                <h2 class="painel-titulo" id="titulo-evolucao">Evolução semanal</h2>
                <p class="painel-subtitulo">Criados e resolvidos nas últimas {{ semanas|length }} semanas</p>
            </div>
        </div>
        {% if teto_semanas %}
        {{ g.grafico_linhas(semanas, linha_criados, linha_resolvidos) }}
        <ul class="legenda">
            <li><span class="legenda-cor serie-criados" aria-hidden="true"></span>Criados</li>
            <li><span class="legenda-cor serie-resolvidos" aria-hidden="true"></span>Resolvidos</li>
        </ul>
        {{ g.tabela_semanas(semanas) }}
        {% else %}
        <p class="estado-vazio">Nenhum chamado nas últimas {{ semanas|length }} semanas.</p>
        {% endif %}
    </section>

    <section class="cartao painel painel-estreito" aria-labelledby="titulo-status">
        <div class="painel-cabecalho">
            <div>
                <h2 class="painel-titulo" id="titulo-status">Status</h2>
                <p class="painel-subtitulo">Situação atual dos chamados do período</p>
            </div>
        </div>
        {% if kpis.total %}
        {{ g.grafico_empilhado(partes_status) }}
        {{ g.tabela_rotulo_valor("Chamados por status", "Status", partes_status) }}
        {% else %}
        <p class="estado-vazio">Nenhum chamado neste período.</p>
        {% endif %}
    </section>

    <section class="cartao painel" aria-labelledby="titulo-setor">
        <div class="painel-cabecalho">
            <div>
                <h2 class="painel-titulo" id="titulo-setor">Por setor</h2>
                <p class="painel-subtitulo">Setores que mais abriram chamados</p>
            </div>
        </div>
        {% if kpis.total %}
        {{ g.grafico_barras(barras_setor) }}
        {{ g.tabela_rotulo_valor("Chamados por setor", "Setor", barras_setor) }}
        {% else %}
        <p class="estado-vazio">Nenhum chamado neste período.</p>
        {% endif %}
    </section>

    <section class="cartao painel" aria-labelledby="titulo-prioridade">
        <div class="painel-cabecalho">
            <div>
                <h2 class="painel-titulo" id="titulo-prioridade">Por prioridade</h2>
                <p class="painel-subtitulo">Distribuição da urgência no período</p>
            </div>
        </div>
        {% if kpis.total %}
        {{ g.grafico_donut(fatias_prioridade) }}
        {{ g.tabela_rotulo_valor("Chamados por prioridade", "Prioridade", fatias_prioridade) }}
        {% else %}
        <p class="estado-vazio">Nenhum chamado neste período.</p>
        {% endif %}
    </section>

    <section class="cartao painel painel-inteiro" aria-labelledby="titulo-recentes">
        <div class="painel-cabecalho">
            <h2 class="painel-titulo" id="titulo-recentes">Chamados recentes</h2>
            <a class="painel-link" href="{{ url_for('chamados.lista_chamados') }}">Ver todos</a>
        </div>
        {% if chamados %}
TABELA_RECENTES        {% else %}
        <p class="estado-vazio">Nenhum chamado registrado ainda.</p>
        {% endif %}
    </section>
</div>
{% endblock %}
'''

icones = {
    "ICONE_TOTAL": ICONE.format('<path d="M4 5h16v14H4z"/><path d="M4 13h4l2 3h4l2-3h4"/>'),
    "ICONE_RESOLVIDOS": ICONE.format('<circle cx="12" cy="12" r="8"/><path d="M8.5 12.5l2.5 2.5 4.5-5"/>'),
    "ICONE_TEMPO": ICONE.format('<circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/>'),
    "ICONE_ABERTO": ICONE.format('<path d="M12 4l9 16H3z"/><path d="M12 10v4"/><path d="M12 17h.01"/>'),
}
for marcador, svg in icones.items():
    novo = novo.replace(marcador, svg)
novo = novo.replace("TABELA_RECENTES", tabela)
arquivo.write_text(novo, encoding="utf-8")
print("dashboard reescrito")
PY
```

- [ ] **Step 5: Rota `/dashboard`**

```bash
cd $HOME/mnt/helpdesk-system && python3 - <<'PY'
import pathlib

arquivo = pathlib.Path("rotas/chamados.py")
texto = arquivo.read_text(encoding="utf-8")

def trocar(antigo, novo):
    global texto
    assert texto.count(antigo) == 1, antigo[:60]
    texto = texto.replace(antigo, novo)

trocar(
    "from armazenamento import enviar_anexo, extensao_valida\n",
    "import graficos\nimport metricas\nfrom armazenamento import enviar_anexo, extensao_valida\n",
)
trocar(
    "from models import Anexo, Chamado, Comentario, Usuario\n",
    "from models import Anexo, Chamado, Comentario, Usuario, obter_data_utc\n",
)

inicio = texto.index('@chamados.route("/dashboard")')
fim = texto.index('@chamados.route("/chamado", methods=["GET", "POST"])')
nova_rota = '''@chamados.route("/dashboard")
@login_required
def dashboard():
    agora = obter_data_utc()
    periodo = metricas.chave_de_periodo_valida(request.args.get("periodo"))
    desde = metricas.inicio_do_periodo(periodo, agora)

    indicadores = metricas.kpis(desde)
    semanas = metricas.evolucao_semanal(agora)
    # As duas séries dividem a mesma escala, senão as linhas não se comparam.
    teto_semanas = max([s["criados"] for s in semanas] + [s["resolvidos"] for s in semanas])

    chamados_recentes = (
        db.session.execute(db.select(Chamado).order_by(Chamado.id.desc()).limit(5))
        .scalars()
        .all()
    )

    return render_template(
        "dashboard.html",
        periodo=periodo,
        periodos=[("7", "7 dias"), ("30", "30 dias"), ("90", "90 dias"), ("tudo", "Tudo")],
        kpis=indicadores,
        tempo_medio=metricas.formatar_duracao(indicadores["tempo_medio"]),
        semanas=semanas,
        teto_semanas=teto_semanas,
        linha_criados=graficos.linha([s["criados"] for s in semanas], teto=teto_semanas),
        linha_resolvidos=graficos.linha([s["resolvidos"] for s in semanas], teto=teto_semanas),
        partes_status=graficos.empilhada(metricas.por_status(desde)),
        barras_setor=graficos.barras(metricas.por_setor(desde)),
        fatias_prioridade=graficos.donut(metricas.por_prioridade(desde)),
        chamados=chamados_recentes,
    )


'''
texto = texto[:inicio] + nova_rota + texto[fim:]
arquivo.write_text(texto, encoding="utf-8")
print("rota atualizada")
PY
```

- [ ] **Step 6: CSS do dashboard**

```bash
cd $HOME/mnt/helpdesk-system && python3 - <<'PY'
import pathlib

SECAO = '''
/* ==============================
   DASHBOARD (visual novo, Fase 1) — KPIs, painéis e gráficos SVG
   Cor dos gráficos sempre por classe + token: .fatia-* define --cor-fatia,
   usado como fill (barra empilhada), stroke (donut) e background (legenda).
   ============================== */
.seletor-periodo {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 4px;
    padding: 4px;
    background: var(--superficie);
    border: 1px solid var(--borda);
    border-radius: var(--raio-pilula);
}

.seletor-periodo a {
    padding: 6px 12px;
    border-radius: var(--raio-pilula);
    color: var(--texto-muted);
    font-size: 13px;
    font-weight: 600;
    text-decoration: none;
    white-space: nowrap;
}

.seletor-periodo a:hover {
    color: var(--texto);
    background: var(--superficie-alt);
}

.seletor-periodo a[aria-current="true"] {
    color: var(--texto-botao);
    background: var(--acento-solido);
}

.seletor-periodo a:focus-visible,
.painel-link:focus-visible {
    outline: 2px solid var(--acento);
    outline-offset: 2px;
}

.cartao {
    background: var(--superficie);
    border: 1px solid var(--borda);
    border-radius: var(--raio-superficie);
    box-shadow: var(--sombra-1);
    transition: box-shadow 0.15s ease, border-color 0.15s ease;
}

.cartao:hover {
    box-shadow: var(--sombra-2);
    border-color: var(--borda-forte);
}

.kpis {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 16px;
    margin-bottom: 16px;
}

.kpi {
    display: grid;
    gap: 4px;
    padding: 18px 20px;
}

.kpi-icone {
    width: 36px;
    height: 36px;
    margin-bottom: 8px;
    display: grid;
    place-items: center;
    border-radius: var(--raio-controle);
    background: var(--acento-suave);
    color: var(--acento);
}

.kpi-icone svg {
    width: 20px;
    height: 20px;
}

.kpi-rotulo {
    font-size: 13px;
    font-weight: 600;
    color: var(--texto-muted);
}

.kpi-valor {
    font-size: 30px;
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -0.02em;
    color: var(--texto);
    font-variant-numeric: tabular-nums;
}

.kpi-detalhe {
    font-size: 12px;
    color: var(--texto-fraco);
}

.dashboard-grade {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 16px;
}

.painel {
    grid-column: span 3;
    min-width: 0;
    padding: 20px;
}

.painel-largo {
    grid-column: span 4;
}

.painel-estreito {
    grid-column: span 2;
}

.painel-inteiro {
    grid-column: 1 / -1;
}

.painel-cabecalho {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;
}

.painel-titulo {
    margin: 0;
    font-size: 16px;
    font-weight: 700;
    text-align: left;
    color: var(--texto);
}

.painel-subtitulo {
    margin-top: 2px;
    font-size: 12px;
    color: var(--texto-fraco);
}

.painel-link {
    font-size: 13px;
    font-weight: 600;
    color: var(--acento);
    text-decoration: none;
    white-space: nowrap;
}

.painel-link:hover {
    text-decoration: underline;
}

.estado-vazio {
    padding: 28px 0;
    text-align: center;
    font-size: 14px;
    color: var(--texto-fraco);
}

.grafico {
    display: block;
    width: 100%;
    height: auto;
}

.grafico-grade {
    stroke: var(--grafico-grade);
    stroke-width: 1;
}

.grafico-eixo {
    fill: var(--texto-fraco);
    font-family: inherit;
    font-size: 11px;
    font-variant-numeric: tabular-nums;
}

.serie {
    fill: none;
    stroke-width: 2.5;
    stroke-linecap: round;
    stroke-linejoin: round;
}

.serie.serie-criados {
    stroke: var(--acento);
}

.serie.serie-resolvidos {
    stroke: var(--sucesso-solido);
}

.grafico .marca {
    stroke: var(--superficie);
    stroke-width: 2;
}

.marca.serie-criados,
.legenda-cor.serie-criados {
    --cor-fatia: var(--acento);
    fill: var(--acento);
}

.marca.serie-resolvidos,
.legenda-cor.serie-resolvidos {
    --cor-fatia: var(--sucesso-solido);
    fill: var(--sucesso-solido);
}

.fatia-aberto { --cor-fatia: var(--erro-texto); }
.fatia-andamento { --cor-fatia: var(--aviso-texto); }
.fatia-resolvido { --cor-fatia: var(--sucesso-texto); }
.fatia-baixa { --cor-fatia: var(--info-texto); }
.fatia-media { --cor-fatia: var(--aviso-texto); }
.fatia-alta { --cor-fatia: var(--prioridade-alta-texto); }
.fatia-critica { --cor-fatia: var(--prioridade-critica-texto); }

.legenda {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    margin: 12px 0 0;
    padding: 0;
    list-style: none;
    font-size: 13px;
    color: var(--texto-muted);
}

.legenda li {
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

.legenda strong {
    color: var(--texto);
    font-variant-numeric: tabular-nums;
}

.legenda-cor {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 3px;
    background: var(--cor-fatia, var(--texto-fraco));
}

.legenda-vertical {
    flex-direction: column;
    margin: 0;
}

.grafico.grafico-empilhado {
    height: 14px;
    border-radius: var(--raio-pilula);
    overflow: hidden;
    background: var(--superficie-alt);
}

.grafico-empilhado rect {
    fill: var(--cor-fatia);
}

.grafico-barras {
    display: grid;
    gap: 10px;
}

.barra-linha {
    display: grid;
    grid-template-columns: minmax(0, 9rem) minmax(0, 1fr) 2.5rem;
    align-items: center;
    gap: 12px;
    font-size: 13px;
}

.barra-rotulo {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--texto-muted);
}

.barra-trilho {
    width: 100%;
    height: 8px;
    border-radius: var(--raio-pilula);
    overflow: hidden;
}

.barra-fundo {
    fill: var(--superficie-alt);
}

.barra-valor {
    fill: var(--acento);
}

.barra-numero {
    text-align: right;
    font-weight: 700;
    color: var(--texto);
    font-variant-numeric: tabular-nums;
}

.donut-bloco {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 24px;
}

.grafico.grafico-donut {
    flex: none;
    width: 160px;
    max-width: 100%;
}

.donut-trilho {
    fill: none;
    stroke: var(--superficie-alt);
    stroke-width: 12;
}

.donut-fatia {
    fill: none;
    stroke: var(--cor-fatia);
    stroke-width: 12;
}

.donut-total {
    fill: var(--texto);
    font-family: inherit;
    font-size: 20px;
    font-weight: 800;
}

.donut-legenda-total {
    fill: var(--texto-fraco);
    font-family: inherit;
    font-size: 8px;
}

@media (max-width: 900px) {
    .kpis {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .dashboard-grade {
        grid-template-columns: minmax(0, 1fr);
    }

    .painel,
    .painel-largo,
    .painel-estreito {
        grid-column: 1 / -1;
    }
}

@media (max-width: 480px) {
    .kpis {
        grid-template-columns: minmax(0, 1fr);
    }
}

@media (prefers-reduced-motion: reduce) {
    .cartao {
        transition: none;
    }
}
'''

arquivo = pathlib.Path("static/css/style.css")
bruto = arquivo.read_bytes().decode("utf-8")
fim_de_linha = "\r\n" if "\r\n" in bruto else "\n"
texto = bruto.replace("\r\n", "\n").rstrip("\n") + "\n" + SECAO
arquivo.write_bytes(texto.replace("\n", fim_de_linha).encode("utf-8"))
print("seção do dashboard acrescentada")
PY
```

- [ ] **Step 7: Rodar e ver passar**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider tests/test_dashboard.py tests/test_topbar.py tests/test_rotas.py -v`
Expected: tudo passa (6 novos em `test_dashboard.py`).

- [ ] **Step 8: Suíte inteira**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider -q`
Expected: 241 passed.

- [ ] **Step 9: Arquivos do commit (o Edu commita)**

`templates/_graficos.html`, `templates/dashboard.html`, `rotas/chamados.py`, `static/css/style.css`, `tests/test_dashboard.py` — mensagem sugerida: `feat(dashboard): mostra KPIs e gráficos por período`

---

### Task 7: Verificação final, contagem de testes e entrega

**Files:**
- Modify: `README.md` (contagem de testes e lista de arquivos da suíte), `docs/index.html` (CRLF), `templates/apresentacao.html`, `templates/recursos.html` — onde o número antigo aparecer
- Modify: `docs/superpowers/specs/2026-09-25-visual-novo-fase1-design.md` (só se algo da implementação divergir do spec)

**Interfaces:**
- Consumes: tudo das Tasks 1–6.
- Produces: suíte verde com contagem atualizada em todo lugar; evidência visual; bloco de comandos para o Edu.

- [ ] **Step 1: Suíte inteira e número final**

Run: `$HOME/venv-helpdesk/bin/python -m pytest -p no:cacheprovider -q`
Expected: `241 passed`. Anotar o número real (N) — se diferente de 241, usar o real daqui em diante.

- [ ] **Step 2: Achar o número antigo**

Run: `cd $HOME/mnt/helpdesk-system && grep -rn "170" --include=*.md --include=*.html . | grep -v "^./venv/" | grep -v "docs/superpowers/"`
Expected: ocorrências em `README.md` ("Suíte com 170 testes", "**170 passed**"), `docs/index.html` (meta description, régua do hero, cartão de qualidade), `templates/apresentacao.html` (`.hero-regua-item`), `templates/recursos.html` (cartão de qualidade). Conferir cada linha: só trocar as que falam da contagem de testes.

- [ ] **Step 3: Atualizar a contagem (preservando CRLF de `docs/index.html`)**

Para cada arquivo listado no Step 2, trocar `170` por N **apenas nas linhas da contagem de testes**, com leitura/escrita em bytes (mesmo padrão dos scripts das tasks anteriores). No `README.md`, trocar também "dividida em cinco arquivos: ..." pela lista atual: `test_app.py`, `test_rotas.py`, `test_api.py`, `test_armazenamento.py`, `test_relatorios.py`, `test_resolvido_em.py`, `test_metricas.py`, `test_graficos.py`, `test_tema.py`, `test_topbar.py` e `test_dashboard.py` ("onze arquivos"), mantendo as descrições que já existem para os cinco primeiros.

Run depois: `grep -rn "170 testes\|170 passed" --include=*.md --include=*.html . | grep -v "^./venv/"`
Expected: nenhuma saída.

- [ ] **Step 4: Evidência visual (execução direta, não delegada)**

Gerar o HTML do dashboard com dados de exemplo pelo cliente de teste do Flask, abrir no Chromium com o `style.css` e tirar screenshot em 1280px e 400px, nos temas escuro e claro. Conferir: topbar sem quebrar, abas roláveis no celular, KPIs 2×2 em tablet e 1 coluna em 400px, gráficos legíveis nos dois temas, nenhuma rolagem horizontal da página. Conferir também `/chamados`, `/login` e `/` (layout antigo com a paleta nova) — nada ilegível.

- [ ] **Step 5: Diff limpo**

Run: `cd $HOME/mnt/helpdesk-system && git --no-optional-locks status --short && git --no-optional-locks diff --ignore-space-at-eol --stat`
Expected: só os arquivos do mapa deste plano. `style.css`, `rotas/api.py`, `tests/test_api.py` e `docs/index.html` sem o arquivo inteiro marcado como alterado (sinal de CRLF perdido).

- [ ] **Step 6: Entregar ao Edu o bloco de comandos**

Seguindo o fluxo dele (um comando por bloco, "Passo 1", "Passo 2"…, sem prompt `PS`, sem marca de geração automatizada): criar a issue da Fase 1 → `git switch main` → `git pull` → `git switch -c feat/visual-novo-fundacao-dashboard` → um `git add` + `git commit` por task com as mensagens sugeridas (Task 7 como `docs: atualiza a contagem de testes para N`, incluindo o spec e este plano em `docs/superpowers/`) → `python -m pytest -v` → `git push -u origin feat/visual-novo-fundacao-dashboard` → `gh pr create` com `Closes #<número da issue>` → passo extra do título sem acento. Fechar com: "confere o CI e o CodeQL, mescla e apaga a branch pelo GitHub, e me manda OK".
