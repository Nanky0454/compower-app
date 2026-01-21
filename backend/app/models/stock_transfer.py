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

    # --- RELACIÓN CON CENTRO DE COSTOS ---
    cost_center_id = db.Column(db.Integer, db.ForeignKey('cost_centers.id'), nullable=True)
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

        cc_name = 'N/A'
        if self.cost_center:
            cc_name = self.cost_center.code

        # --- MODIFICACIÓN: BUSCAR EL ID DE LA GRE ---
        gre_id = None
        # Si la transferencia tiene serie y número, buscamos su ID en la tabla GRE
        if self.gre_series and self.gre_number:
            # Importación local para evitar 'Circular Import Error'
            from .gre import Gre

            # Buscamos la guía que coincida
            gre_record = Gre.query.filter_by(serie=self.gre_series, numero=self.gre_number).first()
            if gre_record:
                gre_id = gre_record.id
        # ---------------------------------------------

        return {
            'id': self.id,
            'transfer_date': self.transfer_date.isoformat(),
            'origin_warehouse': origin_name,
            'destination_warehouse': dest_name,
            'destination_external': self.destination_external_address,
            'status': self.status,
            'cost_center': cc_name,
            'items': [item.to_dict() for item in self.items],

            # Datos GRE
            'gre_id': gre_id,  # <--- AHORA EL FRONTEND RECIBIRÁ ESTE DATO
            'gre_series': self.gre_series,
            'gre_number': self.gre_number,
            'gre_ticket': self.gre_ticket
        }


# Modelo 2: Los detalles (items) de la transferencia (SIN CAMBIOS)
class StockTransferItem(db.Model):
    __tablename__ = 'stock_transfer_items'

    id = db.Column(db.Integer, primary_key=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey('stock_transfers.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    product_name_snapshot = db.Column(db.String(255), nullable=True)
    product_sku_snapshot = db.Column(db.String(100), nullable=True)
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    product = db.relationship('Product')

    def to_dict(self):
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