from flask import Blueprint, jsonify, request, current_app
from ..extensions import db
from ..models.provider import Provider
from ..models.purchase_order import PurchaseOrder, DocumentType, OrderStatus, PurchaseOrderItem
from ..services.auth_service import requires_auth
import requests
from ..models.cost_center import CostCenter
from sqlalchemy.orm import joinedload
from datetime import datetime

purchase_api = Blueprint('purchase_api', __name__)


# --- API 1: La API de SUNAT segura ---
@purchase_api.route('/lookup-provider/<string:ruc>')
@requires_auth(required_permission='create:purchases')
def lookup_provider(ruc, payload):
    # 1. Buscar en BD Local primero
    provider = Provider.query.filter_by(ruc=ruc).first()
    if provider:
        return jsonify(provider.to_dict())

    print(f"Consultando RUC {ruc} a la API externa...")
    try:
        api_key = current_app.config.get('SUNAT_API_KEY', '')
        url = f"https://api.decolecta.com/v1/sunat/ruc?numero={ruc}"

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        # 2. Extracción de datos
        address = data.get('direccion') or data.get('domicilio_fiscal') or data.get('direccion_completa') or ''
        ubigeo = data.get('ubigeo') or ''
        name = data.get('razon_social') or data.get('nombre') or ''

        # 3. Crear Proveedor en BD
        try:
            new_provider = Provider(
                ruc=data['numero_documento'],
                name=name,
                address=address, # Descomenta si tu modelo lo tiene
                # ubigeo=ubigeo
            )
            # Intento seguro de asignar address si el modelo lo soporta
            if hasattr(new_provider, 'address'):
                new_provider.address = address

            db.session.add(new_provider)
            db.session.commit()
            response_data = new_provider.to_dict()

        except Exception as db_err:
            print("Error guardando proveedor, enviando datos temporales:", db_err)
            db.session.rollback()
            response_data = {
                'id': None,
                'document_number': data.get('numero_documento'),
                'ruc': data.get('numero_documento'),
                'name': name,
                'address': address
            }

        # 4. Inyectar datos extra para el frontend
        response_data['address'] = address
        response_data['direccion'] = address
        response_data['ubigeo'] = ubigeo

        return jsonify(response_data)

    except requests.exceptions.RequestException as e:
        return jsonify(error=f"Error conectando a SUNAT: {str(e)}"), 404
    except Exception as e:
        print(f"Error general en lookup: {e}")
        return jsonify(error=str(e)), 500


# --- API 2: Obtener los catálogos ---
@purchase_api.route('/catalogs')
@requires_auth(required_permission='create:purchases')
def get_purchase_catalogs(payload):
    doc_types = DocumentType.query.all()
    statuses = OrderStatus.query.all()
    cost_centers = CostCenter.query.filter_by(status='Activo').all()

    return jsonify({
        'document_types': [d.to_dict() for d in doc_types],
        'statuses': [s.to_dict() for s in statuses],
        'cost_centers': [cc.to_dict() for cc in cost_centers]
    })


# --- API 3: GET Compras ---
@purchase_api.route('/', methods=['GET'], strict_slashes=False)
@requires_auth(required_permission='view:purchases')
def get_purchases(payload):
    try:
        # Usamos joinedload para optimizar la carga del proveedor y estado
        orders = PurchaseOrder.query.options(
            joinedload(PurchaseOrder.provider),
            joinedload(PurchaseOrder.status)
        ).order_by(PurchaseOrder.id.desc()).all()

        return jsonify([o.to_dict() for o in orders])
    except Exception as e:
        return jsonify(error=str(e)), 500


