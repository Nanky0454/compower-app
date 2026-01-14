from ..extensions import db

class CostCenter(db.Model):
    __tablename__ = 'cost_centers' # Renombramos la tabla
    id = db.Column(db.Integer, primary_key=True)

    # Nuevos campos que pediste
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Usamos 'Activo' o 'Inactivo'
    status = db.Column(db.String(50), nullable=False, default='Activo')

    # El presupuesto, tipo numérico, por defecto 0
    budget = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)

    # Lo mantenemos para saber quién lo creó
    owner_id = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        # Actualizamos la función helper
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'budget': float(self.budget), # Convertimos a float para JSON
            'owner_id': self.owner_id
        }