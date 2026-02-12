from app import create_app, db
from sqlalchemy import text

# This script is intended to be run within the Flask application context.
# Example usage:
# with app.app_context():
#     # ... run the functions defined here
#

def add_cost_center_fk_to_treasury_allocation_renders():
    print("--- Adding Foreign Key to treasury_allocation_renders.cost_center_id ---")

    try:
        # Step 1: Identify and nullify invalid cost_center_id values
        # This SQL query checks for cost_center_id values in treasury_allocation_renders
        # that do not exist in the cost_centers table.
        # It then sets those invalid cost_center_id to NULL.
        # This is crucial to ensure referential integrity before adding the FK constraint.
        print("Checking for and nullifying invalid cost_center_id in treasury_allocation_renders...")
        
        # SQL to find invalid IDs
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
            # SQLAlchemy's text() with parameters expects a dictionary for IN clause
            db.session.execute(text(nullify_query), {"invalid_ids": tuple(invalid_cost_center_ids)})
            db.session.commit() # Commit nullification
            print("Invalid cost_center_id values nullified successfully.")
        else:
            print("No invalid cost_center_id values found.")

        # Step 2: Add the foreign key constraint
        print("Attempting to add foreign key constraint on treasury_allocation_renders.cost_center_id...")
        add_fk_query = """
            ALTER TABLE treasury_allocation_renders
            ADD CONSTRAINT fk_treasury_allocation_renders_cost_center_id
            FOREIGN KEY (cost_center_id) REFERENCES cost_centers (id)
            ON DELETE SET NULL;
        """
        db.session.execute(text(add_fk_query))
        db.session.commit()
        print("✅ Foreign key 'fk_treasury_allocation_renders_cost_center_id' added successfully to treasury_allocation_renders.")

    except Exception as e:
        db.session.rollback()
        print(f"❌ Error adding foreign key to treasury_allocation_renders: {e}")

# If you want to integrate this directly into fix_db.py,
# copy the content of the function `add_cost_center_fk_to_treasury_allocation_renders`
# and call it within the `with app.app_context():` block in fix_db.py.
#
# Example of how to call it if it were in fix_db.py:
# with app.app_context():
#     # ... other fix_db.py content
#     add_cost_center_fk_to_treasury_allocation_renders()
#     # ...
