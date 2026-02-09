from ..extensions import db
from datetime import datetime


# --- CABECERA (La Recepción Global) ---
class ProductReceipt(db.Model):
    __tablename__ = 'product_receipts'

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), nullable=True)
    receipt_date = db.Column(db.DateTime, default=datetime.now)
    created_by = db.Column(db.String(255), nullable=True)

    # --- CAMBIO 1: Permitir que sea NULL (nullable=True) ---
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=True)

    # --- CAMBIO 2: Agregar Proveedor directo (Ya que no habrá OC) ---
    provider_id = db.Column(db.Integer, db.ForeignKey('providers.id'), nullable=True)

    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)

    # Relaciones
    purchase_order = db.relationship('PurchaseOrder', backref='receipts')
    # Agregar relación al proveedor
    provider = db.relationship('Provider')
    warehouse = db.relationship('Warehouse')
    cost_center_id = db.Column(db.Integer, db.ForeignKey('cost_centers.id'), nullable=True) # Nuevo campo
    cost_center = db.relationship('CostCenter') # Nueva relación
    items = db.relationship('ProductReceiptItem', backref='receipt', cascade="all, delete-orphan")

# --- DETALLE (Cada producto recibido) ---
class ProductReceiptItem(db.Model):
    __tablename__ = 'product_receipt_items'

    id = db.Column(db.Integer, primary_key=True)
    receipt_id = db.Column(db.Integer, db.ForeignKey('product_receipts.id'), nullable=False)

    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=0.0)
    location = db.Column(db.String(50), nullable=True)  # Ubicación en almacén (A1, B2...)

    # Para saber a qué item de la OC corresponde (trazabilidad)
    po_item_id = db.Column(db.Integer, db.ForeignKey('purchase_order_items.id'), nullable=True)

    product = db.relationship('Product')