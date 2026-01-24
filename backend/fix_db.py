# Guardar como backend/add_obs.py
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("--- MODIFICAR DATO ---")

    try:
        sql = "UPDATE stock_tranfers SET cost_center_id=115 WHERE gre_number = '1162'"
        db.session.execute(text(sql))
        print("CORRECTO")
    except Exception as e:
        # Si ya existe, nos avisará
        print(f"Aviso: {e}")

    try:
        db.session.commit()
        print("Cambios guardados.")
    except Exception as e:
        db.session.rollback()
        print(f"Error commit: {e}")