# --- API 4: CREAR Órdenes (POST) ---
@purchase_api.route('/', methods=['POST'], strict_slashes=False)
@requires_auth(required_permission='create:purchases')
def create_purchase(payload):
    data = request.get_json()

    # Validación simple
    if not data.get('provider_id') or not data.get('items'):
        return jsonify(error="Faltan datos obligatorios (Proveedor o Items)"), 400

    try:
        # --- CORRECCIÓN DE FECHA ---
        t_date_str = data.get('transfer_date')
        t_date = None
        if t_date_str:
            # Convertimos el texto 'YYYY-MM-DD' a objeto date real
            try:
                t_date = datetime.strptime(t_date_str, '%Y-%m-%d').date()
            except ValueError:
                # Opcional: Si el formato viene mal
                pass
                # ---------------------------

        new_po = PurchaseOrder(
            document_number=data.get('document_number', 'S/N'),
            owner_id=payload['sub'],
            provider_id=data['provider_id'],
            document_type_id=data['document_type_id'],
            status_id=data['status_id'],
            cost_center_id=data.get('cost_center_id'),

            # --- NUEVOS CAMPOS ---
            reference=data.get('reference'),
            attention=data.get('attention'),
            scope=data.get('scope'),
            payment_condition=data.get('payment_condition'),
            currency=data.get('currency', 'PEN'),
            transfer_date=t_date
            # ---------------------
        )
        db.session.add(new_po)

        # Agregar Items
        for item_data in data['items']:
            new_item = PurchaseOrderItem(
                order=new_po,
                product_id=item_data.get('product_id'),  # Si envías IDs del catálogo
                invoice_detail_text=item_data.get('invoice_detail_text', 'Item'),
                unit_of_measure=item_data.get('um', 'UND'),
                quantity=float(item_data.get('quantity') or 0),
                unit_price=float(item_data.get('unit_price') or 0)
            )
            db.session.add(new_item)

        db.session.commit()
        return jsonify(new_po.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()  # Ver error en consola
        return jsonify(error=f"Error creando orden: {str(e)}"), 500


# --- API 5: GET ONE ---
@purchase_api.route('/<int:order_id>', methods=['GET'])
@requires_auth(required_permission='view:purchases')
def get_purchase_by_id(order_id, payload):
    try:
        order = PurchaseOrder.query.get_or_404(order_id)
        return jsonify(order.to_dict())
    except Exception as e:
        return jsonify(error=str(e)), 500


# --- API 6: GET Receivables ---
@purchase_api.route('/receivable', methods=['GET'])
@requires_auth(required_permission='manage:inventory')
def get_receivable_orders(payload):
    try:
        orders = PurchaseOrder.query.join(OrderStatus).filter(
            OrderStatus.name != 'Recibida',
            OrderStatus.name != 'Anulada'
        ).order_by(PurchaseOrder.id.desc()).all()
        return jsonify([o.to_dict() for o in orders])
    except Exception as e:
        return jsonify(error=str(e)), 500


# --- API 7: Cancel ---
@purchase_api.route('/<int:order_id>/cancel', methods=['PUT'], strict_slashes=False)
@requires_auth(required_permission='create:purchases')
def cancel_purchase(order_id, payload):
    try:
        order = PurchaseOrder.query.get_or_404(order_id)
        if order.status.name == 'Recibida':
            return jsonify(error="No se puede anular una orden recibida."), 400

        anulada_status = OrderStatus.query.filter_by(name='Anulada').first()
        if not anulada_status:
            anulada_status = OrderStatus(name='Anulada')
            db.session.add(anulada_status)
            db.session.commit()

        order.status_id = anulada_status.id
        db.session.commit()
        return jsonify(success=True)
    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500


# --- API 8: Update (PUT) ---
@purchase_api.route('/<int:order_id>', methods=['PUT'], strict_slashes=False)
@requires_auth(required_permission='create:purchases')
def update_purchase(order_id, payload):
    data = request.get_json()
    try:
        order = PurchaseOrder.query.get_or_404(order_id)
        if order.status.name in ['Recibida', 'Anulada']:
            return jsonify(error=f"No se puede editar orden {order.status.name}."), 400

        # Actualizar campos existentes
        if 'document_number' in data: order.document_number = data['document_number']
        if 'status_id' in data: order.status_id = data['status_id']
        if 'cost_center_id' in data: order.cost_center_id = data.get('cost_center_id')
        if 'provider_id' in data: order.provider_id = data['provider_id']
        if 'document_type_id' in data: order.document_type_id = data['document_type_id']

        # --- ACTUALIZAR NUEVOS CAMPOS ---
        if 'reference' in data: order.reference = data['reference']
        if 'attention' in data: order.attention = data['attention']
        if 'scope' in data: order.scope = data['scope']
        if 'payment_condition' in data: order.payment_condition = data['payment_condition']
        if 'currency' in data: order.currency = data['currency']

        if 'transfer_date' in data:
            val = data['transfer_date']
            order.transfer_date = val if val else None
        # --------------------------------

        # Reemplazar Items si vienen en el payload
        if 'items' in data:
            PurchaseOrderItem.query.filter_by(order_id=order.id).delete()
            for item_data in data['items']:
                new_item = PurchaseOrderItem(
                    order=order,
                    product_id=item_data.get('product_id'),
                    invoice_detail_text=item_data.get('invoice_detail_text'),
                    unit_of_measure=item_data.get('um', 'UND'),
                    quantity=float(item_data.get('quantity') or 0),
                    unit_price=float(item_data.get('unit_price') or 0)
                )
                db.session.add(new_item)

        db.session.commit()
        return jsonify(order.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500


# --- API 9: Buscar Proveedores ---
@purchase_api.route('/providers', methods=['GET'])
@requires_auth(required_permission='create:purchases')
def search_providers(payload):
    """
    Busca proveedores.
    - Si 'q' está vacío: Devuelve los primeros 20.
    - Si 'q' tiene texto: Filtra por nombre o RUC.
    """
    q = request.args.get('q', '').strip()

    query = Provider.query

    if q:
        query = query.filter(
            (Provider.name.ilike(f'%{q}%')) |
            (Provider.ruc.like(f'{q}%'))
        )

    providers = query.order_by(Provider.name).limit(20).all()

    return jsonify([p.to_dict() for p in providers])