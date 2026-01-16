from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("--- 🛠️  ACTUALIZANDO TABLA PROVIDERS ---")

    # Lista de comandos SQL para AGREGAR la columna
    comandos_sql = [
        "ALTER TABLE providers ADD COLUMN address VARCHAR(255)"
    ]

    for sql in comandos_sql:
        try:
            db.session.execute(text(sql))
            print(f"✅ Ejecutado correctamente: {sql}")
        except Exception as e:
            err_msg = str(e).lower()
            # Si dice "duplicate column", es que ya corriste el script antes
            if "duplicate column" in err_msg or "already exists" in err_msg:
                print(f"⚠️  La columna ya existía (No se hizo nada).")
            else:
                print(f"❌ Error al ejecutar: {e}")

    try:
        db.session.commit()
        print("\n✨ ¡LISTO! La columna 'address' ha sido agregada a la tabla 'providers'.")
    except Exception as e:
        db.session.rollback()
        print(f"Error al guardar cambios: {e}")