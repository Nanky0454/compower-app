from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("--- Adding 'currency' column to 'bank_accounts' table ---")
    try:
        with db.engine.connect() as connection:
            # Check if column exists (SQLite specific check, adjust if using other DB)
            # For simplicity in this environment, we'll try to add it and catch error if exists
            try:
                connection.execute(text("ALTER TABLE bank_accounts ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'PEN'"))
                print("Column 'currency' added successfully.")
            except Exception as e:
                if 'duplicate column name' in str(e).lower():
                    print("Column 'currency' already exists.")
                else:
                    print(f"Error adding column: {e}")
                    
            connection.commit()
    except Exception as e:
        print(f"An error occurred: {e}")

    print("Done.")
