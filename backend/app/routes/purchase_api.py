import base64

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
from fpdf import FPDF
import os
import io

purchase_api = Blueprint('purchase_api', __name__)


# --- API 1: Lookup SUNAT ---
@purchase_api.route('/lookup-provider/<string:ruc>')
@requires_auth(required_permission='create:purchases')
def lookup_provider(ruc, payload):
    provider = Provider.query.filter_by(ruc=ruc).first()
    if provider: return jsonify(provider.to_dict())

    print(f"Consultando RUC {ruc} a SUNAT...")
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
        except Exception as db_err:
            db.session.rollback()
            response_data = {'id': None, 'ruc': data.get('numero_documento'), 'name': name, 'address': address}

        response_data['address'] = address
        response_data['direccion'] = address
        response_data['ubigeo'] = ubigeo
        return jsonify(response_data)

    except Exception as e:
        return jsonify(error=str(e)), 500


# --- API 2: Catálogos ---
@purchase_api.route('/catalogs')
@requires_auth(required_permission='create:purchases')
def get_purchase_catalogs(payload):
    return jsonify({
        'document_types': [d.to_dict() for d in DocumentType.query.all()],
        'statuses': [s.to_dict() for s in OrderStatus.query.all()],
        'cost_centers': [cc.to_dict() for cc in CostCenter.query.filter_by(status='Activo').all()]
    })


# --- API 3: GET Compras ---
@purchase_api.route('/', methods=['GET'], strict_slashes=False)
@requires_auth(required_permission='view:purchases')
def get_purchases(payload):
    try:
        orders = PurchaseOrder.query.options(
            joinedload(PurchaseOrder.provider),
            joinedload(PurchaseOrder.status),
            joinedload(PurchaseOrder.cost_center)
        ).order_by(PurchaseOrder.id.desc()).all()
        return jsonify([o.to_dict() for o in orders])
    except Exception as e:
        return jsonify(error=str(e)), 500


