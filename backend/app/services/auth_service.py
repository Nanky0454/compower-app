import json
from functools import wraps
from urllib.request import urlopen
from flask import request
from jose import jwt
from ..extensions import db
from ..models.role import Role
# --- Pega tus valores de Auth0 aquí ---
AUTH0_DOMAIN = 'dev-gforng2dfnavhcdz.us.auth0.com'
API_IDENTIFIER = 'https://api.appcompower.com' # El Audience
ALGORITHMS = ["RS256"]
AUTH0_NAMESPACE = 'https://appcompower.com'
# ------------------------------------


# Clase para los errores de autenticación
class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


# --- Obtener el Token del Header ---
def get_token_auth_header():
    auth = request.headers.get("Authorization", None)
    if not auth:
        raise AuthError({"code": "authorization_header_missing",
                         "description": "Authorization header is expected"}, 401)
    parts = auth.split()
    if parts[0].lower() != "bearer":
        raise AuthError({"code": "invalid_header",
                         "description": "Authorization header must start with 'Bearer'"}, 401)
    elif len(parts) == 1:
        raise AuthError({"code": "invalid_header",
                         "description": "Token not found"}, 401)
    elif len(parts) > 2:
        raise AuthError({"code": "invalid_header",
                         "description": "Authorization header must be 'Bearer token'"}, 401)
    token = parts[1]
    return token


# --- ¡NUEVO! Función para revisar roles en el payload ---
def check_for_roles(required_role, payload):
    """
    Revisa si el rol requerido está en la lista de roles del token.
    """
    roles_key = f"{AUTH0_NAMESPACE}/roles"
    if roles_key not in payload:
        raise AuthError({"code": "invalid_claims",
                         "description": "Roles claim not found in token."}, 401)

    roles = payload[roles_key]
    if not isinstance(roles, list) or required_role not in roles:
        raise AuthError({"code": "unauthorized",
                         "description": "Permission not found."}, 403)  # 403 Forbidden

    return True


# --- ¡ACTUALIZADO! Decorador de Autenticación y Permisos ---
def requires_auth(required_role=None, required_permission=None):
    """
    El decorador que protege las rutas.
    - Si se pasa 'required_role', revisa el rol de Auth0.
    - Si se pasa 'required_permission', revisa los permisos de la BD.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = get_token_auth_header()
            jsonurl = urlopen(f"https://{AUTH0_DOMAIN}/.well-known/jwks.json")
            jwks = json.loads(jsonurl.read())

            try:
                unverified_header = jwt.get_unverified_header(token)
            except jwt.JWTError:
                raise AuthError({"code": "invalid_header",
                                "description": "Unable to parse authentication token."}, 401)

            rsa_key = {}
            for key in jwks["keys"]:
                if key["kid"] == unverified_header["kid"]:
                    rsa_key = {
                        "kty": key["kty"], "kid": key["kid"], "use": key["use"], "n": key["n"], "e": key["e"]
                    }
            if rsa_key:
                try:
                    payload = jwt.decode(
                        token, rsa_key, algorithms=ALGORITHMS,
                        audience=API_IDENTIFIER, issuer=f"https://{AUTH0_DOMAIN}/"
                    )
                except jwt.ExpiredSignatureError:
                    raise AuthError({"code": "token_expired", "description": "Token is expired"}, 401)
                except jwt.JWTClaimsError:
                    raise AuthError({"code": "invalid_claims", "description": "Incorrect claims"}, 401)
                except Exception:
                    raise AuthError({"code": "invalid_header", "description": "Unable to find appropriate key"}, 401)

                # --- REVISIÓN DE ROL (de Auth0) ---
                if required_role:
                    check_for_roles(required_role, payload)

                # --- ¡NUEVO! REVISIÓN DE PERMISO (de la Base de Datos) ---
                if required_permission:
                    # 1. Obtener los roles del token (ej. ['Admin', 'Usuario'])
                    roles_key = f"{AUTH0_NAMESPACE}/roles"
                    if roles_key not in payload:
                        raise AuthError({"code": "invalid_claims", "description": "Roles claim not found."}, 401)
                    auth0_roles = payload[roles_key]

                    # 2. Buscar esos roles en nuestra BD
                    user_roles_in_db = Role.query.filter(Role.name.in_(auth0_roles)).all()

                    # 3. Juntar todos sus permisos en una sola lista
                    all_permissions = set()
                    for role in user_roles_in_db:
                        for perm in role.permissions:
                            all_permissions.add(perm.name)

                    # 4. Revisar si el permiso requerido está en la lista
                    if required_permission not in all_permissions:
                        raise AuthError({"code": "unauthorized",
                                        "description": "Permission not found."}, 403) # 403 Prohibido

                kwargs["payload"] = payload
                return f(*args, **kwargs)

                kwargs["payload"] = payload
                return f(*args, **kwargs)

            raise AuthError({"code": "invalid_header", "description": "Unable to find appropriate key"}, 401)
        return decorated
    return decorator