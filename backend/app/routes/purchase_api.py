import base64
import json
from flask import Blueprint, jsonify, request, current_app, send_file, render_template
from weasyprint import HTML
from ..extensions import db
from ..models.provider import Provider
from ..models.purchase_order import PurchaseOrder, DocumentType, OrderStatus, PurchaseOrderItem
from ..services.auth_service import requires_auth
import requests
from ..models.cost_center import CostCenter
from sqlalchemy.orm import joinedload
from datetime import datetime
import os
import io
from sqlalchemy import func

purchase_api = Blueprint('purchase_api', __name__)


# --- HELPER: Parseo de Fechas ---
def parse_date(date_string):
    if not date_string:
        return None
    try:
        return datetime.strptime(date_string, '%Y-%m-%d').date()
    except ValueError:
        return None


# --- APIs de Lookup y Catálogos (Sin cambios) ---
@purchase_api.route('/lookup-provider/<string:ruc>')
@requires_auth(required_permission='create:purchases')
def lookup_provider(ruc, payload):
    # ... (Mismo código de siempre) ...
    provider = Provider.query.filter_by(ruc=ruc).first()
    if provider: return jsonify(provider.to_dict())
    try:
        api_key = current_app.config.get('SUNAT_API_KEY', '')
        url = f"https://api.decolecta.com/v1/sunat/ruc?numero={ruc}"
        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        address = data.get('direccion') or data.get('domicilio_fiscal') or ''
        ubigeo = data.get('ubigeo') or ''
        name = data.get('razon_social') or data.get('nombre') or ''
        try:
            new_provider = Provider(ruc=data['numero_documento'], name=name, address=address)
            db.session.add(new_provider)
            db.session.commit()
            response_data = new_provider.to_dict()
        except:
            db.session.rollback()
            response_data = {'id': None, 'ruc': data.get('numero_documento'), 'name': name, 'address': address}
        response_data['address'] = address
        response_data['direccion'] = address
        response_data['ubigeo'] = ubigeo
        return jsonify(response_data)
    except Exception as e:
        return jsonify(error=str(e)), 500


@purchase_api.route('/catalogs')
@requires_auth(required_permission='create:purchases')
def get_purchase_catalogs(payload):
    return jsonify({
        'document_types': [d.to_dict() for d in DocumentType.query.all()],
        'statuses': [s.to_dict() for s in OrderStatus.query.all()],
        'cost_centers': [cc.to_dict() for cc in CostCenter.query.filter_by(status='Activo').order_by(CostCenter.code.desc()).all()]
    })


@purchase_api.route('/', methods=['GET'], strict_slashes=False)
@requires_auth(required_permission='view:purchases')
def get_purchases(payload):
    try:
        orders = PurchaseOrder.query.options(
            joinedload(PurchaseOrder.provider),
            joinedload(PurchaseOrder.status),
            joinedload(PurchaseOrder.cost_center)
        ).order_by(PurchaseOrder.document_number.desc()).all()
        return jsonify([o.to_dict() for o in orders])
    except Exception as e:
        return jsonify(error=str(e)), 500


