from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("--- ACTUALIZANDO TABLAS DE COMPRAS ---")


    try:
        db.session.execute(text("UPDATE stock_transfers SET cost_center_id = 39 WHERE id = 30"))
        print("✅ Bse de datos actualizada, id cambiado a 30")
    except Exception as e:
        print(f"⚠️ no se pudo actualizar: {e}")
    try:
        db.session.commit()
        print("✨ Base de datos actualizada.")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error: {e}")