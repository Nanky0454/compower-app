import requests
from app import create_app, db
from app.models.treasury import TreasuryTransaction, TreasuryAllocationRender

app = create_app()

def test_create_render():
    with app.app_context():
        # Find an existing transaction to attach the render to
        # We need an EGRESO transaction.
        tx = TreasuryTransaction.query.filter_by(type='EGRESO').first()
        if not tx:
            print("No EGRESO transaction found to test with.")
            return

        print(f"Testing with Transaction ID: {tx.id}")

        # 1. Test creating a simple render without document
        url = f"http://localhost:5000/api/treasury/transactions/{tx.id}/renders"
        # We need a valid token. For this test, we might need to bypass auth or generate a token.
        # Since bypassing auth is hard without changing code, let's try to call the controller logic directly if possible,
        # OR just use the app context to create the model directly and see if it fails at DB level.
        
        print("Attempting to create Render model directly...")
        try:
            # 1. Create Render
            render = TreasuryAllocationRender(
                transaction_id=tx.id,
                amount=10.00,
                description="Test Render Script"
            )
            db.session.add(render)
            db.session.flush()
            
            # 2. Create Document
            # We know doc type 1 exists (Factura)
            from app.models.treasury import TreasuryRenderDocument
            from datetime import date
            
            doc = TreasuryRenderDocument(
                render_id=render.id,
                document_type_id=1,
                series="F001",
                number="123456",
                issuer_ruc="20123456789",
                issuer_name="Test Provider",
                issue_date=date.today(),
                amount=10.00
            )
            db.session.add(doc)
            
            db.session.commit()
            print("Successfully created Render WITH Document directly in DB.")
            
            # Clean up
            db.session.delete(render) # Cascade should delete doc
            db.session.commit()
            print("Cleaned up test render.")
            
        except Exception as e:
            print(f"Error creating Render model: {e}")
            db.session.rollback()

if __name__ == "__main__":
    test_create_render()
