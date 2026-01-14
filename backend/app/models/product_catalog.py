from ..extensions import db

class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255))

    # --- Subcategorías ---
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    subcategories = db.relationship('Category', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')

    # --- Relación con Productos ---
    # Al usar backref='category', SQLAlchemy inyecta automáticamente la propiedad ".category"
    # en la clase Product. Por eso NO debemos definirla manualmente en Product.
    products = db.relationship('Product', backref='category', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'parent_name': self.parent.name if self.parent else None
        }

class UnitMeasure(db.Model):
    __tablename__ = 'unit_measure'

    id = db.Column(db.Integer, primary_key=True)

    # CÓDIGO SUNAT (Ej: ZZ, NIU, KGM)
    sunat_code = db.Column(db.String(5), unique=True, nullable=False)

    # DESCRIPCIÓN (Ej: Servicio, Unidad, Kilos)
    description = db.Column(db.String(100), nullable=False)

    # SIMBOLO COMERCIAL (Ej: SERV, UND, KG)
    symbol = db.Column(db.String(20), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'sunat_code': self.sunat_code,
            'description': self.description,
            'symbol': self.symbol,
            'label': f"{self.sunat_code} - {self.description}"
        }

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    # --- UNIDAD DE MEDIDA (Relación) ---
    # Reemplazamos el campo de texto simple por la FK
    unit_measure_id = db.Column(db.Integer, db.ForeignKey('unit_measure.id'), nullable=True)
    unit_measure = db.relationship('UnitMeasure', backref='products')

    # --- DATOS EXTRA ---
    standard_price = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    location = db.Column(db.Text, nullable=True)

    # --- CATEGORÍA ---
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    # NOTA: No definimos "category = relationship(...)" aquí porque
    # ya está definida en Category con el backref.

    def to_dict(self):
        locations = [loc.strip() for loc in self.location.split(',')] if self.location else []

        return {
            'id': self.id,
            'sku': self.sku,
            'name': self.name,
            'description': self.description,

            # Datos de Unidad de Medida
            'unit_measure_id': self.unit_measure_id,
            'unit_of_measure': self.unit_measure.symbol if self.unit_measure else 'N/A', # Para compatibilidad visual
            'sunat_code': self.unit_measure.sunat_code if self.unit_measure else '',     # Para GRE

            'standard_price': float(self.standard_price),
            'location': locations,

            # Datos de Categoría
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else 'N/A'
        }