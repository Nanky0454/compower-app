from ..extensions import db
from datetime import datetime
from .cost_center import CostCenter


# --- 1. Catálogos (Sin cambios) ---
class DocumentType(db.Model):
    __tablename__ = 'document_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def to_dict(self): return {'id': self.id, 'name': self.name}

class OrderStatus(db.Model):
    __tablename__ = 'order_statuses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def to_dict(self): return {'id': self.id, 'name': self.name}

# --- 2. DETALLE DE LA ORDEN (Items) ---
class PurchaseOrderItem(db.Model):
    __tablename__ = 'purchase_order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False)

    # Vínculo al Catálogo de Productos (Opcional, para inventario)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    product = db.relationship('Product')

    # --- Campos para tu Formato Excel ---
    invoice_detail_text = db.Column(db.String(255), nullable=False)  # 'descripción' en tu Excel
    unit_of_measure = db.Column(db.String(20), nullable=True, default='UND')  # 'unidad'
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=1.00)  # 'cant'
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)  # 'pu'

    def to_dict(self):
        # Cálculos auxiliares
        product_name = self.product.name if self.product else "Producto Manual"
        product_sku = self.product.sku if self.product else "N/A"

        return {
            'id': self.id,
            'id_oc': self.order_id,

            # Campos exactos de tu Excel
            'descripcion': self.invoice_detail_text,
            'unidad': self.unit_of_measure,
            'cant': float(self.quantity),
            'pu': float(self.unit_price),

            # Extra: Total por línea (Cant * PU)
            'total_line': float(self.quantity * self.unit_price),

            # Datos técnicos del sistema
            'product_name': product_name,
            'product_sku': product_sku
        }

# --- 3. CABECERA DE LA ORDEN (OC) ---
class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_orders'

    id = db.Column(db.Integer, primary_key=True)

    # --- Datos Principales ---
    document_number = db.Column(db.String(50), nullable=False)  # 'código' (ej: 026-001)
    created_at = db.Column(db.DateTime, default=datetime.now)  # 'fecha de emisión'

    # --- NUEVOS CAMPOS (Extraídos de tu Formato Excel) ---
    reference = db.Column(db.String(100), nullable=True)  # 'referencia'
    attention = db.Column(db.String(100), nullable=True)  # 'atención' (Contacto)
    scope = db.Column(db.Text, nullable=True)  # 'alcance' (Texto largo)
    payment_condition = db.Column(db.String(100), nullable=True)  # 'forma de pago'
    transfer_date = db.Column(db.Date, nullable=True)  # 'fecha de traslado'
    currency = db.Column(db.String(10), default='PEN')  # 'tipo de moneda'

    # --- Relaciones ---
    owner_id = db.Column(db.String(255), nullable=False)  # Usuario que creó la OC

    # Proveedor (De aquí sacamos RUC, Dirección y Teléfono)
    provider_id = db.Column(db.Integer, db.ForeignKey('providers.id'), nullable=False)
    provider = db.relationship('Provider')

    # Tipo (OC o OS)
    document_type_id = db.Column(db.Integer, db.ForeignKey('document_types.id'), nullable=False)
    document_type = db.relationship('DocumentType')

    # Estado
    status_id = db.Column(db.Integer, db.ForeignKey('order_statuses.id'), nullable=False)
    status = db.relationship('OrderStatus')

    # Centro de Costos (id_cc)
    cost_center_id = db.Column(db.Integer, db.ForeignKey('cost_centers.id'), nullable=True)
    cost_center = db.relationship('CostCenter')

    # Lista de Items
    items = db.relationship('PurchaseOrderItem', backref='order', lazy='dynamic', cascade="all, delete-orphan")

    def to_dict(self):
        # 1. Calcular el total sumando los items
        total = sum(item.quantity * item.unit_price for item in self.items.all())

        # 2. Formatear fecha para que no de error si está vacía
        t_date = self.transfer_date.strftime('%Y-%m-%d') if self.transfer_date else None

        return {
            'id': self.id,

            # --- Cabecera formato Excel ---
            'codigo': self.document_number,
            'tipo': self.document_type.name if self.document_type else 'N/A',
            'ruc': self.provider.ruc if self.provider else 'N/A',
            'direccion': self.provider.address if self.provider else 'N/A',
            'telefono': self.provider.phone if self.provider else 'N/A',
            'provider_name': self.provider.name if self.provider else 'N/A',

            'id_cc': self.cost_center_id,
            'cost_center_name': self.cost_center.name if self.cost_center else 'N/A',

            # --- Campos nuevos ---
            'referencia': self.reference,
            'atencion': self.attention,
            'fecha_emision': self.created_at.isoformat(),
            'alcance': self.scope,
            'forma_pago': self.payment_condition,
            'fecha_traslado': t_date,
            'moneda': self.currency,

            # --- Totales y Estado ---
            'status': self.status.name if self.status else 'N/A',
            'total_amount': float(total),

            # --- Detalle (Lista de productos) ---
            'items': [item.to_dict() for item in self.items.all()]
        }