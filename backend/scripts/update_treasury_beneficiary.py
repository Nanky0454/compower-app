from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("--- Updating Treasury Schema (Beneficiary) ---")
    
    with db.engine.connect() as connection:
        # Add beneficiary_type
        try:
            print("Adding 'beneficiary_type' column...")
            connection.execute(text("ALTER TABLE treasury_transactions ADD COLUMN beneficiary_type VARCHAR(20)"))
            print("Column 'beneficiary_type' added.")
        except Exception as e:
            if 'duplicate column' in str(e).lower() or 'no such column' not in str(e).lower():
                print(f"Skipping 'beneficiary_type': {e}")
            else:
                print(f"Error adding 'beneficiary_type': {e}")

        # Add beneficiary_provider_id
        try:
            print("Adding 'beneficiary_provider_id' column...")
            connection.execute(text("ALTER TABLE treasury_transactions ADD COLUMN beneficiary_provider_id INTEGER REFERENCES providers(id)"))
            print("Column 'beneficiary_provider_id' added.")
        except Exception as e:
            if 'duplicate column' in str(e).lower() or 'no such column' not in str(e).lower():
                print(f"Skipping 'beneficiary_provider_id': {e}")
            else:
                print(f"Error adding 'beneficiary_provider_id': {e}")

        # Add beneficiary_employee_id
        try:
            print("Adding 'beneficiary_employee_id' column...")
            connection.execute(text("ALTER TABLE treasury_transactions ADD COLUMN beneficiary_employee_id INTEGER REFERENCES employees(id)"))
            print("Column 'beneficiary_employee_id' added.")
        except Exception as e:
            if 'duplicate column' in str(e).lower() or 'no such column' not in str(e).lower():
                print(f"Skipping 'beneficiary_employee_id': {e}")
            else:
                print(f"Error adding 'beneficiary_employee_id': {e}")

        # Add beneficiary_account_id
        try:
            print("Adding 'beneficiary_account_id' column...")
            connection.execute(text("ALTER TABLE treasury_transactions ADD COLUMN beneficiary_account_id INTEGER REFERENCES bank_accounts(id)"))
            print("Column 'beneficiary_account_id' added.")
        except Exception as e:
            if 'duplicate column' in str(e).lower() or 'no such column' not in str(e).lower():
                print(f"Skipping 'beneficiary_account_id': {e}")
            else:
                print(f"Error adding 'beneficiary_account_id': {e}")
        
        connection.commit()

    print("--- Schema Update Complete ---")
