from flask import Blueprint, request, jsonify, render_template, make_response
from sqlalchemy import func, case, and_
from datetime import datetime, time as time_obj
from weasyprint import HTML
from ..models.inventory_models import InventoryTransaction
from ..models.product_catalog import Product, UnitMeasure
from ..models.warehouse import Warehouse
from ..models.stock_transfer import StockTransfer
from ..models.cost_center import CostCenter
from ..extensions import db

stock_transfer_report_api = Blueprint('stock_transfer_report_api', __name__)


@stock_transfer_report_api.route('/reports/stock-transfers/print', methods=['GET'])
def print_stock_transfer_report():
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        warehouse_id = request.args.get('warehouse_id')
        with_details = request.args.get('with_details', 'true') == 'true'

        if not start_date_str or not end_date_str:
            return "<h1>Error: Fechas requeridas</h1>", 400

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.combine(datetime.strptime(end_date_str, '%Y-%m-%d'), time_obj.max)
        
        report_data = []
        title = "Reporte de Movimientos (Kardex)"

        if with_details:
            title = "Reporte Detallado de Movimientos (Kardex)"
            query = db.session.query(
                InventoryTransaction,
                Product.name,
                Product.sku,
                Warehouse.name.label('warehouse_name'),
                StockTransfer.destination_external_address,
                CostCenter.code.label('cost_center_code')
            ).select_from(InventoryTransaction)\
             .join(Product, InventoryTransaction.product_id == Product.id)\
             .join(Warehouse, InventoryTransaction.warehouse_id == Warehouse.id)\
             .outerjoin(StockTransfer, and_(
                 StockTransfer.gre_series == func.substr(InventoryTransaction.reference, 5, 4),
                 StockTransfer.gre_number == func.substr(InventoryTransaction.reference, 10)
             ))\
             .outerjoin(CostCenter, StockTransfer.cost_center_id == CostCenter.id)\
             .filter(InventoryTransaction.timestamp.between(start_date, end_date))

            if warehouse_id:
                query = query.filter(InventoryTransaction.warehouse_id == warehouse_id)

            transactions = query.all()

            for tx, product_name, product_sku, warehouse_name, dest, cc_code in transactions:
                report_data.append({
                    'date': tx.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'product_name': product_name,
                    'product_sku': product_sku,
                    'warehouse_name': warehouse_name,
                    'site': dest or '-',
                    'cost_center': cc_code or '-',
                    'type': tx.type,
                    'reference': tx.reference,
                    'quantity_change': tx.quantity_change,
                    'new_quantity': tx.new_quantity
                })
        else:
            title = "Reporte Resumido de Movimientos (Kardex)"
            query = db.session.query(
                Product.sku,
                Product.name,
                func.sum(case(
                    (InventoryTransaction.quantity_change > 0, InventoryTransaction.quantity_change),
                    else_=0
                )).label('entries'),
                func.sum(case(
                    (InventoryTransaction.quantity_change < 0, func.abs(InventoryTransaction.quantity_change)),
                    else_=0
                )).label('exits')
            ).join(InventoryTransaction, InventoryTransaction.product_id == Product.id)\
             .filter(InventoryTransaction.timestamp.between(start_date, end_date))
            
            if warehouse_id:
                query = query.filter(InventoryTransaction.warehouse_id == warehouse_id)

            results = query.group_by(Product.id).order_by(Product.sku).all()
            for row in results:
                if row.entries == 0 and row.exits == 0:
                    continue
                report_data.append({
                    'codigo': row.sku,
                    'descripcion': row.name,
                    'entradas': float(row.entries or 0),
                    'salidas': float(row.exits or 0)
                })

        html = render_template('stock_transfer_report_print.html',
                               data=report_data,
                               with_details=with_details,
                               title=title,
                               start_date=start_date.strftime('%d/%m/%Y'),
                               end_date=end_date.strftime('%d/%m/%Y'))
        return html

    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"<h1>Error al generar el reporte: {e}</h1>", 500
		
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