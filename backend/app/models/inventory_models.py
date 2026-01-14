from ..extensions import db
from datetime import datetime
from sqlalchemy.schema import UniqueConstraint

# TABLA 1: El stock actual
class InventoryStock(db.Model):
    __tablename__ = 'inventory_stock'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)

    product = db.relationship('Product')
    warehouse = db.relationship('Warehouse')

    # Regla: No puede haber dos entradas para el mismo producto en el mismo almacén
    __table_args__ = (UniqueConstraint('product_id', 'warehouse_id', name='_product_warehouse_uc'),)

# TABLA 2: El historial (Kardex)
class InventoryTransaction(db.Model):
    __tablename__ = 'inventory_transactions'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)

    quantity_change = db.Column(db.Numeric(10, 2), nullable=False) # ej. +50 o -10
    new_quantity = db.Column(db.Numeric(10, 2), nullable=False) # El stock resultante

    type = db.Column(db.String(50), nullable=False) # "Recepción de Compra", "Ajuste"
    timestamp = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.String(255), nullable=False) # Auth0 sub
    reference = db.Column(db.String(100), nullable=True) # ej. "GRE: T001-1", "Ajuste: #123"

    # Vínculo a la línea de la orden de compra
    product = db.relationship('Product')
    warehouse = db.relationship('Warehouse')

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'product_name': self.product.name if self.product else 'N/A',
            'product_sku': self.product.sku if self.product else 'N/A',
            'warehouse_name': self.warehouse.name if self.warehouse else 'N/A',
            'type': self.type,
            'reference': self.reference,
            'quantity_change': float(self.quantity_change),
            'new_quantity': float(self.new_quantity)
        }