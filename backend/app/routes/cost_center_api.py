from flask import Blueprint, jsonify, request
from ..extensions import db
from ..models.cost_center import CostCenter # <-- Modelo actualizado
from ..models.stock_transfer import StockTransfer, StockTransferItem
from ..models.product_catalog import Product
from ..services.auth_service import requires_auth
from sqlalchemy import func, cast
from decimal import Decimal

cost_center_api = Blueprint('cost_center_api', __name__) # <-- Blueprint renombrado


@cost_center_api.route('/with-budget-consumption', methods=['GET'])
@requires_auth(required_permission='view:cost_centers')
def get_cost_centers_with_budget(payload):
    print("--- INICIANDO PETICIÓN DE CENTROS DE COSTOS ---")  # LOG 1
    try:
        # Paso 1: Query de consumo
        print("1. Calculando consumos...")  # LOG 2
        consumption_query = db.session.query(
            StockTransfer.cost_center_id,
            func.sum(
                cast(StockTransferItem.quantity, db.Numeric(10, 2)) *
                cast(Product.standard_price, db.Numeric(10, 2))
            )
        ).join(StockTransferItem, StockTransfer.id == StockTransferItem.transfer_id) \
            .join(Product, StockTransferItem.product_id == Product.id) \
            .filter(StockTransfer.cost_center_id.isnot(None)) \
            .group_by(StockTransfer.cost_center_id) \
            .all()

        consumption_map = {cc_id: total or Decimal(0) for cc_id, total in consumption_query}
        print(f"   -> Consumos calculados: {len(consumption_map)}")

        # Paso 2: Obtener Centros
        print("2. Obteniendo lista de CostCenters de la BD...")  # LOG 3
        cost_centers = CostCenter.query.order_by(CostCenter.code).all()
        print(f"   -> Centros encontrados: {len(cost_centers)}")

        # Paso 3: Combinar
        print("3. Procesando datos...")  # LOG 4
        results = []
        for cc in cost_centers:
            # Depuración por cada fila para encontrar el dato corrupto
            try:
                cc_dict = cc.to_dict()

                # Manejo defensivo del presupuesto
                # Si 'budget' no existe en el objeto, usamos 0.0
                raw_budget = getattr(cc, 'budget', 0.0)
                if raw_budget is None: raw_budget = 0.0

                budget_float = float(raw_budget)

                # Consumo
                consumed_decimal = consumption_map.get(cc.id, Decimal(0))
                consumed_float = float(consumed_decimal)

                cc_dict['budget'] = budget_float  # Aseguramos que vaya al front
                cc_dict['consumed_budget'] = consumed_float
                cc_dict['remaining_budget'] = budget_float - consumed_float

                results.append(cc_dict)
            except Exception as inner_e:
                print(f"   !!! Error procesando CC ID {cc.id}: {inner_e}")
                # Sigue al siguiente para no romper todo
                continue

        print("4. Enviando respuesta...")  # LOG 5
        return jsonify(results)

    except Exception as e:
        import traceback
        print("\n\n############################################")
        print("CRASH FATAL EN /with-budget-consumption")
        print(f"Error: {str(e)}")
        print("Traceback completo:")
        traceback.print_exc()
        print("############################################\n\n")
        return jsonify(error=f"Error fatal servidor: {str(e)}"), 500

# --- RUTA 1: Obtener todos ---
@cost_center_api.route('/', strict_slashes=False)
@requires_auth(required_permission='view:cost_centers') # <-- Permiso actualizado
def get_cost_centers(payload):
    try:
        cost_centers = CostCenter.query.order_by(CostCenter.code).all()
        return jsonify([cc.to_dict() for cc in cost_centers])
    except Exception as e:
        return jsonify(error=str(e)), 500

# --- RUTA 1: Obtener todos ---
@cost_center_api.route('/', strict_slashes=False)
@requires_auth(required_permission='view:cost_centers') # <-- Permiso actualizado
def get_cost_centers_active(payload):
    try:
        cost_centers = CostCenter.query.filter_by(status='Activo').order_by(CostCenter.code).all()
        return jsonify([cc.to_dict() for cc in cost_centers])
    except Exception as e:
        return jsonify(error=str(e)), 500


# --- RUTA 2: Crear uno nuevo ---
@cost_center_api.route('/', methods=['POST'])
@requires_auth(required_permission='create:cost_centers')
def create_cost_center(payload):
    data = request.get_json()
    if not data or not data.get('name') or not data.get('code'):
        return jsonify(error="Los campos 'name' y 'code' son requeridos"), 400

    try:
        owner_id = payload['sub']

        # --- ¡BLOQUE CORREGIDO! ---
        # Ahora leemos todos los campos del formulario (data)
        new_cc = CostCenter(
            code=data['code'],
            name=data['name'],
            description=data.get('description'),
            status=data.get('status', 'Activo'),
            budget=data.get('budget', 0.00), # <-- ¡LÍNEA AÑADIDA!
            owner_id=owner_id
        )
        # ---------------------------

        db.session.add(new_cc)
        db.session.commit()

        return jsonify(new_cc.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500
# --- ¡NUEVA RUTA! 3: Actualizar (para el presupuesto) ---
@cost_center_api.route('/<int:cc_id>', methods=['PUT'])
@requires_auth(required_permission='edit:cost_centers') # <-- Nuevo permiso
def update_cost_center(cc_id, payload):
    """
    Actualiza un centro de costos.
    Permite cambiar nombre, descripción, estado y presupuesto.
    """
    data = request.get_json()
    if not data:
        return jsonify(error="No se recibieron datos"), 400

    try:
        cc = CostCenter.query.get_or_404(cc_id)

        # Actualiza los campos si vienen en el JSON
        if 'name' in data:
            cc.name = data['name']
        if 'description' in data:
            cc.description = data['description']
        if 'status' in data:
            cc.status = data['status']
        if 'budget' in data:
            cc.budget = data['budget']

        db.session.commit()
        return jsonify(cc.to_dict())

    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500