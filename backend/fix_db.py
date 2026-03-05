from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("--- ACTUALIZANDO TABLAS DE COMPRAS ---")

    # 1. Agregar creator_name
    try:
        db.session.execute(text("ALTER TABLE purchase_orders ADD COLUMN creator_name VARCHAR(150);"))
        print("Columna 'creator_name' agregada.")
    except Exception as e:
        print("No se pudo agregar 'creator_name' (posiblemente ya existe).")

    # 2. Agregar creator_role
    try:
        db.session.execute(text("ALTER TABLE purchase_orders ADD COLUMN creator_role VARCHAR(150);"))
        print("Columna 'creator_role' agregada.")
    except Exception as e:
        print("No se pudo agregar 'creator_role' (posiblemente ya existe).")

    # 3. Agregar creator_phone
    try:
        db.session.execute(text("ALTER TABLE purchase_orders ADD COLUMN creator_phone VARCHAR(50);"))
        print("Columna 'creator_phone' agregada.")
    except Exception as e:
        print("No se pudo agregar 'creator_phone' (posiblemente ya existe).")

    # Confirmar cambios
    try:
        db.session.commit()
        print("Base de datos actualizada.")
    except Exception as e:
        db.session.rollback()
        print(f"Error al hacer commit: {e}")