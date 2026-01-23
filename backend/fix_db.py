from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("\n--- 🛠️ ACTUALIZANDO ESTRUCTURA DE BASE DE DATOS ---")

    # Lista de columnas que vamos a intentar agregar
    columnas = [
        ("transportista_documento_numero", "VARCHAR(15)"),
        ("transportista_denominacion", "VARCHAR(255)"),
        ("observaciones", "VARCHAR(255)")
    ]

    for col_nombre, col_tipo in columnas:
        try:
            # Intentamos agregar la columna
            sql = f"ALTER TABLE gre ADD COLUMN {col_nombre} {col_tipo}"
            db.session.execute(text(sql))
            print(f"✅ Columna '{col_nombre}' agregada exitosamente.")
        except Exception as e:
            # Si falla (generalmente porque ya existe), lo ignoramos y seguimos
            err_msg = str(e).lower()
            if "duplicate column" in err_msg or "already exists" in err_msg:
                print(f"ℹ️  La columna '{col_nombre}' ya existía.")
            else:
                print(f"⚠️  No se pudo agregar '{col_nombre}': {e}")

    try:
        db.session.commit()
        print("\n✨ Base de datos sincronizada correctamente.")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error al guardar cambios: {e}")