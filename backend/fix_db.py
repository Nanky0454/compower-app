from app import create_app, db
from sqlalchemy import text

# Inicializamos la aplicación para tener contexto de BD
app = create_app()

with app.app_context():
    print("--- 🛠️  INICIANDO ACTUALIZACIÓN DE ESTRUCTURA (PURCHASE ORDERS) ---")

    # Lista de comandos para agregar las columnas faltantes según tu nuevo Modelo
    cambios_estructura = [
        # Campos de texto simple
        "ALTER TABLE purchase_orders ADD COLUMN reference VARCHAR(100)",
        "ALTER TABLE purchase_orders ADD COLUMN attention VARCHAR(100)",
        "ALTER TABLE purchase_orders ADD COLUMN payment_condition VARCHAR(100)",

        # Campo de texto largo
        "ALTER TABLE purchase_orders ADD COLUMN scope TEXT",

        # Campo de fecha (SQLite lo maneja como DATE o TEXT)
        "ALTER TABLE purchase_orders ADD COLUMN transfer_date DATE",

        # Campo con valor por defecto
        "ALTER TABLE purchase_orders ADD COLUMN currency VARCHAR(10) DEFAULT 'PEN'"
    ]

    # Ejecutamos uno por uno
    for sql in cambios_estructura:
        try:
            db.session.execute(text(sql))
            columna = sql.split("ADD COLUMN")[1].strip().split(" ")[0]
            print(f"✅ Columna agregada: {columna}")
        except Exception as e:
            err_msg = str(e).lower()
            # Si el error es "duplicate column name", significa que ya existe, lo cual es bueno.
            if "duplicate column" in err_msg or "already exists" in err_msg:
                columna = sql.split("ADD COLUMN")[1].strip().split(" ")[0]
                print(f"⚠️  La columna '{columna}' ya existía. (Saltando...)")
            else:
                print(f"❌ Error crítico ejecutando '{sql}': {e}")

    # --- REVISIÓN EXTRA PARA ITEMS (Por si acaso) ---
    # A veces falta 'invoice_detail_text' o 'unit_of_measure' en la tabla items
    print("\n--- Verificando Tabla de Items ---")
    items_cambios = [
        "ALTER TABLE purchase_order_items ADD COLUMN invoice_detail_text VARCHAR(255) DEFAULT 'Item'",
        "ALTER TABLE purchase_order_items ADD COLUMN unit_of_measure VARCHAR(20) DEFAULT 'UND'"
    ]
    for sql in items_cambios:
        try:
            db.session.execute(text(sql))
            print(f"✅ Item columna agregada: {sql.split('ADD COLUMN')[1].split()[0]}")
        except Exception:
            pass  # Ignoramos errores aquí silenciosamente si ya existen

    # Confirmamos los cambios
    try:
        db.session.commit()
        print("\n✨ ¡ÉXITO! La base de datos ha sido actualizada al nuevo formato.")
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Error al guardar los cambios finales: {e}")