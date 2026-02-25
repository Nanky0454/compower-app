from flask import request, jsonify, render_template, current_app, send_file, Blueprint
from flask_cors import cross_origin
from sqlalchemy import func, case, and_, cast, String
from sqlalchemy.orm import joinedload
from datetime import datetime, time as time_obj
import io
from weasyprint import HTML

# --- IMPORTACIONES DE MODELOS ---
from ..extensions import db
from ..models.inventory_models import InventoryTransaction, InventoryStock
from ..models.product_catalog import Product, UnitMeasure
from ..models.cost_center import CostCenter
from ..models.stock_transfer import StockTransfer, StockTransferItem
from ..models.gre import Gre, GreDetail
from ..models.reception import ProductReceipt, ProductReceiptItem
from ..models.provider import Provider
from ..models.location import Location as Site
from ..models.warehouse import Warehouse


report_api = Blueprint('report_api',
                       __name__)


# ==========================================
# REPORTE 1: MOVIMIENTO DE STOCK (EXISTENTE)
# ==========================================
@report_api.route('/stock-movement', methods=['GET'])
def get_stock_movement_report():
    # 1. Obtener filtros
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    warehouse_id = request.args.get('warehouse_id')
    format_type = request.args.get('format', 'json')

    if not start_date_str or not end_date_str:
        return jsonify({"error": "Fechas requeridas"}), 400

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.combine(datetime.strptime(end_date_str, '%Y-%m-%d'), time_obj.max)

    # 2. Consulta Maestra
    query = db.session.query(
        Product.sku,
        Product.name,
        Product.unit_measure_id,
        Product.standard_price,
        func.sum(
            case((InventoryTransaction.timestamp < start_date, InventoryTransaction.quantity_change), else_=0)).label(
            'initial_stock'),
        func.sum(case((and_(InventoryTransaction.timestamp.between(start_date, end_date),
                            InventoryTransaction.quantity_change > 0), InventoryTransaction.quantity_change),
                      else_=0)).label('entries'),
        func.sum(case((and_(InventoryTransaction.timestamp.between(start_date, end_date),
                            InventoryTransaction.quantity_change < 0), func.abs(InventoryTransaction.quantity_change)),
                      else_=0)).label('exits')
    ).join(InventoryTransaction, InventoryTransaction.product_id == Product.id)

    if warehouse_id and warehouse_id != 'all':
        query = query.filter(InventoryTransaction.warehouse_id == warehouse_id)

    results = query.group_by(Product.id).order_by(Product.sku).all()

    report_data = []
    units_map = {u.sunat_code: u.symbol for u in UnitMeasure.query.all()}

    for row in results:
        initial = float(row.initial_stock or 0)
        entries = float(row.entries or 0)
        exits = float(row.exits or 0)
        final_stock = float(initial + entries - exits)
        um_symbol = units_map.get(row.unit_measure_id, 'UND')
        costo_unitario = float(row.standard_price or 0)

        if initial == 0 and entries == 0 and exits == 0:
            continue

        report_data.append({
            'codigo': row.sku,
            'descripcion': row.name,
            'saldo_inicial': initial,
            'entradas': entries,
            'salidas': exits,
            'stock_final': final_stock,
            'unidad': um_symbol,
            'costo_prom': costo_unitario,
            'importe': final_stock * costo_unitario
        })

    total_importe = sum(item['importe'] for item in report_data)

    if format_type == 'json':
        return jsonify(report_data)
    elif format_type == 'pdf':
        html = render_template('stock_report.html', data=report_data, start_date=start_date.strftime('%d/%m/%Y'),
                               end_date=end_date.strftime('%d/%m/%Y'), total_importe=total_importe)
        pdf = HTML(string=html).write_pdf()
        return send_file(io.BytesIO(pdf), mimetype='application/pdf', as_attachment=True,
                         download_name='Stock_Reporte.pdf')


