from ..extensions import db
from datetime import datetime

class Gre(db.Model):
    __tablename__ = 'gre'

    id = db.Column(db.Integer, primary_key=True)

    # --- 1. Datos Generales del Documento ---
    serie = db.Column(db.String(4), nullable=False)
    numero = db.Column(db.Integer, nullable=False)
    fecha_de_emision = db.Column(db.Date, nullable=False)
    fecha_de_inicio_de_traslado = db.Column(db.Date, nullable=False)

    # --- 2. NUEVOS CAMPOS (Solución a tus errores) ---
    # Estos campos son necesarios para diferenciar Remitente vs Transportista
    gre_type = db.Column(db.String(20), default='remitente', nullable=True)
    remitente_original_ruc = db.Column(db.String(15), nullable=True)
    remitente_original_rs = db.Column(db.String(255), nullable=True)

    # --- 3. Datos del Cliente (Destinatario) ---
    cliente_tipo_de_documento = db.Column(db.String(2), nullable=False)
    cliente_numero_de_documento = db.Column(db.String(15), nullable=False)
    cliente_denominacion = db.Column(db.String(255), nullable=False)

    # --- 4. Datos del Traslado ---
    motivo_de_traslado = db.Column(db.String(2), nullable=False)
    motivo = db.Column(db.String(100), nullable=True)
    peso_bruto_total = db.Column(db.Numeric(12, 2), default=0.00)

    # --- 5. Datos del Transporte y Vehículo ---
    tipo_de_transporte = db.Column(db.String(2), nullable=False)
    transportista_placa_numero = db.Column(db.String(10), nullable=True)
    marca = db.Column(db.String(50), nullable=True)

    # --- 6. Datos del Conductor ---
    conductor_documento_tipo = db.Column(db.String(2), nullable=True)
    conductor_documento_numero = db.Column(db.String(15), nullable=True)
    licencia = db.Column(db.String(20), nullable=True)
    conductor_nombre = db.Column(db.String(100), nullable=True)
    conductor_apellidos = db.Column(db.String(100), nullable=True)

    # --- 7. Puntos de Partida y Llegada ---
    punto_de_partida_ubigeo = db.Column(db.String(6), nullable=False)
    punto_de_partida_direccion = db.Column(db.String(255), nullable=False)

    punto_de_llegada_ubigeo = db.Column(db.String(6), nullable=False)
    punto_de_llegada_direccion = db.Column(db.String(255), nullable=False)

    xml_hash = db.Column(db.String(255), nullable=True)

    # --- Relaciones y Metadatos ---
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    status = db.Column(db.String(20), default='emitido', nullable=False)

    # Relación con items
    items = db.relationship('GreDetail', backref='gre', cascade='all, delete-orphan')

    def to_dict(self):
        """Devuelve el JSON para el frontend o reportes"""
        return {
            "id": self.id,
            "serie": self.serie,
            "numero": self.numero,
            "status": self.status,
            # Incluimos los nuevos campos en la respuesta
            "gre_type": self.gre_type,
            "remitente_original_ruc": self.remitente_original_ruc,
            "remitente_original_rs": self.remitente_original_rs,

            "fecha_de_emision": self.fecha_de_emision.isoformat() if self.fecha_de_emision else None,
            "fecha_de_inicio_de_traslado": self.fecha_de_inicio_de_traslado.isoformat() if self.fecha_de_inicio_de_traslado else None,

            "cliente_tipo_de_documento": self.cliente_tipo_de_documento,
            "cliente_numero_de_documento": self.cliente_numero_de_documento,
            "cliente_denominacion": self.cliente_denominacion,

            "motivo_de_traslado": self.motivo_de_traslado,
            "motivo": self.motivo,
            "peso_bruto_total": float(self.peso_bruto_total),

            "tipo_de_transporte": self.tipo_de_transporte,
            "transportista_placa_numero": self.transportista_placa_numero,
            "marca": self.marca,

            "conductor_documento_tipo": self.conductor_documento_tipo,
            "conductor_documento_numero": self.conductor_documento_numero,
            "licencia": self.licencia,
            "conductor_nombre": self.conductor_nombre,
            "conductor_apellidos": self.conductor_apellidos,

            "punto_de_partida_ubigeo": self.punto_de_partida_ubigeo,
            "punto_de_partida_direccion": self.punto_de_partida_direccion,
            "punto_de_llegada_ubigeo": self.punto_de_llegada_ubigeo,
            "punto_de_llegada_direccion": self.punto_de_llegada_direccion,

            "items": [item.to_dict() for item in self.items]
        }

class GreDetail(db.Model):
    __tablename__ = 'gre_detail'

    id = db.Column(db.Integer, primary_key=True)
    gre_id = db.Column(db.Integer, db.ForeignKey('gre.id'), nullable=False)

    # --- Datos del Producto (Snapshot) ---
    unidad_de_medida = db.Column(db.String(10), nullable=False) # "NIU", "KGM"
    codigo = db.Column(db.String(50), nullable=True) # SKU
    descripcion = db.Column(db.String(255), nullable=False)
    cantidad = db.Column(db.Numeric(12, 2), nullable=False)

    # Relación opcional con tabla products
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)

    def to_dict(self):
        return {
            "unidad_de_medida": self.unidad_de_medida,
            "codigo": self.codigo,
            "descripcion": self.descripcion,
            "cantidad": float(self.cantidad)
        }