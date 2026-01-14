from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Adding correlative column to treasury_allocation_renders...")
    try:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE treasury_allocation_renders ADD COLUMN correlative VARCHAR(20)"))
            conn.commit()
        print("Column added successfully.")
    except Exception as e:
        print(f"Error (column might already exist): {e}")
