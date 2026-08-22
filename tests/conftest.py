import pytest

from app import create_app
from extensions import db

# Toda a configuração de teste vem daqui, não do ambiente. Antes da fábrica era
# preciso definir DATABASE_URL *antes* de importar o app, porque o objeto
# SQLAlchemy montava a engine no momento da importação — se a ordem escapasse,
# a suíte rodava contra o banco de desenvolvimento e o drop_all do teardown
# apagava dados de verdade. Com `create_app`, essa armadilha deixou de existir.
CONFIG_DE_TESTE = {
    "TESTING": True,
    "SQLALCHEMY_DATABASE_URI": "sqlite://",  # banco em memória
    "SECRET_KEY": "chave-de-teste",
    "WTF_CSRF_ENABLED": False,  # formulários de teste não têm token
    "MAIL_SUPPRESS_SEND": True,
}


@pytest.fixture
def app():
    """Uma aplicação nova, isolada, para cada teste."""
    aplicacao = create_app(CONFIG_DE_TESTE)

    with aplicacao.app_context():
        # Trava de segurança: se por algum motivo a engine apontar para um
        # arquivo, o db.drop_all() do teardown apagaria um banco de verdade.
        assert str(db.engine.url) in ("sqlite://", "sqlite:///:memory:"), (
            f"Os testes iriam rodar contra {db.engine.url}. "
            "Abortando para não destruir um banco real."
        )

        aplicacao.extensions["mail"].suppress = True
        db.create_all()

        yield aplicacao

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    with app.test_client() as cliente:
        yield cliente


@pytest.fixture
def criar_usuario(app):
    """Cria um usuário direto no banco, com o perfil pedido.

    O cadastro público sempre gera perfil "Usuário", então promover alguém a
    Técnico ou Administrador nos testes tem que ser feito por aqui.
    """

    def _criar(nome="Fulano", email="fulano@teste.com", senha="senha-de-teste", tipo="Usuário"):
        from werkzeug.security import generate_password_hash

        from models import Usuario

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
