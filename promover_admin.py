from app import app, db, Usuario

email = input("Digite o e-mail do usuário que você quer promover a Administrador: ").strip().lower()

with app.app_context():
    usuario = db.session.execute(
        db.select(Usuario).where(Usuario.email == email)
    ).scalar_one_or_none()

    if usuario is None:
        print(f"Nenhum usuário encontrado com o e-mail '{email}'.")
    else:
        usuario.tipo_usuario = "Administrador"
        db.session.commit()
        print(f"Pronto! {usuario.nome} ({usuario.email}) agora é Administrador.")