import os
from app import create_app
from flask_migrate import upgrade as flask_migrate_upgrade # Import upgrade function

def apply_migrations():
    app = create_app()
    with app.app_context():
        print("Applying database migrations...")
        flask_migrate_upgrade()
        print("Database migrations applied successfully.")

if __name__ == '__main__':
    apply_migrations()