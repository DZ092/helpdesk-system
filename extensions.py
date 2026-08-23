"""Extensões do Flask, criadas sem aplicação.

Instanciar `SQLAlchemy(app)` exigiria o objeto `app` já pronto, e é isso que
cria a dependência circular clássica: o app precisa dos modelos, os modelos
precisam do `db`, o `db` precisaria do app. Criando as extensões vazias aqui e
chamando `init_app()` depois, o ciclo desaparece — e mais de uma aplicação (a de
produção e a dos testes) pode usar as mesmas extensões.
"""

from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
mail = Mail()
csrf = CSRFProtect()

# O Migrate liga o Alembic ao `db`. É ele que passa a existir por trás dos
# comandos `flask db migrate` e `flask db upgrade`, e é quem sabe comparar os
# modelos deste projeto com o esquema que está gravado no banco.
migrate = Migrate()
