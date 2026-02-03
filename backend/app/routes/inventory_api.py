from datetime import date

from flask import Blueprint, jsonify, request, send_file, current_app

from .. import Provider
from ..extensions import db
from ..models.exchange_rate import ExchangeRate
from ..models.warehouse import Warehouse
from ..models.purchase_order import PurchaseOrder, PurchaseOrderItem, OrderStatus, DocumentType
from ..models.inventory_models import InventoryStock, InventoryTransaction
from ..models.product_catalog import Product, Category
# --- IMPORTS NUEVOS PARA RECEPCIÓN ---
from ..models.reception import ProductReceipt, ProductReceiptItem
# -------------------------------------
from ..services.auth_service import requires_auth
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import joinedload
import pandas as pd
import os
from fpdf import FPDF
from PIL import Image

inventory_api = Blueprint('inventory_api', __name__)


# --- API DE ETIQUETAS (Sin cambios) ---
class PDF(FPDF):
    def header(self): pass

    def footer(self): pass


@inventory_api.route('/generate-labels', methods=['POST'])
@requires_auth(required_permission='view:inventory')
def generate_labels(payload):
    data = request.get_json()
    products = data.get('products', [])

    if not products:
        return jsonify(error="No se proporcionaron productos para generar etiquetas."), 400

    try:
        pdf = PDF('P', 'mm', 'A4')
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=10)
        pdf.set_font('Arial', 'B', 10)

        label_width, label_height = 60, 30
        margin_x, margin_y = 10, 10
        gap_x, gap_y = 5, 5

        logo_path = os.path.join(current_app.instance_path, 'logo_v2.png')
        if not os.path.exists(logo_path):
            return jsonify(error=f"No se encontró el logo en: {logo_path}"), 500

        with Image.open(logo_path) as img:
            logo_orig_w, logo_orig_h = img.size
            aspect_ratio = logo_orig_w / logo_orig_h

        x, y = margin_x, margin_y

        for product in products:
            quantity = int(product.get('quantity', 1))
            for _ in range(quantity):
                pdf.rect(x, y, label_width, label_height)

                logo_h = 8
                logo_w = logo_h * aspect_ratio
                x_logo = x + (label_width - logo_w) / 2
                pdf.image(logo_path, x_logo, y + 2, w=logo_w, h=logo_h)

                pdf.set_font('Arial', 'B', 12)
                pdf.set_xy(x + 1, y + 12)
                pdf.cell(label_width - 2, 5, f"SKU: {product.get('product_sku', 'N/A')}", align='C')

                pdf.set_font('Arial', '', 8)
                pdf.set_xy(x + 1, y + 18)
                pdf.multi_cell(label_width - 2, 5, product.get('product_name', 'Sin Nombre'), align='C')

                x += label_width + gap_x
                if x + label_width > pdf.w - margin_x:
                    x = margin_x
                    y += label_height + gap_y
                    if y + label_height > pdf.h - margin_y:
                        pdf.add_page()
                        y = margin_y

        pdf_output_path = os.path.join(current_app.instance_path, 'etiquetas.pdf')
        pdf.output(pdf_output_path)

        return send_file(pdf_output_path, as_attachment=True, download_name='etiquetas.pdf', mimetype='application/pdf')

    except Exception as e:
        print(f"--- ERROR GENERANDO ETIQUETAS: {e} ---")
        return jsonify(error=str(e)), 500


# --- API 1: Obtener almacenes ---
@inventory_api.route('/warehouses', methods=['GET'])
@requires_auth(required_permission='manage:inventory')
def get_warehouses(payload):
    try:
        warehouses = Warehouse.query.all()
        return jsonify([w.to_dict() for w in warehouses])
    except Exception as e:
        return jsonify(error=str(e)), 500


