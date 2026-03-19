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

    # 4. Add returned_quantity to stock_transfer_items
    try:
        db.session.execute(text("ALTER TABLE stock_transfer_items ADD COLUMN returned_quantity NUMERIC(10, 2) DEFAULT 0;"))
        print("Columna 'returned_quantity' agregada a 'stock_transfer_items'.")
    except Exception as e:
        print(f"No se pudo agregar 'returned_quantity' a 'stock_transfer_items' (posiblemente ya existe o error): {e}")

    # 5. Create stock_returns table
    try:
        db.session.execute(text("DROP TABLE IF EXISTS stock_return_items;"))
        print("Intentando borrar tabla 'stock_return_items' (si existe).")
        db.session.execute(text("DROP TABLE IF EXISTS stock_returns;"))
        print("Intentando borrar tabla 'stock_returns' (si existe).")
        db.session.execute(text("""
            CREATE TABLE stock_returns (
                id INTEGER NOT NULL PRIMARY KEY,
                transfer_id INTEGER NOT NULL,
                return_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_id VARCHAR(255) NOT NULL,
                FOREIGN KEY(transfer_id) REFERENCES stock_transfers (id)
            );
        """))
        print("Tabla 'stock_returns' creada.")
    except Exception as e:
        print(f"No se pudo crear la tabla 'stock_returns' (posiblemente ya existe o error): {e}")

    # 6. Create stock_return_items table
    try:
        db.session.execute(text("""
            CREATE TABLE stock_return_items (
                id INTEGER NOT NULL PRIMARY KEY,
                stock_return_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity NUMERIC(10, 2) NOT NULL,
                FOREIGN KEY(stock_return_id) REFERENCES stock_returns (id),
                FOREIGN KEY(product_id) REFERENCES products (id)
            );
        """))
        print("Tabla 'stock_return_items' creada.")
    except Exception as e:
        print(f"No se pudo crear la tabla 'stock_return_items' (posiblemente ya existe o error): {e}")

    # Confirmar cambios
    try:
        db.session.commit()
        print("Base de datos actualizada.")
    except Exception as e:
        db.session.rollback()
        print(f"Error al hacer commit: {e}")