from ..extensions import db

class Location(db.Model):
    __tablename__ = 'locations' # Nombre más genérico que 'sites'

    id = db.Column(db.Integer, primary_key=True)

    # "Nombre": Aquí pones "Almacén Central", "Site T-505", "Oficina San Isidro"
    name = db.Column(db.String(200), nullable=False)


    # --- Datos Fiscales (Para la GRE) ---
    # RUC de la entidad dueña de esa ubicación.
    # - Si es tu Almacén -> TU RUC.
    # - Si es un Site de un operador -> RUC del Operador.
    ruc = db.Column(db.String(11), nullable=False)

    # Dirección exacta (Obligatorio SUNAT)
    address = db.Column(db.String(255), nullable=False)

    # --- Ubicación Geográfica ---
    # Relación con tu tabla de Ubigeos (para saber Distrito/Prov/Dpto)
    ubigeo_code = db.Column(db.String(6), db.ForeignKey('ubigeos.ubigeo_inei'), nullable=False)
    ubigeo = db.relationship('Ubigeo', backref='locations')

    # --- Nuevas Relaciones ---
    provider_id = db.Column(db.Integer, db.ForeignKey('providers.id'), nullable=True)
    provider = db.relationship('Provider', backref='locations')

    cost_center_id = db.Column(db.Integer, db.ForeignKey('cost_centers.id'), nullable=True)
    cost_center = db.relationship('CostCenter', backref='locations')

    # Estado (Activo/Inactivo)
    status = db.Column(db.String(20), default='ACTIVE')

    def to_dict(self):
        ubigeo_display = None
        if self.ubigeo:
            ubigeo_display = f"{self.ubigeo.departamento} / {self.ubigeo.provincia} / {self.ubigeo.distrito}"

        return {
            'id': self.id,
            'name': self.name,
            'ruc': self.ruc,
            'address': self.address,
            'ubigeo_code': self.ubigeo_code,
            'ubigeo_name': ubigeo_display,
            'provider_id': self.provider_id,
            'provider_name': self.provider.name if self.provider else None,
            'cost_center_id': self.cost_center_id,
            'cost_center_name': self.cost_center.name if self.cost_center else None,
            'status': self.status
        }