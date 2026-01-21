from flask import request, jsonify, render_template, current_app, send_file, Blueprint
from sqlalchemy import func, case, and_
from sqlalchemy.orm import joinedload
from datetime import datetime, time as time_obj
import io
from weasyprint import HTML

# --- IMPORTACIONES DE MODELOS ---
from ..extensions import db
from ..models.inventory_models import InventoryTransaction
from ..models.product_catalog import Product, UnitMeasure
# Nuevos modelos para el reporte de costos
from ..models.cost_center import CostCenter
from ..models.stock_transfer import StockTransfer
from ..models.gre import Gre, GreDetail

report_api = Blueprint('report_api',
                       __name__)  # Asegúrate que en __init__.py lo registres con url_prefix='/api/reports'


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
        Product.unit_measure_code,
        Product.cost,  # Agregamos el costo del producto para cálculos
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
        initial = row.initial_stock or 0
        entries = row.entries or 0
        exits = row.exits or 0
        final_stock = initial + entries - exits
        um_symbol = units_map.get(row.unit_measure_code, 'UND')
        costo_unitario = float(row.cost or 0)

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
            'importe': final_stock * costo_unitario  # Calculo simple de valorizado
        })

    if format_type == 'json':
        return jsonify(report_data)
    elif format_type == 'pdf':
        html = render_template('stock_report.html', data=report_data, start_date=start_date.strftime('%d/%m/%Y'),
                               end_date=end_date.strftime('%d/%m/%Y'))
        pdf = HTML(string=html).write_pdf()
        return send_file(io.BytesIO(pdf), mimetype='application/pdf', as_attachment=True,
                         download_name='Stock_Reporte.pdf')


# ==========================================
# REPORTE 2: COSTOS POR PROYECTO (NUEVO)
# ==========================================
@report_api.route('/gre-by-cost-center', methods=['GET'])
def get_gre_by_cost_center():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Join: CostCenter -> StockTransfer -> Gre
        query = db.session.query(CostCenter, Gre) \
            .join(StockTransfer, StockTransfer.cost_center_id == CostCenter.id) \
            .join(Gre, and_(
            Gre.serie == StockTransfer.gre_series,
            Gre.numero == StockTransfer.gre_number
        )) \
            .options(joinedload(Gre.items).joinedload(GreDetail.product))

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

            # Verificar duplicados de guías (por si el join trae filas repetidas)
            if any(g['id'] == gre.id for g in grouped_data[cc_id]['gres']):
                continue

            items_formatted = []
            for item in gre.items:
                # Obtener precio del producto o fallback a 0
                unit_price = float(item.product.cost or item.product.price or 0) if item.product else 0

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

        return jsonify(list(grouped_data.values()))

    except Exception as e:
        print(f"Error reporte costos: {e}")
        return jsonify({"error": str(e)}), 500