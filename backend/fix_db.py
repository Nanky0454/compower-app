from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("--- ACTUALIZANDO TABLAS DE COMPRAS ---")

    # 1. Agregar columnas a purchase_orders
    try:
        db.session.execute(text("ALTER TABLE purchase_orders ADD COLUMN coordinator VARCHAR(150)"))
        print("✅ Columna 'coordinator' agregada.")
    except:
        print("⚠️ Columna 'coordinator' ya existe.")

    try:
        db.session.execute(text("ALTER TABLE purchase_orders ADD COLUMN site VARCHAR(255)"))
        print("✅ Columna 'site' agregada.")
    except:
        print("⚠️ Columna 'site' ya existe.")

    # 2. Agregar columna a purchase_order_items (Para el árbol de servicios)
    try:
        db.session.execute(text("ALTER TABLE purchase_order_items ADD COLUMN group_name VARCHAR(255)"))
        print("✅ Columna 'group_name' agregada a items.")
    except:
        print("⚠️ Columna 'group_name' ya existe.")

    # NUEVO
    try:
        db.session.execute(text("ALTER TABLE purchase_orders ADD COLUMN start_date DATE"))
        print("✅ Columna 'start_date' agregada.")
    except Exception as e:
        print(f"⚠️ Columna 'start_date' ya existe.")

    try:
        db.session.execute(text("ALTER TABLE purchase_orders ADD COLUMN end_date DATE"))
        print("✅ Columna 'end_date' agregada.")
    except Exception as e:
        print(f"⚠️ Columna 'end_date' ya existe.")

    try:
        db.session.execute(text("ALTER TABLE purchase_orders ADD COLUMN commercial_conditions TEXT"))
        print("✅ Columna 'commercial_conditions' agregada.")
    except Exception as e:
        print(f"⚠️ Columna 'commercial_conditions' ya existe.")

    try:
        db.session.execute(text("ALTER TABLE purchase_orders ADD COLUMN footer_note TEXT"))
        print("✅ Columna 'commercial_conditions' agregada.")
    except Exception as e:
        print(f"⚠️ Columna 'footer_note' ya existe.")
    try:
        db.session.execute(text("INSERT INTO roles (name) VALUES ('Logistica')"))
        print("✅ Columna 'commercial_conditions' agregada.")
    except Exception as e:
        print(f"⚠️ Columna 'footer_note' ya existe.")
    try:
        db.session.commit()
        print("✨ Base de datos actualizada.")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error: {e}")