@report_api.route('/item-movement-report', methods=['GET'])
def get_item_movement_report():
    # 1. Obtener filtros
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    product_ids_str = request.args.get('product_ids') # Ej: "1,2,3"

    if not all([start_date_str, end_date_str, product_ids_str]):
        return jsonify({"error": "Fechas y al menos un ID de producto son requeridos"}), 400

    try:
        product_ids = [int(pid) for pid in product_ids_str.split(',')]
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.combine(datetime.strptime(end_date_str, '%Y-%m-%d'), time_obj.max)
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Argumentos inválidos: {e}"}), 400

    report_data = []

    for product_id in product_ids:
        product = Product.query.get(product_id)
        if not product:
            continue

        current_stock = db.session.query(func.sum(InventoryStock.quantity)).filter_by(product_id=product_id).scalar() or 0
        movements = []

        entries = db.session.query(ProductReceiptItem, ProductReceipt)\
            .join(ProductReceipt, ProductReceiptItem.receipt_id == ProductReceipt.id)\
            .filter(ProductReceiptItem.product_id == product_id)\
            .filter(ProductReceipt.receipt_date.between(start_date, end_date))\
            .all()

        for item, receipt in entries:
            movements.append({
                'date': receipt.receipt_date.strftime('%d-%m-%Y'),
                'type': 'ENTRADA',
                'quantity': float(item.quantity),
                'reference': f"Factura: {receipt.invoice_number or 'S/N'}"
            })

        exits = db.session.query(StockTransferItem, StockTransfer)\
            .join(StockTransfer, StockTransferItem.transfer_id == StockTransfer.id)\
            .filter(StockTransferItem.product_id == product_id)\
            .filter(StockTransfer.status != 'Anulada')\
            .filter(StockTransfer.transfer_date.between(start_date, end_date))\
            .options(joinedload(StockTransfer.cost_center))\
            .all()

        for item, transfer in exits:
            site_name = transfer.cost_center.name if transfer.cost_center else 'N/A'
            movements.append({
                'date': transfer.transfer_date.strftime('%d-%m-%Y'),
                'type': 'SALIDA',
                'quantity': float(item.quantity),
                'reference': f"Site: {site_name}"
            })

        movements.sort(key=lambda x: datetime.strptime(x['date'], '%d-%m-%Y'))

        report_data.append({
            'product_name': product.name,
            'product_sku': product.sku,
            'current_stock': float(current_stock),
            'movements': movements
        })

    html = render_template('item_report_detail.html',
                           data=report_data,
                           start_date=start_date.strftime('%d/%m/%Y'),
                           end_date=end_date.strftime('%d/%m/%Y'))
    pdf = HTML(string=html).write_pdf()
    return send_file(io.BytesIO(pdf), mimetype='application/pdf', as_attachment=True,
                     download_name='Reporte_Detallado_Item.pdf')

# ==========================================
# REPORTE 2: COSTOS POR PROYECTO (EXISTENTE)
# ==========================================
@report_api.route('/gre-by-cost-center', methods=['GET', 'OPTIONS'])
@cross_origin()
def get_gre_by_cost_center():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        format_type = request.args.get('format', 'json')

        query = db.session.query(CostCenter, Gre) \
            .join(StockTransfer, StockTransfer.cost_center_id == CostCenter.id) \
            .join(Gre, and_(
            Gre.serie == StockTransfer.gre_series,
            cast(Gre.numero, String) == StockTransfer.gre_number
        )) \
            .options(joinedload(Gre.items).joinedload(GreDetail.product))

        query = query.filter(
            and_(
                StockTransfer.status != 'Anulada',
                StockTransfer.status != 'anulado',
                Gre.gre_type == 'remitente'
            )
        )

        if start_date and end_date:
            query = query.filter(Gre.fecha_de_emision.between(start_date, end_date))

        results = query.order_by(CostCenter.name, Gre.fecha_de_emision.desc()).all()
        grouped_data = {}

        for cc, gre in results:
            cc_id = cc.id
            if cc_id not in grouped_data:
                grouped_data[cc_id] = {
                    'cost_center_id': cc.id,
                    'cost_center_code': cc.code,
                    'cost_center_name': cc.name,
                    'gres': []
                }

            if any(g['id'] == gre.id for g in grouped_data[cc_id]['gres']):
                continue

            items_formatted = []
            for item in gre.items:
                unit_price = 0
                if item.product:
                    costo = getattr(item.product, 'standard_price', None)
                    if costo is None:
                        costo = getattr(item.product, 'standart_price', None)

                    precio = getattr(item.product, 'price', None)
                    unit_price = float(costo or precio or 0)

                items_formatted.append({
                    'descripcion': item.descripcion,
                    'cantidad': float(item.cantidad),
                    'unit_price': unit_price,
                    'unidad': item.unidad_de_medida
                })

            grouped_data[cc_id]['gres'].append({
                'id': gre.id,
                'serie': gre.serie,
                'numero': gre.numero,
                'fecha_emision': gre.fecha_de_emision.strftime('%Y-%m-%d') if gre.fecha_de_emision else None,
                'destinatario': gre.cliente_denominacion,
                'items': items_formatted
            })

        final_list = []
        grand_total = 0.0

        for cc_val in grouped_data.values():
            cc_total = 0.0
            gres_with_totals = []

            for gre in cc_val['gres']:
                gre_total = sum(item['cantidad'] * item['unit_price'] for item in gre['items'])
                gre['total_gre'] = gre_total
                cc_total += gre_total
                gres_with_totals.append(gre)

            cc_val['gres'] = gres_with_totals
            cc_val['total_cc'] = cc_total
            grand_total += cc_total
            final_list.append(cc_val)

        if format_type == 'json':
            return jsonify(final_list)

        elif format_type == 'pdf':
            html = render_template(
                'cost_report.html',
                data=final_list,
                start_date=start_date,
                end_date=end_date,
                grand_total=grand_total
            )
            pdf = HTML(string=html).write_pdf()
            return send_file(
                io.BytesIO(pdf),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'Reporte_Costos_{start_date}.pdf'
            )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================================================