# --- API 4: CREAR (POST) ---
@purchase_api.route('/', methods=['POST'], strict_slashes=False)
@requires_auth(required_permission='create:purchases')
def create_purchase(payload):
    data = request.get_json()

    if not data.get('provider_id') or not data.get('items'):
        return jsonify(error="Faltan datos obligatorios"), 400

    try:
        t_date = None
        if data.get('transfer_date'):
            try:
                t_date = datetime.strptime(data.get('transfer_date'), '%Y-%m-%d').date()
            except ValueError:
                pass

        new_po = PurchaseOrder(
            document_number=data.get('document_number', 'S/N'),
            owner_id=payload['sub'],
            provider_id=data['provider_id'],
            document_type_id=data['document_type_id'],
            status_id=data['status_id'],
            cost_center_id=data.get('cost_center_id'),

            # --- NUEVO: TIPO DE ORDEN ---
            order_type=data.get('order_type', 'OC'),  # 'OC' o 'OS'

            # Campos Excel
            reference=data.get('reference'),
            attention=data.get('attention'),
            provider_contact=data.get('provider_contact'),
            scope=data.get('scope'),
            payment_condition=data.get('payment_condition'),
            currency=data.get('currency', 'PEN'),
            transfer_date=t_date,

        )
        db.session.add(new_po)

        for item_data in data['items']:
            new_item = PurchaseOrderItem(
                order=new_po,
                product_id=item_data.get('product_id'),
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
        print(f"Error creando OC: {e}")
        return jsonify(error=f"Error creando orden: {str(e)}"), 500


# --- API 5: GET ONE ---
@purchase_api.route('/<int:order_id>', methods=['GET'])
@requires_auth(required_permission='view:purchases')
def get_purchase_by_id(order_id, payload):
    try:
        return jsonify(PurchaseOrder.query.get_or_404(order_id).to_dict())
    except Exception as e:
        return jsonify(error=str(e)), 500


# --- API 8: Update (PUT) ---
@purchase_api.route('/<int:order_id>', methods=['PUT'], strict_slashes=False)
@requires_auth(required_permission='create:purchases')
def update_purchase(order_id, payload):
    data = request.get_json()
    try:
        order = PurchaseOrder.query.get_or_404(order_id)
        if order.status.name in ['Recibida', 'Anulada']:
            return jsonify(error="No se puede editar orden cerrada."), 400

        if 'document_number' in data: order.document_number = data['document_number']
        if 'status_id' in data: order.status_id = data['status_id']
        if 'cost_center_id' in data: order.cost_center_id = data.get('cost_center_id')
        if 'provider_id' in data: order.provider_id = data['provider_id']

        # Actualizar Tipo y Contacto
        if 'order_type' in data: order.order_type = data['order_type']
        if 'provider_phone' in data: order.provider_phone = data['provider_phone']
        if 'provider_email' in data: order.provider_email = data['provider_email']

        # Campos Excel
        if 'reference' in data: order.reference = data['reference']
        if 'attention' in data: order.attention = data['attention']
        if 'provider_contact' in data: order.provider_contact = data['provider_contact']
        if 'scope' in data: order.scope = data['scope']
        if 'payment_condition' in data: order.payment_condition = data['payment_condition']
        if 'currency' in data: order.currency = data['currency']

        if 'transfer_date' in data:
            val = data['transfer_date']
            order.transfer_date = datetime.strptime(val, '%Y-%m-%d').date() if val else None

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


# --- AGREGAR ESTO EN routes/purchase_api.py ---
from sqlalchemy import func


@purchase_api.route('/next-correlative/<string:series>', methods=['GET'])
@requires_auth(required_permission='create:purchases')
def get_next_correlative(series, payload):
    """
    Busca la última orden que empiece con la serie dada (ej: '026')
    y devuelve el siguiente número disponible.
    """
    try:
        # Buscamos la orden más reciente cuyo document_number empiece con "026-"
        last_order = PurchaseOrder.query.filter(
            PurchaseOrder.document_number.like(f"{series}-%")
        ).order_by(PurchaseOrder.id.desc()).first()

        if last_order:
            # Extraemos el número (ej: de "026-045" sacamos "045")
            try:
                parts = last_order.document_number.split('-')
                if len(parts) == 2:
                    last_num = int(parts[1])
                    return jsonify({'next_number': last_num + 1})
            except ValueError:
                pass

        # Si no existe ninguna orden con esa serie, empezamos en 1
        return jsonify({'next_number': 1})

    except Exception as e:
        return jsonify(error=str(e)), 500


# --- API 6: GET Receivables (ESTA ES LA QUE TE FALTA) ---
@purchase_api.route('/receivable', methods=['GET'])
@requires_auth(required_permission='manage:inventory')
def get_receivable_orders(payload):
    try:
        # Buscamos órdenes que NO estén ni Recibidas ni Anuladas
        orders = PurchaseOrder.query.options(
            joinedload(PurchaseOrder.provider),
            joinedload(PurchaseOrder.cost_center),
            joinedload(PurchaseOrder.status)
        ).join(OrderStatus).filter(
            OrderStatus.name == 'Aprobada',
            PurchaseOrder.order_type == 'OC'
        ) .order_by(PurchaseOrder.id.desc()).all()

        return jsonify([o.to_dict() for o in orders])
    except Exception as e:
        return jsonify(error=str(e)), 500


# --- API 7: Cancel (TAMBIÉN FALTA ESTA) ---
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

    # 1. Logo Base64
    logo_path = os.path.join(current_app.instance_path, 'logo_v2.png')
    logo_b64 = ""
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as image_file:
            logo_b64 = base64.b64encode(image_file.read()).decode('utf-8')

    # 2. Lógica de Condiciones (Tu requerimiento específico)
    # Lista maestra de textos fijos
    condiciones = [
        f"Forma de Pago: {order.payment_condition or '-'}",
        f"Fecha de traslado y ejecucion: {order.transfer_date or '-'}",
        f"Tipo de moneda: {order.currency}",
        # Punto 4 (Solo OS)
        "El contratista sera responsable de proveer los implementos de seguridad, SCTR y documentos de SST para su respectivo llenado a su personal.",
        # Punto 5
        "Ambas partes acuerdan que toda información y documentación será considerada confidencial, no será divulgada a terceros sin consentimiento, no utilizarla para fines distintos a los establecidos en esta orden de compra.",
        # Punto 6
        "El contratista se compromete a cumplir con todas la leyes, regulaciones y normas de medio ambiente según apliquen en esta orden de compra.",
        # Punto 7
        "El número de esta orden de compra deberá estar claramente indicado en las facturas. Enviar facturas a: mayala@compower.pe, jbarbachan@compower.pe."
    ]

    # Si es OC (Compra), eliminamos el índice 3 (Punto 4)
    # Al renderizar en el HTML con loop.index, se re-numeran automáticamente (1, 2, 3, 4, 5...)
    if order.order_type == 'OC':
        condiciones.pop(3)

    # 3. Preparar Items
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
            'total': subtotal
        })

    igv = total_neto * 0.18
    total_gen = total_neto + igv

    # 4. Contexto para el Template
    context = {
        'logo_b64': logo_b64,
        'titulo_doc': "ORDEN DE SERVICIO" if order.order_type == 'OS' else "ORDEN DE COMPRA",
        'tipo': order.order_type,
        'codigo': order.document_number,

        'proveedor_nombre': order.provider.name,
        'proveedor_direccion': (order.provider.address or '-')[:60],  # Truncar si es muy largo
        'proveedor_ruc': order.provider.ruc,
        'contacto': order.provider_contact or '-',

        'referencia': order.reference or '-',
        'atencion': order.attention or '-',
        'cc_codigo': order.cost_center.code if order.cost_center else '-',  # CÓDIGO
        'fecha_emision': order.created_at.strftime('%d/%m/%Y'),

        'items': items_data,
        'alcance': order.scope,

        'simbolo': 'S/.' if order.currency == 'PEN' else '$',
        'subtotal': total_neto,
        'igv': igv,
        'total': total_gen,

        'condiciones': condiciones
    }

    # 5. Generar PDF con WeasyPrint
    html_string = render_template('purchase_order_weasy.html', **context)
    pdf_bytes = HTML(string=html_string).write_pdf()

    # 6. Enviar archivo
    safe_name = str(order.document_number).replace('/', '-')
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"Orden_{safe_name}.pdf"
    )