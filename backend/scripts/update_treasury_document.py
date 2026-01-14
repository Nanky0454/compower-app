from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("--- Updating Treasury Schema (Documents) ---")
    
    # Create table if not exists
    try:
        print("Creating 'treasury_transaction_documents' table...")
        db.create_all() # This will create any missing tables defined in models
        print("Table creation check complete.")
    except Exception as e:
        print(f"Error creating table: {e}")
        
    print("--- Schema Update Complete ---")