# REPORTE 4: MATERIALES ENVIADOS POR PROVEEDOR Y SITE (NUEVO)
# =========================================================
@report_api.route('/provider-sites', methods=['GET'])
def get_provider_sites_report():
    provider_id = request.args.get('provider_id')
    site_ids_str = request.args.get('site_ids')
    format_type = request.args.get('format', 'json')

    if not provider_id or not site_ids_str:
        return jsonify(error="Se requiere proveedor y al menos un site."), 400

    try:
        site_ids = [int(s_id) for s_id in site_ids_str.split(',')]
    except ValueError:
        return jsonify(error="IDs de site inválidos."), 400

    provider = Provider.query.get_or_404(provider_id)

    # 1. Get the names of the selected sites from their IDs
    selected_site_names_query = db.session.query(Site.name).filter(Site.id.in_(site_ids))
    selected_site_names = [r[0] for r in selected_site_names_query.all()]

    if not selected_site_names:
        return jsonify({'sites': [], 'grand_total': 0.0}) # Return empty report if no sites found

    # 2. Query transfers by filtering the text field 'destination_external_address'
    transfers = db.session.query(
        StockTransferItem.quantity,
        Product.standard_price.label('unit_price'),
        Product.name.label('product_name'),
        StockTransfer.destination_external_address.label('site_name')
    ).select_from(StockTransferItem)\
     .join(Product, StockTransferItem.product_id == Product.id)\
     .join(StockTransfer, StockTransferItem.transfer_id == StockTransfer.id)\
     .join(Gre, and_(
         Gre.serie == StockTransfer.gre_series,
         cast(Gre.numero, String) == StockTransfer.gre_number
     ))\
     .filter(StockTransfer.destination_external_address.in_(selected_site_names))\
     .filter(StockTransfer.status != 'Anulada')\
     .filter(Gre.gre_type == 'remitente')\
     .all()

    report_data = {}
    grand_total = 0.0

    for item in transfers:
        site_name = item.site_name
        if site_name not in report_data:
            report_data[site_name] = {
                'site_id': site_name,  # Grouping by name now
                'site_name': site_name,
                'item_list': [], # Renamed from 'items' to avoid keyword collision
                'total_site': 0.0
            }
        
        quantity = float(item.quantity or 0)
        unit_price = float(item.unit_price or 0)
        subtotal = quantity * unit_price

        # Aggregate items by product to avoid duplicates in the report
        existing_item = next((i for i in report_data[site_name]['item_list'] if i['product_name'] == item.product_name), None)
        if existing_item:
            existing_item['quantity'] += quantity
            existing_item['subtotal'] += subtotal
        else:
            report_data[site_name]['item_list'].append({
                'product_name': item.product_name,
                'quantity': quantity,
                'unit_price': unit_price,
                'subtotal': subtotal
            })
        
        report_data[site_name]['total_site'] += subtotal
        grand_total += subtotal
        
    final_data = {
        'sites': list(report_data.values()),
        'grand_total': grand_total
    }

    if format_type == 'json':
        return jsonify(final_data)
    
    elif format_type == 'pdf':
        html = render_template(
            'provider_sites_report.html',
            data=final_data,
            provider_name=provider.name,
            currency="PEN"
        )
        pdf = HTML(string=html).write_pdf()
        return send_file(
            io.BytesIO(pdf),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Reporte_Proveedor_{provider.name}.pdf'
        )

    return jsonify(error="Formato no soportado"), 400