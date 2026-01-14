from app import create_app, db
from app.models.treasury import TreasuryAllocationRender, TreasuryRenderDocument

app = create_app()

with app.app_context():
    print("Creating tables...")
    db.create_all()
    print("Tables created.")