# --- API CREAR ---
@purchase_api.route('/', methods=['POST'], strict_slashes=False)
@requires_auth(required_permission='create:purchases')
def create_purchase(payload):
    data = request.get_json()
    if not data.get('provider_id') or not data.get('items'):
        return jsonify(error="Faltan datos obligatorios"), 400

    try:
        # Fecha emisión
        created_at_val = datetime.now()
        if data.get('issue_date'):
            try:
                issue_dt = datetime.strptime(data.get('issue_date'), '%Y-%m-%d')
                created_at_val = issue_dt.replace(hour=datetime.now().hour, minute=datetime.now().minute)
            except:
                pass

        new_po = PurchaseOrder(
            document_class=data.get('document_class', 'Factura'),
            document_number=data.get('document_number', 'S/N'),
            created_at=created_at_val,
            owner_id=payload['sub'],
            provider_id=data['provider_id'],
            document_type_id=data['document_type_id'],
            status_id=data['status_id'],
            cost_center_id=data.get('cost_center_id'),
            order_type=data.get('order_type', 'OC'),
            reference=data.get('reference'),
            attention=data.get('attention'),
            provider_contact=data.get('provider_contact'),
            coordinator=data.get('coordinator'),
            site=data.get('site'),
            scope=data.get('scope'),
            payment_condition=data.get('payment_condition'),
            currency=data.get('currency', 'PEN'),

            # Campos Nuevos
            commercial_conditions=data.get('commercial_conditions'),
            footer_note=data.get('footer_note'),

            transfer_date=parse_date(data.get('transfer_date')),
            start_date=parse_date(data.get('start_date')),
            end_date=parse_date(data.get('end_date')),
        )
        db.session.add(new_po)

        for item_data in data['items']:
            new_item = PurchaseOrderItem(
                order=new_po,
                product_id=item_data.get('product_id'),
                group_name=item_data.get('group_name'),
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
        return jsonify(error=str(e)), 500


@purchase_api.route('/<int:order_id>', methods=['GET'])
@requires_auth(required_permission='view:purchases')
def get_purchase_by_id(order_id, payload):
    try:
        return jsonify(PurchaseOrder.query.get_or_404(order_id).to_dict())
    except Exception as e:
        return jsonify(error=str(e)), 500


# --- API UPDATE ---
@purchase_api.route('/<int:order_id>', methods=['PUT'], strict_slashes=False)
@requires_auth(required_permission='create:purchases')
def update_purchase(order_id, payload):
    data = request.get_json()
    try:
        order = PurchaseOrder.query.get_or_404(order_id)
        if order.status.name in ['Recibida', 'Anulada']:
            return jsonify(error="No se puede editar orden cerrada."), 400

        if 'document_class' in data: order.document_class = data['document_class']
        if 'document_number' in data: order.document_number = data['document_number']
        if 'status_id' in data: order.status_id = data['status_id']
        if 'cost_center_id' in data: order.cost_center_id = data.get('cost_center_id')
        if 'provider_id' in data: order.provider_id = data['provider_id']
        if 'order_type' in data: order.order_type = data['order_type']
        if 'coordinator' in data: order.coordinator = data['coordinator']
        if 'site' in data: order.site = data['site']
        if 'reference' in data: order.reference = data['reference']
        if 'attention' in data: order.attention = data['attention']
        if 'provider_contact' in data: order.provider_contact = data['provider_contact']
        if 'scope' in data: order.scope = data['scope']
        if 'payment_condition' in data: order.payment_condition = data['payment_condition']
        if 'currency' in data: order.currency = data['currency']

        # Actualizar campos nuevos
        if 'commercial_conditions' in data: order.commercial_conditions = data['commercial_conditions']
        if 'footer_note' in data: order.footer_note = data['footer_note']

        # Actualizar fecha emisión
        if 'issue_date' in data and data['issue_date']:
            try:
                issue_dt = datetime.strptime(data['issue_date'], '%Y-%m-%d')
                order.created_at = issue_dt.replace(hour=datetime.now().hour, minute=datetime.now().minute)
            except:
                pass

        if 'transfer_date' in data: order.transfer_date = parse_date(data['transfer_date'])
        if 'start_date' in data: order.start_date = parse_date(data['start_date'])
        if 'end_date' in data: order.end_date = parse_date(data['end_date'])

        if 'items' in data:
            PurchaseOrderItem.query.filter_by(order_id=order.id).delete()
            for item_data in data['items']:
                new_item = PurchaseOrderItem(
                    order=order,
                    product_id=item_data.get('product_id'),
                    group_name=item_data.get('group_name'),
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


# --- API 9: Search Providers ---
@purchase_api.route('/providers', methods=['GET'])
@requires_auth(required_permission='create:purchases')
def search_providers(payload):
    q = request.args.get('q', '').strip()
    query = Provider.query
    if q:
        query = query.filter((Provider.name.ilike(f'%{q}%')) | (Provider.ruc.like(f'{q}%')))
    providers = query.order_by(Provider.name).limit(20).all()
    return jsonify([p.to_dict() for p in providers])

@purchase_api.route('/providerslist', methods=['GET'])
@requires_auth(required_permission='create:purchases')
def get_providers(payload):
    """Devuelve una lista de todas los proveedores."""
    try:
        providers = Provider.query.order_by(Provider.name).all()
        return jsonify([p.to_dict() for p in providers])
    except Exception as e:
        return jsonify(error=str(e)), 500


@purchase_api.route('/next-correlative/<string:series>', methods=['GET'])
@requires_auth(required_permission='create:purchases')
def get_next_correlative(series, payload):
    try:
        last_order = PurchaseOrder.query.filter(
            PurchaseOrder.document_number.like(f"{series}-%")
        ).order_by(PurchaseOrder.id.desc()).first()

        if last_order:
            try:
                parts = last_order.document_number.split('-')
                if len(parts) == 2:
                    last_num = int(parts[1])
                    return jsonify({'next_number': last_num + 1})
            except ValueError:
                pass
        return jsonify({'next_number': 1})

    except Exception as e:
        return jsonify(error=str(e)), 500


# --- API 6: GET Receivables ---
@purchase_api.route('/receivable', methods=['GET'])
@requires_auth(required_permission='manage:inventory')
def get_receivable_orders(payload):
    try:
        orders = PurchaseOrder.query.options(
            joinedload(PurchaseOrder.provider),
            joinedload(PurchaseOrder.cost_center),
            joinedload(PurchaseOrder.status)
        ).join(OrderStatus).filter(
            OrderStatus.name == 'Aprobada',
            PurchaseOrder.order_type == 'OC'
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


@purchase_api.route('/<int:order_id>/pdf', methods=['GET'])
@requires_auth(required_permission='view:purchases')
def download_purchase_pdf(order_id, payload):
    order = PurchaseOrder.query.get_or_404(order_id)

    logo_path = os.path.join(current_app.instance_path, 'logo_v2.png')
    logo_b64 = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as image_file:
            logo_b64 = base64.b64encode(image_file.read()).decode('utf-8')

    # --- CONDICIONES DINÁMICAS ---

    # 1. Fecha Dinámica
    if order.order_type == 'OS' and order.start_date:
        f_inicio = order.start_date.strftime('%d/%m/%Y')
        f_fin = order.end_date.strftime('%d/%m/%Y') if order.end_date else '...'
        texto_fecha = f"Plazo de ejecución: Del {f_inicio} al {f_fin}"
    else:
        f_traslado = order.transfer_date.strftime('%d/%m/%Y') if order.transfer_date else '-'
        texto_fecha = f"Fecha de traslado y ejecución: {f_traslado}"

    # 2. Lista Base (Forma de pago, Fecha, Moneda)
    condiciones = [
        f"Forma de Pago: {order.payment_condition or '-'}",
        texto_fecha,
        f"Tipo de moneda: {order.currency}"
    ]

    # 3. Agregar condiciones guardadas (Penalidad + Lista Extra)
    if order.commercial_conditions:
        try:
            extra_conditions = json.loads(order.commercial_conditions)
            if isinstance(extra_conditions, list):
                condiciones.extend(extra_conditions)
        except:
            pass
    else:
        # Fallback (solo si no hay nada guardado)
        condiciones.append("Penalidad: 5% por día de atraso...")

        # 4. Procesar Footer Note (Notas Legales)
    notas_legales = []
    if order.footer_note:
        notas_legales = order.footer_note.split('\n')  # Convertir saltos de línea a lista

    # --- ITEMS ---
    items_data = []
    total_neto = 0
    for item in order.items:
        subtotal = float(item.quantity) * float(item.unit_price)
        total_neto += subtotal
        items_data.append({
            'descripcion': item.invoice_detail_text,
            'unidad': item.unit_of_measure,
            'cantidad': float(item.quantity),
            'pu': float(item.unit_price),
            'total': subtotal,
            'grupo': item.group_name
        })

    igv = 0
    if order.document_class == 'Factura':
        igv = total_neto * 0.18
    total_gen = total_neto + igv

    alcance_data = order.scope
    try:
        if alcance_data and alcance_data.strip().startswith('{'):
            alcance_data = json.loads(alcance_data)
    except:
        pass

    context = {
        'document_class': order.document_class,
        'logo_b64': logo_b64,
        'titulo_doc': "ORDEN DE SERVICIO" if order.order_type == 'OS' else "ORDEN DE COMPRA",
        'tipo': order.order_type,
        'codigo': order.document_number,
        'proveedor_nombre': order.provider.name,
        'proveedor_direccion': (order.provider.address or '-')[:60],
        'proveedor_ruc': order.provider.ruc,
        'contacto': order.provider_contact or '-',
        'referencia': order.reference or '-',
        'atencion': order.attention or '-',
        'cc_codigo': order.cost_center.code if order.cost_center else '-',
        'coordinador': order.coordinator or '-',
        'site': order.site or '-',
        'fecha_emision': order.created_at.strftime('%d/%m/%Y'),
        'items': items_data,
        'alcance': alcance_data,
        'simbolo': 'S/.' if order.currency == 'PEN' else '$',
        'subtotal': total_neto,
        'igv': igv,
        'total': total_gen,
        'condiciones': condiciones,
        'notas_legales': notas_legales  # <--- Pasamos las notas
    }

    html_string = render_template('purchase_order_weasy.html', **context)
    pdf_bytes = HTML(string=html_string).write_pdf()

    safe_name = str(order.document_number).replace('/', '-')
    return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf', as_attachment=True,
                     download_name=f"Orden_{safe_name}.pdf")


@purchase_api.route('/aprobar/<int:order_id>', methods=['POST'])
@requires_auth(required_permission='create:purchases')
def aprobar_orden(payload, order_id):
        # Nota: Aquí quizás no sea necesario ser estrictamente 'Admin',
        # a veces un 'Gerente' o 'Jefe de Compras' también puede aprobar.
        # Pero mantengo la lógica de Admin de tu ejemplo.

        NAMESPACE = 'https://appcompower.com'
        roles = payload.get(f'{NAMESPACE}/roles', [])
        is_admin = 'Admin' in roles or 'Logistica' in roles

        if not is_admin:
            return jsonify({"error": "ACCESO DENEGADO: Solo los administradores pueden aprobar órdenes."}), 403

        try:
            order = PurchaseOrder.query.get_or_404(order_id)

            current_status = OrderStatus.query.get(order.status_id)
            if current_status and current_status.name in ['Aprobada', 'Emitida', 'Recibida']:
                return jsonify({"error": f"La orden ya se encuentra en estado {current_status.name}."}), 400

            if current_status and current_status.name == 'Anulada':
                return jsonify({"error": "No se puede aprobar una orden que ha sido Anulada."}), 400

            # 1. BUSCAR ESTADO DESTINO
            # Dependiendo de tu flujo, el estado de "Aceptado" puede llamarse 'Aprobada' o 'Emitida'
            target_status_name = 'Aprobada'
            status_aprobada = OrderStatus.query.filter_by(name=target_status_name).first()

            if not status_aprobada:
                status_aprobada = OrderStatus(name=target_status_name)
                db.session.add(status_aprobada)
                db.session.flush()

            # 2. ACTUALIZAR
            order.status_id = status_aprobada.id
            db.session.commit()

            return jsonify({
                "success": True,
                "message": f"Orden {order.document_number} APROBADA correctamente."
            }), 200

        except Exception as e:
            db.session.rollback()
            print(f"❌ ERROR AL APROBAR ORDEN: {str(e)}")
            return jsonify({"error": str(e)}), 500

@purchase_api.route('/anular/<int:order_id>', methods=['POST'])
@requires_auth(required_permission='create:purchases')
def anular_orden(payload, order_id):
    user_id = payload['sub']

    # 1. VERIFICACIÓN DE ROL ADMIN (Igual que en tu ejemplo)
    NAMESPACE = 'https://appcompower.com'
    roles = payload.get(f'{NAMESPACE}/roles', [])
    is_admin = 'Admin' in roles or 'Logistica' in roles

    if not is_admin:
        return jsonify({"error": "ACCESO DENEGADO: Solo los administradores pueden anular órdenes."}), 403

    try:
        order = PurchaseOrder.query.get_or_404(order_id)

        # Validar estado actual
        current_status = OrderStatus.query.get(order.status_id)
        if current_status and current_status.name.lower() == 'anulada':
            return jsonify({"error": "Esta orden ya se encuentra anulada."}), 400

        # 2. VALIDACIÓN DE NEGOCIO: ¿Tiene ingresos asociados?
        # Si la orden ya tiene recepciones (receipts), no se debe anular la orden "padre"
        # sin antes anular los ingresos, porque rompería la trazabilidad.
        if order.receipts and len(order.receipts) > 0:
            return jsonify({
                "error": "No se puede anular esta orden porque ya tiene INGRESOS DE MERCADERÍA registrados. "
                         "Debes eliminar o anular los ingresos primero."
            }), 400

        # 3. CAMBIO DE ESTADO
        status_anulada = OrderStatus.query.filter_by(name='Anulada').first()
        if not status_anulada:
            # Fallback por si no existe el estado en DB
            status_anulada = OrderStatus(name='Anulada')
            db.session.add(status_anulada)
            db.session.flush()

        order.status_id = status_anulada.id

        # Opcional: Registrar quién anuló en algún log o nota interna
        # order.footer_note += f"\n[Anulada por admin el {date.today()}]"

        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Orden {order.document_number} ANULADA correctamente."
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"❌ ERROR AL ANULAR ORDEN: {str(e)}")
        return jsonify({"error": str(e)}), 500