"""Valores fixos do domínio, usados por mais de um módulo.

Ficam isolados aqui para que modelos, rotas e testes leiam sempre a mesma
definição — e para que mudar um limite (o tamanho mínimo de senha, por exemplo)
seja uma edição em um lugar só.
"""

from datetime import timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TIPOS_USUARIO = ("Usuário", "Técnico", "Administrador")
PERFIS_TECNICOS = ("Técnico", "Administrador")
PRIORIDADES = ("Baixa", "Média", "Alta", "Crítica")
STATUS_CHAMADO = ("Aberto", "Em andamento", "Resolvido")

TAMANHO_MINIMO_SENHA = 8

# Throttle da troca de senha: quantas tentativas erradas da senha atual são
# toleradas antes de bloquear, e por quanto tempo o bloqueio dura.
MAX_TENTATIVAS_SENHA = 5
JANELA_BLOQUEIO_SEGUNDOS = 300

# Mesma ideia, aplicada ao login: limita tentativas de força bruta contra uma
# conta antes de existir uma sessão (por isso o throttle abaixo é por e-mail,
# não por usuario_id).
MAX_TENTATIVAS_LOGIN = 5
JANELA_BLOQUEIO_LOGIN_SEGUNDOS = 300

# Lista curta de senhas óbvias. Não substitui uma checagem contra bases de
# vazamentos (ver README), mas barra os casos mais comuns sem depender de rede.
SENHAS_PROIBIDAS = frozenset(
    {
        "12345678", "123456789", "1234567890", "senha123", "password",
        "password1", "qwerty123", "abc12345", "helpdesk", "admin123",
        "12341234", "10203040", "1q2w3e4r", "senhasenha", "mudar123",
    }
)

# O zoneinfo lê o banco de fusos do sistema operacional, e o Windows não tem um.
# O pacote `tzdata` (nos requirements) supre isso, mas se por algum motivo ele
# faltar, cair para um deslocamento fixo de -3h é melhor que derrubar a aplicação
# — o Brasil não adota mais horário de verão desde 2019, então o valor é exato.
try:
    FUSO_EXIBICAO = ZoneInfo("America/Sao_Paulo")
except ZoneInfoNotFoundError:  # pragma: no cover
    FUSO_EXIBICAO = timezone(timedelta(hours=-3))
