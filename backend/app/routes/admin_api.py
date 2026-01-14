from flask import Blueprint, jsonify, request
from ..extensions import db
from ..models.role import Role
from ..models.permission import Permission
# Importaremos un decorador de auth mejorado en el siguiente paso
# Por ahora, usaremos el que ya tenemos
from ..services.auth_service import requires_auth

admin_api = Blueprint('admin_api', __name__)

# --- RUTA 1: Obtener todos los roles y permisos ---
@admin_api.route('/roles')
@requires_auth(required_permission='access:admin_panel')
def get_roles(payload):
    """
    Devuelve una lista de todos los roles con sus permisos
    y una lista de todos los permisos disponibles.
    """
    try:
        # 1. Obtener todos los roles
        roles = Role.query.all()
        roles_data = []
        for role in roles:
            roles_data.append({
                'id': role.id,
                'name': role.name,
                # Creamos una lista solo con los IDs de los permisos del rol
                'permission_ids': [p.id for p in role.permissions]
            })

        # 2. Obtener todos los permisos disponibles
        permissions = Permission.query.all()
        permissions_data = [
            {'id': p.id, 'name': p.name, 'display_name': p.display_name, 'description': p.description}
            for p in permissions
        ]

        # 3. Devolver todo
        return jsonify({
            'roles': roles_data,
            'permissions': permissions_data
        })
    except Exception as e:
        return jsonify(error=str(e)), 500


# --- RUTA 2: Actualizar los permisos de un rol ---
@admin_api.route('/roles/<int:role_id>/permissions', methods=['PUT'])
@requires_auth(required_permission='access:admin_panel')
def update_role_permissions(role_id, payload):
    """
    Actualiza la lista de permisos para un rol específico.
    Espera un JSON con: { "permission_ids": [1, 2, 3] }
    """
    data = request.get_json()
    if not data or 'permission_ids' not in data:
        return jsonify(error="Faltan 'permission_ids'"), 400

    try:
        # 1. Encontrar el rol
        role = Role.query.get_or_404(role_id)

        # 2. Encontrar los objetos de Permiso basados en la lista de IDs
        new_permissions = Permission.query.filter(Permission.id.in_(data['permission_ids'])).all()

        # 3. Asignar la nueva lista de permisos al rol
        role.permissions = new_permissions

        # 4. Guardar en la base de datos
        db.session.commit()

        return jsonify(success=True, message=f"Permisos del rol '{role.name}' actualizados.")

    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500