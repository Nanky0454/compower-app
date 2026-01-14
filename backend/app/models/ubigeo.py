from ..extensions import db

class Ubigeo(db.Model):
    __tablename__ = 'ubigeos'

    id = db.Column(db.Integer, primary_key=True)
    
    # Campos según Excel del usuario
    ubigeo_inei = db.Column(db.String(6), unique=True, nullable=False) # UBIGEO_INEI
    departamento = db.Column(db.String(100), nullable=False)
    provincia = db.Column(db.String(100), nullable=False)
    distrito = db.Column(db.String(100), nullable=False)

    @property
    def full_name(self):
        return f"{self.departamento} / {self.provincia} / {self.distrito}"
    def to_dict(self):
        return {
            'id': self.id,
            'ubigeo_inei': self.ubigeo_inei,
            'departamento': self.departamento,
            'provincia': self.provincia,
            'distrito': self.distrito,
            'full_name': f"{self.departamento} / {self.provincia} / {self.distrito}"
        }