from ..extensions import db

class Warehouse(db.Model):
    __tablename__ = 'warehouses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    location = db.Column(db.String(100))
    address = db.Column(db.String(255), nullable=True)
    ubigeo = db.Column(db.String(6), db.ForeignKey('ubigeos.ubigeo_inei'), nullable=True)
    ubigeo_rel = db.relationship('Ubigeo', backref='warehouses')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'location': self.location,
            'address': self.address,
            'ubigeo': self.ubigeo, # Devuelve el código (ej. "150140")

            # Nuevo: Devuelve el nombre real sacado de la otra tabla (ej. "SANTIAGO DE SURCO")
            'ubigeo_nombre': self.ubigeo_rel.full_name if self.ubigeo_rel else None
        }