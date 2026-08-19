import os

# ATENÇÃO: estas variáveis precisam ser definidas ANTES de importar `app`.
#
# O objeto SQLAlchemy é criado no momento em que app.py é importado, e é nesse
# momento que ele lê a URI do banco e monta a engine. A versão anterior deste
# arquivo trocava SQLALCHEMY_DATABASE_URI dentro da fixture, ou seja, tarde
# demais: a engine já apontava para instance/chamados.db, e o db.drop_all() do
# teardown apagava as tabelas do banco REAL de desenvolvimento a cada `pytest`.
os.environ["DATABASE_URL"] = "sqlite://"  # banco em memória
os.environ.setdefault("SECRET_KEY", "chave-de-teste")

import pytest  # noqa: E402

from app import app as flask_app, db  # noqa: E402


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False  # formulários de teste não têm token
    flask_app.config["MAIL_SUPPRESS_SEND"] = True
    flask_app.extensions["mail"].suppress = True

    with flask_app.app_context():
        # Trava de segurança: se por algum motivo a engine apontar para um
        # arquivo, o db.drop_all() do teardown apagaria um banco de verdade.
        assert str(db.engine.url) in ("sqlite://", "sqlite:///:memory:"), (
            f"Os testes iriam rodar contra {db.engine.url}. "
            "Abortando para não destruir um banco real."
        )

        db.create_all()

        with flask_app.test_client() as client:
            yield client

        db.session.remove()
        db.drop_all()


@pytest.fixture
def criar_usuario():
    """Cria um usuário direto no banco, com o perfil pedido.

    O cadastro público sempre gera perfil "Usuário", então promover alguém a
    Técnico ou Administrador nos testes tem que ser feito por aqui.
    """

    def _criar(nome="Fulano", email="fulano@teste.com", senha="senha-de-teste", tipo="Usuário"):
        from werkzeug.security import generate_password_hash

        from app import Usuario

        usuario = Usuario(
            nome=nome,
            email=email,
            senha=generate_password_hash(senha),
            tipo_usuario=tipo,
        )
        db.session.add(usuario)
        db.session.commit()
        return usuario

    return _criar