from app import create_app
from app.extensions import db
from app.models.stock_transfer import StockTransfer

app = create_app()

with app.app_context():
    print("Iniciando limpieza...")

    # Busca las guías
    guias = StockTransfer.query.filter(StockTransfer.id >= 1, StockTransfer.id <= 24).all()

    if not guias:
        print("No se encontraron guías en ese rango.")
    else:
        print(f"Se encontraron {len(guias)} guías. Eliminando...")
        for guia in guias:
            db.session.delete(guia)

        db.session.commit()
        print("✅ ¡Eliminación exitosa!")