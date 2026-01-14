from ..extensions import db
from datetime import datetime


# Modelo 1: La cabecera de la transferencia
class StockTransfer(db.Model):
    __tablename__ = 'stock_transfers'

    id = db.Column(db.Integer, primary_key=True)
    transfer_date = db.Column(db.DateTime, default=datetime.now)

    # --- Origen (Siempre es un almacén interno) ---
    origin_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    origin_warehouse = db.relationship('Warehouse', foreign_keys=[origin_warehouse_id])

    # --- Destino (Puede ser interno O externo) ---
    destination_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)
    destination_warehouse = db.relationship('Warehouse', foreign_keys=[destination_warehouse_id])

    destination_external_address = db.Column(db.String(255), nullable=True)

    status = db.Column(db.String(50), nullable=False, default='Completada')
    user_id = db.Column(db.String(255), nullable=False)

    # --- RELACIÓN CON CENTRO DE COSTOS (La clave del arreglo) ---
    # Coincide con el ALTER TABLE que hiciste
    cost_center_id = db.Column(db.Integer, db.ForeignKey('cost_centers.id'), nullable=True)

    # Usamos string 'CostCenter' para evitar errores de importación circular
    cost_center = db.relationship('CostCenter', backref='stock_transfers')

    # Datos de Guía de Remisión (GRE)
    gre_series = db.Column(db.String(10), nullable=True)
    gre_number = db.Column(db.String(20), nullable=True)
    gre_ticket = db.Column(db.String(50), nullable=True)

    items = db.relationship('StockTransferItem', backref='transfer', cascade="all, delete-orphan")

    def to_dict(self):
        # Lógica segura para evitar errores si el objeto relacionado es None
        origin_name = self.origin_warehouse.name if self.origin_warehouse else 'N/A'
        dest_name = self.destination_warehouse.name if self.destination_warehouse else 'N/A'

        # Validación extra: si cost_center es None, devuelve 'N/A'
        cc_name = 'N/A'
        if self.cost_center:
            cc_name = self.cost_center.name

        return {
            'id': self.id,
            'transfer_date': self.transfer_date.isoformat(),
            'origin_warehouse': origin_name,
            'destination_warehouse': dest_name,
            'destination_external': self.destination_external_address,
            'status': self.status,
            'cost_center': cc_name,  # <-- Ahora seguro
            'items': [item.to_dict() for item in self.items],
            'gre_series': self.gre_series,
            'gre_number': self.gre_number,
            'gre_ticket': self.gre_ticket
        }


# Modelo 2: Los detalles (items) de la transferencia
class StockTransferItem(db.Model):
    __tablename__ = 'stock_transfer_items'

    id = db.Column(db.Integer, primary_key=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey('stock_transfers.id'), nullable=False)

    # nullable=True para mantener historial aunque se borre el producto
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)

    # Snapshots (Guardarán el texto para siempre)
    product_name_snapshot = db.Column(db.String(255), nullable=True)
    product_sku_snapshot = db.Column(db.String(100), nullable=True)

    quantity = db.Column(db.Numeric(10, 2), nullable=False)

    product = db.relationship('Product')

    def to_dict(self):
        # 1. Usar snapshot histórico si existe
        # 2. Si no, usar el nombre actual del producto
        # 3. Si no, poner aviso de eliminado
        real_name = self.product_name_snapshot
        if not real_name and self.product:
            real_name = self.product.name

        real_sku = self.product_sku_snapshot
        if not real_sku and self.product:
            real_sku = self.product.sku

        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': real_name or "Producto Eliminado/N/A",
            'product_sku': real_sku or "N/A",
            'quantity': float(self.quantity)
        }