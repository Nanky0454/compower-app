from flask import Blueprint, jsonify, request
from ..extensions import db
from ..models.cost_center import CostCenter # <-- Modelo actualizado
from ..models.stock_transfer import StockTransfer, StockTransferItem
from ..models.product_catalog import Product
from ..services.auth_service import requires_auth
from ..models.purchase_order import PurchaseOrder, PurchaseOrderItem
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
        consumption_query_st = db.session.query(
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

        consumption_query_po = db.session.query(
            PurchaseOrder.cost_center_id,
            func.sum(
                cast(PurchaseOrderItem.quantity, db.Numeric(10, 2)) *
                cast(PurchaseOrderItem.unit_price, db.Numeric(10, 2))
            )
        ).join(PurchaseOrderItem, PurchaseOrder.id == PurchaseOrderItem.order_id) \
            .filter(PurchaseOrder.cost_center_id.isnot(None)) \
            .group_by(PurchaseOrder.cost_center_id) \
            .all()

        consumption_map_st = {cc_id: total or Decimal(0) for cc_id, total in consumption_query_st}
        consumption_map_po = {cc_id: total or Decimal(0) for cc_id, total in consumption_query_po}

        print(f"   -> Consumos calculados: {len(consumption_map_st)} y {len(consumption_map_po)}")

        # Paso 2: Obtener Centros
        print("2. Obteniendo lista de CostCenters de la BD...")  # LOG 3
        cost_centers = CostCenter.query.order_by(CostCenter.code.desc()).all()
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
                consumed_decimal_st = consumption_map_st.get(cc.id, Decimal(0))
                consumed_decimal_po = consumption_map_po.get(cc.id, Decimal(0))
                consumed_float = float(consumed_decimal_st) + float(consumed_decimal_po)

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
def get_cost_centers_active(payload):
    try:
        cost_centers = CostCenter.query.order_by(CostCenter.code).filter_by(status='Activo').all()
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


@cost_center_api.route('/<int:cc_id>/movements', methods=['GET'])
@requires_auth(required_permission='view:cost_centers')
def get_cost_center_movements(cc_id, payload):
    try:
        movements = []

        # 1. Buscar Órdenes de Compra (OC)
        orders = PurchaseOrder.query.filter_by(cost_center_id=cc_id).all()

        for oc in orders:
            # Calcular total de la orden
            total = sum(float(i.quantity) * float(i.unit_price) for i in oc.items)
            print(f"Total de ordenes de compra: {total}")
            # Determinar fecha (usar issue_date si existe, sino created_at)
            fecha = oc.created_at
            if hasattr(oc, 'issue_date') and oc.issue_date:
                fecha = oc.issue_date

            movements.append({
                'id': f"OC-{oc.id}",
                'type': oc.order_type,  # Identificador para el icono
                'doc_number': oc.document_number,
                'date': fecha.isoformat() if fecha else None,
                'description': oc.provider.name if oc.provider else "Proveedor Desconocido",
                'amount': total,
                'currency': oc.currency
            })



        # 2. Buscar Salidas de Almacén / Guías (GRE)
        # Asumiendo que StockTransfer tiene un campo cost_center_id
        transfers = StockTransfer.query.filter_by(cost_center_id=cc_id).all()

        for tr in transfers:
            # Calcular valorización de la salida (Cantidad * Precio Estándar del Producto)
            total_valorizado = 0
            for item in tr.items:
                if item.product:
                    total_valorizado += float(item.quantity) * float(item.product.standard_price)
            print(f"Total de GRE: {total_valorizado}") # Moved outside the inner loop
            movements.append({
                'id': f"GRE-{tr.id}",
                'type': 'GRE',  # Identificador para el icono
                'doc_number': getattr(tr, 'guide_number', f"{tr.gre_series}-{tr.gre_number}"),  # Usa número de guía o ID
                'date': tr.transfer_date.isoformat() if tr.transfer_date else tr.created_at.isoformat(),
                'site': tr.destination_external_address,
                'amount': total_valorizado,
                'currency': 'PEN'
            })

        # 3. Ordenar por fecha descendente (lo más reciente primero)
        movements.sort(key=lambda x: x['date'] or '', reverse=True)

        return jsonify(movements)

    except Exception as e:
        print(f"Error getting movements: {e}")
        return jsonify(error=str(e)), 500