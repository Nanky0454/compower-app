from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("--- 🛠️  CORRIGIENDO CLIENTE EN GRE 37 ---")

    # SQL para actualizar el nombre del cliente
    sql = "UPDATE gre SET cliente_denominacion='ENTEL PERU S.A.' WHERE id=37"

    try:
        # Ejecutamos la consulta
        result = db.session.execute(text(sql))

        # Confirmamos cambios
        db.session.commit()

        # rowcount nos dice cuántas filas fueron afectadas
        if result.rowcount > 0:
            print(f"✅ Se actualizó el cliente a 'ENTEL PERU S.A.' en la guía ID 37.")
        else:
            print(f"⚠️  La sentencia corrió, pero no se encontró el ID 37 (ninguna fila afectada).")

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error al actualizar: {e}")

    print("\n✨ Proceso finalizado.")