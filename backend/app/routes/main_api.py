from flask import Blueprint, jsonify
from ..services.auth_service import requires_auth, AUTH0_NAMESPACE
from ..models.role import Role

main_api = Blueprint('main_api', __name__)

# --- RUTA MÓDULO 1 ---
@main_api.route('/message')
@requires_auth(required_permission='view:modulo_1') # <-- CAMBIO
def get_message(payload):
    return jsonify(message="¡Hola desde Módulo 1! (Permiso Concedido)")

# --- RUTA MÓDULO 2 ---
@main_api.route('/entrada2_data')
@requires_auth(required_permission='view:modulo_2') # <-- CAMBIO
def get_entrada2_data(payload):
    return jsonify(message="Datos secretos del Módulo 2.")

# --- RUTA MÓDULO 3 ---
@main_api.route('/entrada3_data')
@requires_auth(required_permission='view:modulo_3') # <-- CAMBIO
def get_entrada3_data(payload):
    return jsonify(message="Reportes confidenciales del Módulo 3.")

# --- ¡NUEVA RUTA! Obtener permisos del usuario logueado ---
@main_api.route('/my-permissions')
@requires_auth() # Solo requiere estar logueado
def get_my_permissions(payload):
    """
    Devuelve una lista de todos los nombres de permisos
    que el usuario logueado posee.
    """
    try:
        # 1. Obtener los roles del token (ej. ['Usuario'])
        roles_key = f"{AUTH0_NAMESPACE}/roles"
        if roles_key not in payload:
            return jsonify(permissions=[]) # Devuelve vacío si no tiene roles

        auth0_roles = payload[roles_key]

        # 2. Buscar esos roles en nuestra BD
        user_roles_in_db = Role.query.filter(Role.name.in_(auth0_roles)).all()

        # 3. Juntar todos sus permisos en una sola lista
        all_permissions = set()
        for role in user_roles_in_db:
            for perm in role.permissions:
                all_permissions.add(perm.name)

        # 4. Devolver la lista
        return jsonify(permissions=list(all_permissions))

    except Exception as e:
        return jsonify(error=str(e)), 500


# --- ¡NUEVA RUTA! Página de Novedades (Home) ---
@main_api.route('/home-data')
@requires_auth(required_permission='view:home')
def get_home_data(payload):
    # En el futuro, podrías sacar esto de una tabla de "Novedades"
    return jsonify(
        title="Novedades de la Versión 0.1",
        content="¡Bienvenido a la nueva versión de CompowerAPP! Hemos implementado un sistema de roles dinámico y un panel de administración."
    )