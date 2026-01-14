
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Iniciando reseteo de tablas Ubigeo y relacionadas...")
    
    # Desactivar constraints para poder borrar en cualquier orden (SQLite/Postgres)
    # Nota: Esto es específico para SQLite, si usan Postgres es diferente, pero probaremos con drop_all de tablas específicas.
    
    try:
        # Intentar borrar tablas específicas
        print("Borrando tabla 'locations'...")
        db.session.execute(text("DROP TABLE IF EXISTS locations"))
        
        print("Borrando tabla 'warehouses'...")
        db.session.execute(text("DROP TABLE IF EXISTS warehouses"))
        
        print("Borrando tabla 'ubigeos'...")
        db.session.execute(text("DROP TABLE IF EXISTS ubigeos"))
        
        db.session.commit()
        print("Tablas borradas correctamente.")
        
        print("Recreando todas las tablas...")
        db.create_all()
        print("Tablas recreadas.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.session.rollback()
