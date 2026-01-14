from ..extensions import db

# 1. Esta es la tabla de asociación (muchos-a-muchos)
# Le dice a SQLAlchemy cómo conectar un Rol con un Permiso.
roles_permissions = db.Table('roles_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True)
)

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)

    # 'name' será el rol, ej: 'Admin', 'Usuario'
    name = db.Column(db.String(80), unique=True, nullable=False)

    # 2. Aquí definimos la relación
    # 'permissions' será una lista de objetos Permission
    permissions = db.relationship('Permission', secondary=roles_permissions,
                                  lazy='subquery',
                                  backref=db.backref('roles', lazy=True))