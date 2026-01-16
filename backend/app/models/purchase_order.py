from ..extensions import db
from datetime import datetime
from .cost_center import CostCenter


# --- 1. Catálogos ---
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


# --- 2. DETALLE (Items) ---
class PurchaseOrderItem(db.Model):
    __tablename__ = 'purchase_order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    product = db.relationship('Product')

    # Campos formato Excel
    invoice_detail_text = db.Column(db.String(255), nullable=False)
    unit_of_measure = db.Column(db.String(20), nullable=True, default='UND')
    quantity = db.Column(db.Numeric(10, 2), nullable=False, default=1.00)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)

    def to_dict(self):
        product_name = self.product.name if self.product else "Producto Manual"
        product_sku = self.product.sku if self.product else "N/A"
        return {
            'id': self.id,
            'id_oc': self.order_id,
            'descripcion': self.invoice_detail_text,
            'unidad': self.unit_of_measure,
            'cant': float(self.quantity),
            'pu': float(self.unit_price),
            'total_line': float(self.quantity * self.unit_price),
            'product_name': product_name,
            'product_sku': product_sku
        }


# --- 3. CABECERA (OC/OS) ---
class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_orders'

    id = db.Column(db.Integer, primary_key=True)
    document_number = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    order_type = db.Column(db.String(5), nullable=False, default='OC')

    # --- Campos Formato Excel ---
    reference = db.Column(db.String(100), nullable=True)
    attention = db.Column(db.String(100), nullable=True)
    scope = db.Column(db.Text, nullable=True)
    payment_condition = db.Column(db.String(100), nullable=True)
    transfer_date = db.Column(db.Date, nullable=True)
    currency = db.Column(db.String(10), default='PEN')

    # --- CAMBIO: UN SOLO CAMPO DE CONTACTO ---
    # Aquí guardaremos el teléfono O el email
    provider_contact = db.Column(db.String(150), nullable=True)

    # --- Relaciones ---
    owner_id = db.Column(db.String(255), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('providers.id'), nullable=False)
    provider = db.relationship('Provider')
    document_type_id = db.Column(db.Integer, db.ForeignKey('document_types.id'), nullable=False)
    document_type = db.relationship('DocumentType')
    status_id = db.Column(db.Integer, db.ForeignKey('order_statuses.id'), nullable=False)
    status = db.relationship('OrderStatus')
    cost_center_id = db.Column(db.Integer, db.ForeignKey('cost_centers.id'), nullable=True)
    cost_center = db.relationship('CostCenter')
    items = db.relationship('PurchaseOrderItem', backref='order', lazy='dynamic', cascade="all, delete-orphan")

    def to_dict(self):
        total = sum(item.quantity * item.unit_price for item in self.items.all())
        t_date = self.transfer_date.strftime('%Y-%m-%d') if self.transfer_date else None

        return {
            'id': self.id,
            'codigo': self.document_number,
            'order_type': self.order_type,
            'tipo_doc_nombre': self.document_type.name if self.document_type else 'N/A',
            'ruc': self.provider.ruc if self.provider else 'N/A',
            'direccion': self.provider.address if self.provider else 'N/A',
            'provider_name': self.provider.name if self.provider else 'N/A',

            # --- CAMBIO EN EL DICCIONARIO ---
            # Devolvemos el campo unificado. Si está vacío, devolvemos 'N/A'
            'contacto': self.provider_contact or 'N/A',

            'id_cc': self.cost_center_id,
            'cost_center_name': self.cost_center.name if self.cost_center else 'N/A',
            'referencia': self.reference,
            'atencion': self.attention,
            'fecha_emision': self.created_at.isoformat(),
            'alcance': self.scope,
            'forma_pago': self.payment_condition,
            'fecha_traslado': t_date,
            'moneda': self.currency,
            'status': self.status.name if self.status else 'N/A',
            'total_amount': float(total),
            'items': [item.to_dict() for item in self.items.all()]
        }