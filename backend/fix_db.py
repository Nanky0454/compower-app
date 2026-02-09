from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("--- ACTUALIZANDO TABLAS DE COMPRAS ---")

    # Add cost_center_id to product_receipt
    try:
        db.session.execute(text("ALTER TABLE product_receipt ADD COLUMN cost_center_id INTEGER"))
        print("✅ Columna 'cost_center_id' a 'product_receipt' agregada.")
    except Exception as e:
        print(f"⚠️ Columna 'cost_center_id' en 'product_receipt' ya existe o error al agregar: {e}")

    try:
        db.session.execute(text("ALTER TABLE product_receipt ADD CONSTRAINT fk_product_receipt_cost_center FOREIGN KEY (cost_center_id) REFERENCES cost_centers(id)"))
        print("✅ Restricción FOREIGN KEY para 'cost_center_id' en 'product_receipt' agregada.")
    except Exception as e:
        print(f"⚠️ Restricción FOREIGN KEY para 'cost_center_id' en 'product_receipt' ya existe o error al agregar: {e}")

    try:
        db.session.execute(text("ALTER TABLE product_receipt_items ADD COLUMN unit_price NUMERIC(10, 2)"))
        print("✅ Columna 'unit_price' a 'product_receipt_items' agregada.")
    except Exception as e:
        print(f"⚠️ Columna 'unit_price' en 'product_receipt_items' ya existe o error al agregar: {e}")

    try:
        db.session.commit()
        print("✨ Base de datos actualizada.")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error: {e}")