# --- API 2: Procesar la Recepción (CON LÓGICA DE MONEDA Y PROMEDIO) ---
@inventory_api.route('/receive', methods=['POST'])
@requires_auth(required_permission='manage:inventory')
def receive_inventory(payload):
    data = request.get_json()
    user_id = payload['sub']

    required_fields = ['warehouse_id', 'order_id', 'items']
    if not all(field in data for field in required_fields):
        return jsonify(error="Faltan datos (warehouse_id, order_id, items)"), 400

    try:
        warehouse_id = data['warehouse_id']
        order_id = data['order_id']
        invoice_number = data.get('invoice_number')

        # 1. OBTENER ORDEN Y TIPO DE CAMBIO
        order = PurchaseOrder.query.get(order_id)
        if not order:
            return jsonify(error="Orden de compra no encontrada"), 404

        # Lógica de Tipo de Cambio
        tipo_cambio_venta = 1.0
        moneda_orden = getattr(order, 'currency', 'PEN')  # Asume PEN si no existe campo currency

        if moneda_orden == 'USD':
            # Buscar el tipo de cambio de HOY (o de la fecha de la orden si prefieres)
            tc = ExchangeRate.query.filter_by(date=date.today(), currency='USD').first()
            if not tc:
                # OJO: Si no hay tipo de cambio, es peligroso inventar uno.
                # Retornamos error para obligar a que se ejecute el cron o se cargue manual.
                return jsonify(
                    error=f"No se encontró el Tipo de Cambio (USD) para hoy ({date.today()}). Por favor actualízalo."), 400

            tipo_cambio_venta = float(tc.sell_rate)

        # 2. Crear Cabecera
        new_receipt = ProductReceipt(
            purchase_order_id=order_id,
            warehouse_id=warehouse_id,
            invoice_number=invoice_number,
            created_by=user_id
        )
        db.session.add(new_receipt)
        db.session.flush()

        # 3. Recorrer items
        for item_data in data['items']:
            po_item_id = item_data['po_item_id']
            product_id = item_data['product_id']
            quantity_received = float(item_data['quantity_received'])

            # Sanitizar Location
            raw_loc = item_data.get('location')
            if isinstance(raw_loc, list):
                location = ", ".join(str(x) for x in raw_loc)
            elif raw_loc:
                location = str(raw_loc).strip()
            else:
                location = None

            if quantity_received <= 0:
                continue

            po_item = PurchaseOrderItem.query.get(po_item_id)
            if po_item:
                po_item.product_id = product_id

            # Crear Detalle Recepción
            receipt_item = ProductReceiptItem(
                receipt_id=new_receipt.id,
                product_id=product_id,
                quantity=quantity_received,
                location=location,
                po_item_id=po_item_id
            )
            db.session.add(receipt_item)

            # Gestión de Stock
            stock_entry = InventoryStock.query.filter_by(
                product_id=product_id,
                warehouse_id=warehouse_id
            ).first()

            if not stock_entry:
                stock_entry = InventoryStock(
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    quantity=0.0
                )
                db.session.add(stock_entry)

            # --- CÁLCULO DE PRECIO PROMEDIO PONDERADO (CORREGIDO) ---
            product = Product.query.get(product_id)

            # A. Obtener el precio de entrada y CONVERTIR A SOLES si es necesario
            precio_unitario_original = float(po_item.unit_price) if po_item else 0.0
            precio_entrada_soles = precio_unitario_original * tipo_cambio_venta

            # B. Datos actuales
            stock_actual_total = db.session.query(func.sum(InventoryStock.quantity)).filter_by(
                product_id=product_id).scalar() or 0.0
            stock_actual_total = float(stock_actual_total)
            costo_promedio_actual = float(product.standard_price or 0.0)

            # C. Fórmula Ponderada
            # Si el stock global es 0 o negativo, el nuevo precio es simplemente el precio de entrada.
            # Esto soluciona el problema de "promediar con 0".
            if stock_actual_total <= 0:
                new_avg_price = precio_entrada_soles
            else:
                valor_total_actual = stock_actual_total * costo_promedio_actual
                valor_entrada = quantity_received * precio_entrada_soles
                nuevo_stock_total = stock_actual_total + quantity_received

                new_avg_price = (valor_total_actual + valor_entrada) / nuevo_stock_total

            product.standard_price = new_avg_price

            # Actualizar Ubicación (Append)
            if location:
                if not product.location:
                    product.location = location
                else:
                    existing_locs = [l.strip() for l in product.location.split(',')]
                    if location not in existing_locs:
                        existing_locs.append(location)
                        product.location = ", ".join(existing_locs)

            # Aumentar Stock Físico
            stock_entry.quantity = float(stock_entry.quantity) + quantity_received

            # Kardex
            moneda_txt = "USD" if moneda_orden == 'USD' else "PEN"
            transaction = InventoryTransaction(
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity_change=quantity_received,
                new_quantity=stock_entry.quantity,
                type="Recepción de Compra",
                user_id=user_id,
                # Guardamos referencia del TC usado para auditoría
                reference=f"OC #{order_id} ({moneda_txt} -> S/ {tipo_cambio_venta})"
            )
            db.session.add(transaction)

        # Actualizar estado OC
        order = PurchaseOrder.query.get(order_id)
        received_status = OrderStatus.query.filter_by(name='Recibida').first()
        if order and received_status:
            order.status_id = received_status.id

        db.session.commit()
        return jsonify(success=True, message="Recepción guardada correctamente.", receipt_id=new_receipt.id)

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        print(f"--- ERROR AL RECEPCIONAR: {str(e)} ---")
        return jsonify(error=str(e)), 500


