from flask import Blueprint, jsonify, request
from ..extensions import db
from ..models.warehouse import Warehouse
from ..services.auth_service import requires_auth

warehouse_api = Blueprint('warehouse_api', __name__)

# --- RUTA 1: Obtener TODOS los almacenes ---
@warehouse_api.route('/', methods=['GET'], strict_slashes=False)
@requires_auth(required_permission='view:inventory')
def get_warehouses(payload):
    """Devuelve una lista de todos los almacenes."""
    try:
        warehouses = Warehouse.query.order_by(Warehouse.name).all()
        return jsonify([w.to_dict() for w in warehouses])
    except Exception as e:
        return jsonify(error=str(e)), 500

# --- RUTA 2: Crear un nuevo almacén ---
@warehouse_api.route('/', methods=['POST'], strict_slashes=False)
@requires_auth(required_permission='manage:inventory')
def create_warehouse(payload):
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify(error="El campo 'name' es requerido"), 400

    try:
        new_wh = Warehouse(
            name=data['name'],
            location=data.get('location', ''),
            address=data.get('address', ''),
            ubigeo=data.get('ubigeo', '')
        )
        db.session.add(new_wh)
        db.session.commit()
        return jsonify(new_wh.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500

# --- RUTA 3: Actualizar un almacén ---
@warehouse_api.route('/<int:wh_id>', methods=['PUT'])
@requires_auth(required_permission='manage:inventory')
def update_warehouse(wh_id, payload):
    data = request.get_json()
    wh = Warehouse.query.get_or_404(wh_id)

    try:
        wh.name = data.get('name', wh.name)
        wh.location = data.get('location', wh.location)
        wh.address = data.get('address', wh.address)
        wh.ubigeo = data.get('ubigeo', wh.ubigeo)

        db.session.commit()
        return jsonify(wh.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500

# --- RUTA 4: Eliminar un almacén ---
@warehouse_api.route('/<int:wh_id>', methods=['DELETE'])
@requires_auth(required_permission='manage:inventory')
def delete_warehouse(wh_id, payload):
    wh = Warehouse.query.get_or_404(wh_id)

    try:
        db.session.delete(wh)
        db.session.commit()
        return jsonify(success=True, message="Almacén eliminado")
    except Exception as e:
        # Captura errores si el almacén está en uso
        db.session.rollback()
        return jsonify(error=f"No se pudo eliminar: {str(e)}"), 500