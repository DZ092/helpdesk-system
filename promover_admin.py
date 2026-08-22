"""Cria ou promove um usuário Administrador pela linha de comando.

O cadastro público do sistema sempre cria contas com o perfil "Usuário" — o
formulário não escolhe o perfil, justamente para que nenhum visitante consiga
criar a própria conta de administrador. Este script é a porta de entrada
controlada: use-o para criar o primeiro administrador ou para promover alguém
sem passar pelo painel.

Uso:
    python promover_admin.py
"""

from getpass import getpass

from werkzeug.security import generate_password_hash

from app import create_app
from extensions import db
from constantes import TAMANHO_MINIMO_SENHA
from models import Usuario


def pedir_senha():
    """Pede a senha duas vezes, sem exibir na tela."""
    while True:
        senha = getpass("Senha (não aparece enquanto você digita): ")
        if len(senha) < TAMANHO_MINIMO_SENHA:
            print(f"A senha precisa ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres.\n")
            continue
        if senha != getpass("Repita a senha: "):
            print("As senhas não conferem. Tente de novo.\n")
            continue
        return senha


def main():
    email = input("E-mail do administrador: ").strip().lower()

    if not email:
        print("Nenhum e-mail informado. Saindo.")
        return

    app = create_app()

    with app.app_context():
        db.create_all()

        usuario = db.session.execute(
            db.select(Usuario).where(Usuario.email == email)
        ).scalar_one_or_none()

        if usuario is None:
            print(f"\nNão existe conta com '{email}'.")
            if input("Quer criar essa conta como Administrador? [s/N]: ").strip().lower() != "s":
                print("Nada foi alterado.")
                return

            nome = input("Nome: ").strip()
            if not nome:
                print("Nome vazio. Nada foi alterado.")
                return

            senha = pedir_senha()

            usuario = Usuario(
                nome=nome,
                email=email,
                senha=generate_password_hash(senha),
                tipo_usuario="Administrador",
            )
            db.session.add(usuario)
            db.session.commit()
            print(f"\nConta criada: {usuario.nome} ({usuario.email}) — Administrador.")
            return

        if usuario.tipo_usuario == "Administrador":
            print(f"\n{usuario.nome} ({usuario.email}) já é Administrador. Nada a fazer.")
            return

        perfil_anterior = usuario.tipo_usuario
        usuario.tipo_usuario = "Administrador"
        db.session.commit()
        print(f"\n{usuario.nome} ({usuario.email}): {perfil_anterior} → Administrador.")


if __name__ == "__main__":
    main()