# --- API 3: Reporte de Stock ---
@inventory_api.route('/stock-report', methods=['GET'], strict_slashes=False)
@requires_auth(required_permission='view:inventory')
def get_stock_report(payload):
    try:
        query = InventoryStock.query.options(
            joinedload(InventoryStock.product).joinedload(Product.category),
            joinedload(InventoryStock.warehouse)
        )

        stock_entries = query.all()
        report = []
        for entry in stock_entries:
            if not entry.product: continue

            qty = float(entry.quantity)
            price = float(entry.product.standard_price or 0.0)
            category_name = entry.product.category.name if entry.product.category else "Sin Categoría"

            report.append({
                "product_sku": entry.product.sku,
                "product_name": entry.product.name,
                "category_name": category_name,
                "warehouse_name": entry.warehouse.name,
                "product_location": entry.product.location,
                "quantity": qty,
                "unit_price": price,
                "total_value": qty * price
            })

        return jsonify(report)
    except Exception as e:
        print(f"--- ERROR REPORTE: {str(e)} ---")
        return jsonify(error=str(e)), 500


# --- API 4: Carga Masiva (Ajuste) ---
@inventory_api.route('/adjust-mass', methods=['POST'], strict_slashes=False)
@requires_auth(required_permission='manage:inventory')
def adjust_inventory_mass(payload):
    if 'file' not in request.files or 'warehouse_id' not in request.form:
        return jsonify(error="Faltan datos (archivo o almacén)"), 400

    file = request.files['file']
    warehouse_id = request.form['warehouse_id']
    user_id = payload['sub']

    try:
        df = pd.read_excel(file)
        expected_columns = ['SKU', 'Cantidad', 'Locacion']
        if not all(col in df.columns for col in expected_columns):
            return jsonify(error="El Excel debe tener: SKU, Cantidad, Locacion"), 400

        updated_count = 0
        errors = []

        for index, row in df.iterrows():
            sku = str(row['SKU']).strip()
            try:
                real_quantity = float(row['Cantidad'])
                location = str(row['Locacion']).strip() if pd.notna(row['Locacion']) else None
            except (ValueError, TypeError):
                errors.append(f"SKU {sku}: Cantidad inválida.")
                continue

            product = Product.query.filter_by(sku=sku).first()
            if not product:
                errors.append(f"SKU no encontrado: {sku}")
                continue

            if location:
                product.location = location

            stock_entry = InventoryStock.query.filter_by(
                product_id=product.id,
                warehouse_id=warehouse_id
            ).first()

            if not stock_entry:
                stock_entry = InventoryStock(
                    product_id=product.id,
                    warehouse_id=warehouse_id,
                    quantity=0.0
                )
                db.session.add(stock_entry)

            current_qty = float(stock_entry.quantity)
            difference = real_quantity - current_qty

            if difference != 0:
                stock_entry.quantity = real_quantity
                transaction = InventoryTransaction(
                    product_id=product.id,
                    warehouse_id=warehouse_id,
                    quantity_change=difference,
                    new_quantity=real_quantity,
                    type="Carga Inicial / Ajuste",
                    user_id=user_id
                )
                db.session.add(transaction)
                updated_count += 1

        db.session.commit()
        return jsonify({"message": "Proceso completado", "updated_products": updated_count, "errors": errors})

    except Exception as e:
        db.session.rollback()
        print(f"--- ERROR CARGA MASIVA: {e} ---")
        return jsonify(error=str(e)), 500


