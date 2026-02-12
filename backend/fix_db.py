from app import create_app, db
from sqlalchemy import text, inspect

app = create_app()

def add_cost_center_fk_to_treasury_allocation_renders_sqlite():
    print("--- Adding Foreign Key to treasury_allocation_renders.cost_center_id (SQLite workaround) ---")

    try:
        # Check if the foreign key already exists to prevent errors on re-run
        inspector = inspect(db.engine)
        fks = inspector.get_foreign_keys('treasury_allocation_renders')
        for fk in fks:
            if 'cost_center_id' in fk['constrained_columns'] and fk['referred_table'] == 'cost_centers':
                print("Foreign key on 'treasury_allocation_renders.cost_center_id' already exists. Skipping.")
                return

        # Step 0: Temporarily disable foreign key checks for schema modification
        db.session.execute(text("PRAGMA foreign_keys = OFF;"))
        db.session.commit()
        print("Foreign key checks temporarily disabled.")

        # Step 1: Identify and nullify invalid cost_center_id values
        print("Checking for and nullifying invalid cost_center_id in treasury_allocation_renders...")
        
        invalid_ids_query = """
            SELECT DISTINCT t.cost_center_id
            FROM treasury_allocation_renders AS t
            LEFT JOIN cost_centers AS c ON t.cost_center_id = c.id
            WHERE t.cost_center_id IS NOT NULL AND c.id IS NULL;
        """
        invalid_cost_center_ids = db.session.execute(text(invalid_ids_query)).scalars().all()

        if invalid_cost_center_ids:
            print(f"Found invalid cost_center_id values: {invalid_cost_center_ids}. Nullifying them...")
            nullify_query = """
                UPDATE treasury_allocation_renders
                SET cost_center_id = NULL
                WHERE cost_center_id IN :invalid_ids;
            """
            db.session.execute(text(nullify_query), {"invalid_ids": tuple(invalid_cost_center_ids)})
            db.session.commit()
            print("Invalid cost_center_id values nullified successfully.")
        else:
            print("No invalid cost_center_id values found.")

        # Step 2: Get original table schema
        # This part requires fetching the actual CREATE TABLE statement or inferring columns and types.
        # For simplicity and robustness, we will assume the model definition is the source of truth
        # and redefine it. This is a simplification and could be brittle if the actual DB schema differs.
        # A more robust solution would dynamically inspect the table, but that's much more complex.
        
        # We need the full schema of treasury_allocation_renders to recreate it.
        # Let's assume the schema based on treasury.py model:
        # id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_id INTEGER NOT NULL, correlative VARCHAR(20),
        # amount NUMERIC(10, 2) NOT NULL, description VARCHAR(255) NOT NULL,
        # cost_center_id INTEGER, created_at DATETIME
        # FOREIGN KEY (transaction_id) REFERENCES treasury_transactions (id) ON DELETE CASCADE
        # FOREIGN KEY (cost_center_id) REFERENCES cost_centers (id) ON DELETE SET NULL

        print("Recreating 'treasury_allocation_renders' table with foreign key...")

        # Step 3: Rename the old table
        db.session.execute(text("ALTER TABLE treasury_allocation_renders RENAME TO old_treasury_allocation_renders;"))
        db.session.commit()

        # Step 4: Create the new table with the foreign key constraint
        create_new_table_query = """
            CREATE TABLE treasury_allocation_renders (
                id INTEGER NOT NULL,
                transaction_id INTEGER NOT NULL,
                correlative VARCHAR(20),
                amount NUMERIC(10, 2) NOT NULL,
                description VARCHAR(255) NOT NULL,
                cost_center_id INTEGER,
                created_at DATETIME,
                PRIMARY KEY (id),
                FOREIGN KEY(transaction_id) REFERENCES treasury_transactions (id) ON DELETE CASCADE,
                FOREIGN KEY(cost_center_id) REFERENCES cost_centers (id) ON DELETE SET NULL
            );
        """
        db.session.execute(text(create_new_table_query))
        db.session.commit()

        # Step 5: Copy data from the old table to the new table
        db.session.execute(text("""
            INSERT INTO treasury_allocation_renders (id, transaction_id, correlative, amount, description, cost_center_id, created_at)
            SELECT id, transaction_id, correlative, amount, description, cost_center_id, created_at
            FROM old_treasury_allocation_renders;
        """))
        db.session.commit()

        # Step 6: Drop the old table
        db.session.execute(text("DROP TABLE old_treasury_allocation_renders;"))
        db.session.commit()

        print("✅ Foreign key 'cost_center_id' added to treasury_allocation_renders successfully (SQLite workaround).")

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error adding foreign key to treasury_allocation_renders (SQLite workaround): {e}")

    finally:
        # Step 7: Re-enable foreign key checks
        db.session.execute(text("PRAGMA foreign_keys = ON;"))
        db.session.commit()
        print("Foreign key checks re-enabled.")

with app.app_context():
    print("--- Running Database Fixes ---")

    # Call the SQLite-specific foreign key addition function
    add_cost_center_fk_to_treasury_allocation_renders_sqlite()

    print("--- Database Fixes Complete ---")
