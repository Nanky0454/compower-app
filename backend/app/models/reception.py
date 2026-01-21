from ..extensions import db
from datetime import datetime


# --- CABECERA (La Recepción Global) ---
class ProductReceipt(db.Model):
    __tablename__ = 'product_receipts'

    id = db.Column(db.Integer, primary_key=True)

    # AQUÍ ESTÁ LA FACTURA QUE PEDISTE
    invoice_number = db.Column(db.String(50), nullable=True)

    receipt_date = db.Column(db.DateTime, default=datetime.now)
    created_by = db.Column(db.String(255), nullable=True)  # ID del usuario (Auth0)

    # Relaciones
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)

    purchase_order = db.relationship('PurchaseOrder', backref='receipts')
    warehouse = db.relationship('Warehouse')
    items = db.relationship('ProductReceiptItem', backref='receipt', cascade="all, delete-orphan")


# --- DETALLE (Cada producto recibido) ---
class ProductReceiptItem(db.Model):
    __tablename__ = 'product_receipt_items'

    id = db.Column(db.Integer, primary_key=True)
    receipt_id = db.Column(db.Integer, db.ForeignKey('product_receipts.id'), nullable=False)

    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    location = db.Column(db.String(50), nullable=True)  # Ubicación en almacén (A1, B2...)

    # Para saber a qué item de la OC corresponde (trazabilidad)
    po_item_id = db.Column(db.Integer, db.ForeignKey('purchase_order_items.id'), nullable=True)