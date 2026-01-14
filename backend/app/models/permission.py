from ..extensions import db

class Permission(db.Model):
    __tablename__ = 'permissions'
    id = db.Column(db.Integer, primary_key=True)

    # El nombre interno, ej: 'view:modulo_1'
    name = db.Column(db.String(100), unique=True, nullable=False)

    # ¡NUEVO! El nombre para la UI, ej: 'Módulo 1'
    display_name = db.Column(db.String(100), nullable=False)

    # ¡NUEVO! Una descripción para el panel de admin
    description = db.Column(db.String(255), nullable=True)