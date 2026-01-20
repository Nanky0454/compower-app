from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("--- 🛠️  AGREGANDO COLUMNA ÚNICA DE CONTACTO ---")

    # Solo agregamos la columna nueva.
    # Las viejas (phone/email) se quedarán ahí ocultas para no romper datos antiguos,
    # pero ya no las usaremos.
    sql = "ALTER TABLE purchase_orders ADD COLUMN provider_contact VARCHAR(150)"

    try:
        db.session.execute(text(sql))
        print(f"✅ Columna 'provider_contact' agregada.")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print(f"⚠️  La columna ya existía.")
        else:
            print(f"❌ Error: {e}")

    try:
        db.session.commit()
        print("\n✨ Base de datos actualizada.")
    except Exception as e:
        db.session.rollback()
        print(f"Error final: {e}")