"""Extensões do Flask, criadas sem aplicação.

Instanciar `SQLAlchemy(app)` exigiria o objeto `app` já pronto, e é isso que
cria a dependência circular clássica: o app precisa dos modelos, os modelos
precisam do `db`, o `db` precisaria do app. Criando as extensões vazias aqui e
chamando `init_app()` depois, o ciclo desaparece — e mais de uma aplicação (a de
produção e a dos testes) pode usar as mesmas extensões.
"""

from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
mail = Mail()
csrf = CSRFProtect()