# --- API 5: Kardex ---
@inventory_api.route('/transactions', methods=['GET'], strict_slashes=False)
@requires_auth(required_permission='view:inventory')
def get_kardex_transactions(payload):
    try:
        query = InventoryTransaction.query.options(
            joinedload(InventoryTransaction.product),
            joinedload(InventoryTransaction.warehouse)
        ).order_by(InventoryTransaction.timestamp.desc())

        product_id = request.args.get('product_id')
        warehouse_id = request.args.get('warehouse_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if product_id: query = query.filter(InventoryTransaction.product_id == product_id)
        if warehouse_id: query = query.filter(InventoryTransaction.warehouse_id == warehouse_id)
        if start_date: query = query.filter(InventoryTransaction.timestamp >= start_date)
        if end_date: query = query.filter(InventoryTransaction.timestamp <= end_date)

        transactions = query.all()
        return jsonify([t.to_dict() for t in transactions])

    except Exception as e:
        print(f"--- ERROR KARDEX: {e} ---")
        return jsonify(error=str(e)), 500


# --- API 6: Productos en Almacén ---
@inventory_api.route('/warehouse/<int:warehouse_id>/products', methods=['GET'])
@requires_auth(required_permission='view:inventory')
def get_products_in_warehouse(payload, warehouse_id):
    try:
        results = db.session.query(Product, InventoryStock).outerjoin(
            InventoryStock,
            and_(InventoryStock.product_id == Product.id, InventoryStock.warehouse_id == warehouse_id)
        ).all()

        response = []
        for product, stock_entry in results:
            sunat_code = product.unit_measure.sunat_code if product.unit_measure else 'NIU'
            current_stock = float(stock_entry.quantity) if stock_entry else 0.0

            response.append({
                'id': product.id,
                'sku': product.sku,
                'name': product.name,
                'sunat_code': sunat_code,
                'stock': current_stock,
                'location': product.location  # Enviar ubicación actual también
            })

        return jsonify(response)

    except Exception as e:
        print(f"Error fetching warehouse products: {e}")
        return jsonify(error=str(e)), 500


# --- API 2: Ingreso Directo (Sin OC Previa) ---
from flask import request, jsonify
from datetime import date
from sqlalchemy import func


# Asegúrate de importar tus modelos y extensiones
# from app import db
# from app.models import Product, ProductReceipt, ProductReceiptItem, InventoryStock, InventoryTransaction, Provider, ExchangeRate

@inventory_api.route('/direct-receive', methods=['POST'])
@requires_auth(required_permission='manage:inventory')
def direct_receive_inventory(payload):
    data = request.get_json()
    user_id = payload['sub']

    # 1. VALIDACIÓN BÁSICA
    if not data.get('warehouse_id') or not data.get('items'):
        return jsonify(error="Faltan datos obligatorios (Almacén o Items)."), 400

    try:
        # ---------------------------------------------------------
        # 2. GESTIÓN DE TIPO DE CAMBIO (Moneda)
        # ---------------------------------------------------------
        currency = data.get('currency', 'PEN')
        tipo_cambio_venta = 1.0

        if currency == 'USD':
            tc = ExchangeRate.query.filter_by(date=date.today(), currency='USD').first()
            if not tc:
                # Fallback al último TC conocido
                tc = ExchangeRate.query.filter_by(currency='USD').order_by(ExchangeRate.date.desc()).first()

            if not tc:
                return jsonify(error="Error: No se encontró Tipo de Cambio para procesar ingreso en Dólares."), 400

            tipo_cambio_venta = float(tc.sell_rate)

        # ---------------------------------------------------------
        # 3. GESTIÓN DE PROVEEDOR
        # ---------------------------------------------------------
        # Ahora lo guardamos directamente en la Recepción, no en una OC
        provider_id = data.get('provider_id')
        target_provider_id = None

        if provider_id:
            target_provider_id = provider_id
        else:
            # Fallback: Proveedor Genérico
            generic_ruc = '99999999999'
            generic_provider = Provider.query.filter_by(ruc=generic_ruc).first()
            if not generic_provider:
                generic_provider = Provider(ruc=generic_ruc, name='INGRESO MANUAL / AJUSTE', address='INTERNO')
                db.session.add(generic_provider)
                db.session.flush()
            target_provider_id = generic_provider.id

        # ---------------------------------------------------------
        # 4. CREACIÓN DE LA RECEPCIÓN (LIMPIA, SIN OC)
        # ---------------------------------------------------------
        new_receipt = ProductReceipt(
            purchase_order_id=None,  # <--- AQUÍ ESTÁ LA MAGIA: NULL
            provider_id=target_provider_id,  # <--- Guardamos quién envió la mercadería
            warehouse_id=data['warehouse_id'],
            invoice_number=data.get('invoice_number', 'SN'),
            created_by=user_id
        )
        db.session.add(new_receipt)
        db.session.flush()  # Obtenemos el ID de la recepción

        # ---------------------------------------------------------
        # 5. PROCESAMIENTO DE ITEMS (Stock, Costos, Kardex)
        # ---------------------------------------------------------
        for item in data['items']:
            product_id = item['product_id']
            qty = float(item['quantity'])

            # Precio ingresado por usuario
            raw_unit_price = float(item.get('unit_price', 0))

            # Valoración en Soles (Contable)
            price_in_soles = raw_unit_price * tipo_cambio_venta

            # Ubicación
            raw_loc = item.get('location')
            location = str(raw_loc).strip() if raw_loc else None

            # A) Crear Item de Recepción
            receipt_item = ProductReceiptItem(
                receipt_id=new_receipt.id,
                product_id=product_id,
                quantity=qty,
                location=location,
                po_item_id=None  # <--- NULL: No hay item de OC vinculado
            )
            db.session.add(receipt_item)

            # B) Obtener o Crear Stock en Almacén
            stock_entry = InventoryStock.query.filter_by(
                product_id=product_id,
                warehouse_id=data['warehouse_id']
            ).first()

            if not stock_entry:
                stock_entry = InventoryStock(
                    product_id=product_id,
                    warehouse_id=data['warehouse_id'],
                    quantity=0.0
                )
                db.session.add(stock_entry)

            # C) CÁLCULO PRECIO PROMEDIO PONDERADO (CPP) - GLOBAL
            product = Product.query.get(product_id)

            current_total_qty = db.session.query(func.sum(InventoryStock.quantity)).filter_by(
                product_id=product_id).scalar() or 0.0
            current_total_qty = float(current_total_qty)
            current_avg_price = float(product.standard_price or 0.0)

            # Lógica CPP
            if current_total_qty <= 0:
                product.standard_price = price_in_soles
            else:
                current_val = current_total_qty * current_avg_price
                incoming_val = qty * price_in_soles
                final_qty = current_total_qty + qty

                if final_qty > 0:
                    product.standard_price = (current_val + incoming_val) / final_qty

            # D) Actualizar Ubicación (Concatenar si es nueva)
            if location:
                if not product.location:
                    product.location = location
                else:
                    existing = [l.strip() for l in product.location.split(',')]
                    new_locs = [l.strip() for l in location.split(',')]
                    changed = False
                    for nl in new_locs:
                        if nl not in existing:
                            existing.append(nl)
                            changed = True
                    if changed:
                        product.location = ", ".join(existing)

            # E) Aumentar Stock Físico
            stock_entry.quantity = float(stock_entry.quantity) + qty

            # F) Registrar en Kardex
            ref_text = f"Ingreso Directo {data.get('invoice_number', 'SN')}"
            if currency == 'USD':
                ref_text += f" (TC: {tipo_cambio_venta:.3f})"

            transaction = InventoryTransaction(
                product_id=product_id,
                warehouse_id=data['warehouse_id'],
                quantity_change=qty,
                new_quantity=stock_entry.quantity,
                type="Ingreso Manual",
                user_id=user_id,
                reference=ref_text
            )
            db.session.add(transaction)

        # 6. COMMIT FINAL
        db.session.commit()
        return jsonify(success=True, message="Ingreso registrado correctamente", receipt_id=new_receipt.id)

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify(error=f"Error al procesar ingreso: {str(e)}"), 500


