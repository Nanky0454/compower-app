from flask import Blueprint, request, jsonify, render_template, make_response
from sqlalchemy import func, case, and_
from datetime import datetime, time as time_obj
from weasyprint import HTML
from ..models.inventory_models import InventoryTransaction
from ..models.product_catalog import Product, UnitMeasure
from ..models.warehouse import Warehouse 
from ..extensions import db

stock_transfer_report_api = Blueprint('stock_transfer_report_api', __name__)


@stock_transfer_report_api.route('/reports/stock-transfers', methods=['GET'])
def get_stock_transfer_report():
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        warehouse_id = request.args.get('warehouse_id')
        report_format = request.args.get('format', 'json')

        if not start_date_str or not end_date_str:
            return jsonify({"error": "Las fechas de inicio y fin son requeridas"}), 400

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.combine(datetime.strptime(end_date_str, '%Y-%m-%d'), time_obj.max)
        except ValueError:
            return jsonify({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}), 400

        query = db.session.query(
            Product.sku,
            Product.name,
            UnitMeasure.sunat_code,
            Product.standard_price.label('product_cost'),
            func.sum(case(
                (InventoryTransaction.timestamp < start_date, InventoryTransaction.quantity_change),
                else_=0
            )).label('initial_stock'),
            func.sum(case(
                (and_(
                    InventoryTransaction.timestamp.between(start_date, end_date),
                    InventoryTransaction.quantity_change > 0
                ), InventoryTransaction.quantity_change),
                else_=0
            )).label('entries'),
            func.sum(case(
                (and_(
                    InventoryTransaction.timestamp.between(start_date, end_date),
                    InventoryTransaction.quantity_change < 0
                ), func.abs(InventoryTransaction.quantity_change)),
                else_=0
            )).label('exits')
        ).join(InventoryTransaction, InventoryTransaction.product_id == Product.id) \
            .join(UnitMeasure, Product.unit_measure_id == UnitMeasure.id)

        if warehouse_id:
            query = query.filter(InventoryTransaction.warehouse_id == warehouse_id)

        results = query.group_by(Product.id, Product.sku, Product.name, UnitMeasure.sunat_code, Product.standard_price).order_by(
            Product.sku).all()

        report_data = []
        units_map = {u.sunat_code: u.symbol for u in UnitMeasure.query.all()}
        total_importe = 0

        for row in results:
            initial = float(row.initial_stock or 0)
            entries = float(row.entries or 0)
            exits = float(row.exits or 0)
            final_stock = initial + entries - exits

            if initial == 0 and entries == 0 and exits == 0:
                continue

            um_symbol = units_map.get(row.sunat_code, row.sunat_code)
            costo_unitario = float(row.product_cost or 0)
            importe_total = final_stock * costo_unitario
            total_importe += importe_total

            report_data.append({
                'codigo': row.sku,
                'descripcion': row.name,
                'saldo_inicial': initial,
                'entradas': entries,
                'salidas': exits,
                'stock_final': final_stock,
                'unidad': um_symbol,
                'costo_prom': costo_unitario,
                'importe': importe_total
            })

        if report_format == 'pdf':
            warehouse_name = "Todos los Almacenes"
            if warehouse_id:
                warehouse = Warehouse.query.get(warehouse_id)
                if warehouse:
                    warehouse_name = warehouse.name
            
            currency = "SOLES"

            html_template = render_template(
                'stock_report.html',
                data=report_data,
                start_date=start_date.strftime('%d/%m/%Y'),
                end_date=end_date.strftime('%d/%m/%Y'),
                warehouse_name=warehouse_name,
                currency=currency,
                total_importe=total_importe
            )
            pdf_bytes = HTML(string=html_template).write_pdf()
            response = make_response(pdf_bytes)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename=stock_report_{start_date_str}_to_{end_date_str}.pdf'
            return response

        return jsonify(report_data)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500