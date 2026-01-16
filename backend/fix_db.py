from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("--- 🛠️  AGREGANDO TIPO (OC/OS) A LA BASE DE DATOS ---")

    # Agregamos la columna order_type con valor por defecto 'OC'
    sql = "ALTER TABLE purchase_orders ADD COLUMN order_type VARCHAR(5) DEFAULT 'OC'"

    try:
        db.session.execute(text(sql))
        print(f"✅ Columna 'order_type' agregada con éxito.")
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