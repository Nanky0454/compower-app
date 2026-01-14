from ..extensions import db

class Provider(db.Model):
    __tablename__ = 'providers'
    id = db.Column(db.Integer, primary_key=True)
    ruc = db.Column(db.String(11), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    # Aquí se podrían añadir más datos: dirección, teléfono, etc.

    def to_dict(self):
        return {'id': self.id, 'ruc': self.ruc, 'name': self.name}