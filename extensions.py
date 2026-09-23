"""Extensões do Flask, criadas sem aplicação.

Instanciar `SQLAlchemy(app)` exigiria o objeto `app` já pronto, e é isso que
cria a dependência circular clássica: o app precisa dos modelos, os modelos
precisam do `db`, o `db` precisaria do app. Criando as extensões vazias aqui e
chamando `init_app()` depois, o ciclo desaparece — e mais de uma aplicação (a de
produção e a dos testes) pode usar as mesmas extensões.
"""

from flask import request
from flask_limiter import Limiter
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
mail = Mail()
csrf = CSRFProtect()


def _chave_por_ip():
    """IP do visitante, usado como chave do rate limit.

    Atrás do proxy da Render, `request.remote_addr` é sempre o IP do próprio
    proxy — todo visitante cairia na mesma chave, e o limite por pessoa
    viraria um limite único para a aplicação inteira. A Render garante (é o
    que respondem no quadro de feedback deles) que o primeiro valor de
    X-Forwarded-For é sempre o IP real de quem conectou, não importa o que o
    cliente tenha colocado nesse cabeçalho antes de chegar no proxy deles —
    por isso ler só o primeiro item já é seguro aqui, sem precisar de
    ProxyFix. Sem o cabeçalho (desenvolvimento local, sem proxy no meio), cai
    para `request.remote_addr`.
    """
    cabecalho = request.headers.get("X-Forwarded-For")
    if cabecalho:
        return cabecalho.split(",")[0].strip()
    return request.remote_addr or "sem-ip"


# Guarda a contagem em memória, não no banco: diferente do Throttle de login
# (que precisa sobreviver a um reinício porque é por e-mail e importa manter
# o bloqueio), este é só uma proteção contra flood básico por IP nas rotas
# públicas — reiniciar zerada a cada deploy é uma perda aceitável, e gravar
# uma linha por requisição pública no banco seria caro à toa.
limiter = Limiter(key_func=_chave_por_ip)

# O Migrate liga o Alembic ao `db`. É ele que passa a existir por trás dos
# comandos `flask db migrate` e `flask db upgrade`, e é quem sabe comparar os
# modelos deste projeto com o esquema que está gravado no banco.
migrate = Migrate()
