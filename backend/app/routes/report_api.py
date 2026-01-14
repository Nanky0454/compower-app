from flask import request, jsonify, render_template, current_app, send_file, Blueprint
from sqlalchemy import func, case, and_
from datetime import datetime, time as time_obj
import io
from weasyprint import HTML
from ..models.inventory_models import InventoryTransaction
from ..models.product_catalog import Product, UnitMeasure  # Para mostrar UND en vez de NIU
from ..extensions import db

report_api = Blueprint('admin_api', __name__)

@report_api.route('/reports/stock-movement', methods=['GET'])
def get_stock_movement_report():
    # 1. Obtener filtros
    start_date_str = request.args.get('start_date')  # YYYY-MM-DD
    end_date_str = request.args.get('end_date')  # YYYY-MM-DD
    warehouse_id = request.args.get('warehouse_id')
    format_type = request.args.get('format', 'json')  # 'json' o 'pdf'

    if not start_date_str or not end_date_str:
        return jsonify({"error": "Fechas requeridas"}), 400

    # Convertir a objetos datetime (Inicio del día 00:00:00 y Fin del día 23:59:59)
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.combine(datetime.strptime(end_date_str, '%Y-%m-%d'), time_obj.max)

    # 2. Construir la consulta maestra
    # Esta consulta calcula todo en un solo paso
    query = db.session.query(
        Product.sku,
        Product.name,
        Product.unit_measure_code,  # Asumiendo que guardas 'NIU' aquí
        # A) SALDO INICIAL: Suma de movimientos ANTES de la fecha de inicio
        func.sum(case(
            (InventoryTransaction.timestamp < start_date, InventoryTransaction.quantity_change),
            else_=0
        )).label('initial_stock'),
        # B) ENTRADAS: Suma de movimientos positivos DURANTE el rango
        func.sum(case(
            (and_(InventoryTransaction.timestamp.between(start_date, end_date),
                  InventoryTransaction.quantity_change > 0), InventoryTransaction.quantity_change),
            else_=0
        )).label('entries'),
        # C) SALIDAS: Suma de movimientos negativos DURANTE el rango (valor absoluto)
        func.sum(case(
            (and_(InventoryTransaction.timestamp.between(start_date, end_date),
                  InventoryTransaction.quantity_change < 0), func.abs(InventoryTransaction.quantity_change)),
            else_=0
        )).label('exits')
    ).join(InventoryTransaction, InventoryTransaction.product_id == Product.id)

    if warehouse_id:
        query = query.filter(InventoryTransaction.warehouse_id == warehouse_id)

    # Agrupar por producto
    results = query.group_by(Product.id).order_by(Product.sku).all()

    # 3. Procesar datos
    report_data = []

    # Pre-cargar unidades para traducir NIU -> UND
    units_map = {u.sunat_code: u.symbol for u in UnitMeasure.query.all()}

    for row in results:
        initial = row.initial_stock or 0
        entries = row.entries or 0
        exits = row.exits or 0
        final_stock = initial + entries - exits

        # Traducir unidad
        um_symbol = units_map.get(row.unit_measure_code, 'UND')

        # Filtrar: Si no tuvo movimiento ni tiene saldo, no lo mostramos (opcional)
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
            # Placeholder para costos (si tuvieras la lógica de costos implementada)
            'costo_prom': 0.00,
            'importe': 0.00
        })

    # 4. Retornar JSON o PDF
    if format_type == 'json':
        return jsonify(report_data)

    elif format_type == 'pdf':
        # Renderizar HTML
        html = render_template('stock_report.html',
                               data=report_data,
                               start_date=start_date.strftime('%d/%m/%Y'),
                               end_date=end_date.strftime('%d/%m/%Y'),
                               logo_path=None)  # Pasa tu logo aquí si quieres

        pdf = HTML(string=html).write_pdf()
        return send_file(io.BytesIO(pdf), mimetype='application/pdf', as_attachment=True,
                         download_name='Stock_Reporte.pdf')