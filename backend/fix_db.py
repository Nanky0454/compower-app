from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("--- ACTUALIZANDO TABLAS DE COMPRAS ---")

    try:
        db.session.execute(text("DROP TABLE treasury_allocation_renders"))
        print("Tabla eliminada 1")
    except Exception as e:
        print("no se pudo actualizar")

    try:
        db.session.commit()
        print("✨ Base de datos actualizada.")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error: {e}")