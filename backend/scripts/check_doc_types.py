import requests
from app import create_app

app = create_app()

def test_doc_types():
    with app.app_context():
        # We can call the view function directly or use test client
        with app.test_client() as client:
            # We need to mock auth or bypass it.
            # Since requires_auth decorates it, it's hard to bypass without token.
            # But we can check the DB directly which we already did.
            # Let's try to call the function logic directly.
            from app.models.purchase_order import DocumentType
            types = DocumentType.query.all()
            print(f"Found {len(types)} document types:")
            for t in types:
                print(f"{t.id}: {t.name}")

if __name__ == "__main__":
    test_doc_types()
