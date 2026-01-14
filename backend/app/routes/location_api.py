from flask import Blueprint, jsonify, request
from ..extensions import db
from ..models.location import Location
from ..models.provider import Provider
from ..models.cost_center import CostCenter
from ..services.auth_service import requires_auth

location_api = Blueprint('location_api', __name__)

# --- CRUD de Sites (Locations) ---

# [CORREGIDO] Agregado strict_slashes=False para evitar error de Redirect/CORS
@location_api.route('/', methods=['GET'], strict_slashes=False)
@requires_auth(required_permission='view:cost_centers')
def get_locations(payload):
    try:
        # Filtro opcional por proveedor (útil para tu frontend)
        provider_id = request.args.get('provider_id')

        query = Location.query
        if provider_id:
            query = query.filter_by(provider_id=provider_id)

        locations = query.all()
        return jsonify([l.to_dict() for l in locations])
    except Exception as e:
        return jsonify(error=str(e)), 500

# [CORREGIDO] Agregado strict_slashes=False
@location_api.route('/', methods=['POST'], strict_slashes=False)
@requires_auth(required_permission='manage:transfers')
def create_location(payload):
    try:
        data = request.get_json()

        # Validaciones básicas
        # Nota: He quitado 'ruc' de obligatorio estricto si no es crítico para ti,
        # pero si tu modelo lo exige, déjalo.
        if not data.get('name') or not data.get('ubigeo_code'):
            return jsonify(error="Faltan campos obligatorios (name, ubigeo_code)"), 400

        new_location = Location(
            name=data['name'],
            ruc=data.get('ruc', ''), # RUC opcional o vacío si no viene
            address=data.get('address', ''),
            ubigeo_code=data['ubigeo_code'],
            provider_id=data.get('provider_id'),
            cost_center_id=data.get('cost_center_id'),
            status=data.get('status', 'ACTIVE')
        )

        db.session.add(new_location)
        db.session.commit()
        return jsonify(new_location.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500

@location_api.route('/<int:id>', methods=['PUT'])
@requires_auth(required_permission='manage:transfers')
def update_location(id, payload):
    try:
        location = Location.query.get_or_404(id)
        data = request.get_json()

        if 'name' in data: location.name = data['name']
        if 'ruc' in data: location.ruc = data['ruc']
        if 'address' in data: location.address = data['address']
        if 'ubigeo_code' in data: location.ubigeo_code = data['ubigeo_code']
        if 'provider_id' in data: location.provider_id = data['provider_id']
        if 'cost_center_id' in data: location.cost_center_id = data['cost_center_id']
        if 'status' in data: location.status = data['status']

        db.session.commit()
        return jsonify(location.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500

@location_api.route('/<int:id>', methods=['DELETE'])
@requires_auth(required_permission='manage:transfers')
def delete_location(id, payload):
    try:
        location = Location.query.get_or_404(id)
        db.session.delete(location)
        db.session.commit()
        return jsonify(message="Site eliminado correctamente")
    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500