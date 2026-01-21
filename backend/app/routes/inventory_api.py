from flask import Blueprint, jsonify, request, send_file, current_app

from .. import Provider
from ..extensions import db
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


# --- API 2: Procesar la Recepción (CON FIX DE LISTAS) ---
@inventory_api.route('/receive', methods=['POST'])
@requires_auth(required_permission='manage:inventory')
def receive_inventory(payload):
    data = request.get_json()
    user_id = payload['sub']

    # Validaciones básicas
    required_fields = ['warehouse_id', 'order_id', 'items']
    if not all(field in data for field in required_fields):
        return jsonify(error="Faltan datos (warehouse_id, order_id, items)"), 400

    try:
        warehouse_id = data['warehouse_id']
        order_id = data['order_id']
        invoice_number = data.get('invoice_number')  # Factura opcional

        # 1. Crear la Cabecera de Recepción (ProductReceipt)
        new_receipt = ProductReceipt(
            purchase_order_id=order_id,
            warehouse_id=warehouse_id,
            invoice_number=invoice_number,
            created_by=user_id
        )
        db.session.add(new_receipt)
        db.session.flush()  # ID necesario para los items

        # 2. Recorrer items
        for item_data in data['items']:
            po_item_id = item_data['po_item_id']
            product_id = item_data['product_id']
            quantity_received = float(item_data['quantity_received'])

            # --- FIX: SANITIZAR LOCATION (Evitar error de lista) ---
            raw_loc = item_data.get('location')
            if isinstance(raw_loc, list):
                location = ", ".join(str(x) for x in raw_loc)
            elif raw_loc:
                location = str(raw_loc).strip()
            else:
                location = None
            # -------------------------------------------------------

            if quantity_received <= 0:
                continue

                # A. Actualizar item de la orden original
            po_item = PurchaseOrderItem.query.get(po_item_id)
            if po_item:
                po_item.product_id = product_id

            # B. Crear Detalle de Recepción (Historial)
            receipt_item = ProductReceiptItem(
                receipt_id=new_receipt.id,
                product_id=product_id,
                quantity=quantity_received,
                location=location,
                po_item_id=po_item_id
            )
            db.session.add(receipt_item)

            # C. Gestión de Stock (InventoryStock)
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

            # D. Actualizar Producto (Ubicación maestra y Precio Promedio)
            product = Product.query.get(product_id)

            # Agregar ubicación al maestro si es nueva
            if location:
                if not product.location:
                    product.location = location
                else:
                    existing_locs = [l.strip() for l in product.location.split(',')]
                    if location not in existing_locs:
                        existing_locs.append(location)
                        product.location = ",".join(existing_locs)

            # Cálculo Precio Promedio
            current_total_stock = db.session.query(db.func.sum(InventoryStock.quantity)).filter_by(
                product_id=product_id).scalar() or 0.0
            current_total_stock = float(current_total_stock)
            current_avg_price = float(product.standard_price or 0.0)

            incoming_price = float(po_item.unit_price) if po_item else 0.0

            current_total_value = current_total_stock * current_avg_price
            incoming_total_value = quantity_received * incoming_price
            new_total_quantity = current_total_stock + quantity_received

            if new_total_quantity > 0:
                new_avg_price = (current_total_value + incoming_total_value) / new_total_quantity
                product.standard_price = new_avg_price

            # E. Aumentar Stock Real
            new_stock_quantity = float(stock_entry.quantity) + quantity_received
            stock_entry.quantity = new_stock_quantity

            # F. Crear Transacción Kardex
            transaction = InventoryTransaction(
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity_change=quantity_received,
                new_quantity=new_stock_quantity,
                type="Recepción de Compra",
                user_id=user_id,
                reference=f"Orden #{order_id} - {invoice_number or 'S/F'}"
            )
            db.session.add(transaction)

        # 3. Actualizar estado de la OC a "Recibida"
        order = PurchaseOrder.query.get(order_id)
        received_status = OrderStatus.query.filter_by(name='Recibida').first()
        if order and received_status:
            order.status_id = received_status.id

        db.session.commit()
        return jsonify(success=True, message="Recepción guardada correctamente.", receipt_id=new_receipt.id)

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()  # Ver error completo en consola
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
        ).filter(InventoryStock.quantity > 0)

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
@inventory_api.route('/direct-receive', methods=['POST'])
@requires_auth(required_permission='manage:inventory')
def direct_receive_inventory(payload):
    data = request.get_json()
    user_id = payload['sub']

    # 1. Validar Datos
    if not data.get('warehouse_id') or not data.get('items'):
        return jsonify(error="Faltan datos obligatorios (Almacén o Items)."), 400

    try:
        # 2. GESTIÓN DE PROVEEDOR
        provider_id = data.get('provider_id')
        target_provider_id = None

        if provider_id:
            target_provider_id = provider_id
        else:
            # Fallback: Proveedor Genérico
            generic_provider = Provider.query.filter_by(ruc='99999999999').first()
            if not generic_provider:
                generic_provider = Provider(ruc='99999999999', name='INGRESO MANUAL / AJUSTE', address='INTERNO')
                db.session.add(generic_provider)
                db.session.flush()
            target_provider_id = generic_provider.id

        # 3. GESTIÓN DE ESTADOS Y TIPOS
        status_recibida = OrderStatus.query.filter_by(name='Recibida').first()
        if not status_recibida:
            status_recibida = OrderStatus(name='Recibida')
            db.session.add(status_recibida)
            db.session.flush()

        doc_type_guia = DocumentType.query.filter_by(name='Guía de Remisión').first()
        if not doc_type_guia:
            doc_type_guia = DocumentType.query.first()
            if not doc_type_guia:
                doc_type_guia = DocumentType(name='Ingreso Interno')
                db.session.add(doc_type_guia)
                db.session.flush()

        # 4. Crear OC "Fantasma"
        import uuid
        unique_suffix = str(uuid.uuid4())[:8]

        invoice_num = data.get('invoice_number', 'SN')
        dummy_order = PurchaseOrder(
            document_number=f"MAN-{invoice_num}-{unique_suffix}",
            owner_id=user_id,
            provider_id=target_provider_id,
            document_type_id=doc_type_guia.id,
            status_id=status_recibida.id,
            order_type='OC',
            reference=f"Ingreso directo Ref: {invoice_num}"
        )
        db.session.add(dummy_order)
        db.session.flush()

        # 5. Crear la Recepción (ProductReceipt)
        new_receipt = ProductReceipt(
            purchase_order_id=dummy_order.id,
            warehouse_id=data['warehouse_id'],
            invoice_number=invoice_num,
            created_by=user_id
        )
        db.session.add(new_receipt)
        db.session.flush()

        # 6. Procesar Items
        for item in data['items']:
            product_id = item['product_id']
            qty = float(item['quantity'])
            price = float(item.get('unit_price', 0))

            # --- FIX: SANITIZAR LOCATION (Evitar error de lista) ---
            raw_loc = item.get('location')
            location = None
            if isinstance(raw_loc, list):
                # Si es lista ['A', 'B'], convertir a "A, B"
                location = ", ".join(str(x) for x in raw_loc)
            elif raw_loc:
                location = str(raw_loc).strip()
            # -------------------------------------------------------

            # A) Item Recepción
            receipt_item = ProductReceiptItem(
                receipt_id=new_receipt.id,
                product_id=product_id,
                quantity=qty,
                location=location
            )
            db.session.add(receipt_item)

            # B) Stock
            stock_entry = InventoryStock.query.filter_by(
                product_id=product_id,
                warehouse_id=data['warehouse_id']
            ).first()

            if not stock_entry:
                stock_entry = InventoryStock(
                    product_id=product_id,
                    warehouse_id=data['warehouse_id'],
                    quantity=0
                )
                db.session.add(stock_entry)

            # C) Recalcular Costo Promedio y Ubicación
            product = Product.query.get(product_id)

            if location:
                # Actualizar ubicación del producto maestro (Append)
                if not product.location:
                    product.location = location
                else:
                    # Evitar duplicados simples
                    existing = [l.strip() for l in product.location.split(',')]
                    new_locs = [l.strip() for l in location.split(',')]
                    for nl in new_locs:
                        if nl not in existing:
                            existing.append(nl)
                    product.location = ", ".join(existing)

            # Cálculo Ponderado
            current_total_qty = db.session.query(func.sum(InventoryStock.quantity)).filter_by(
                product_id=product_id).scalar() or 0
            current_total_qty = float(current_total_qty)
            current_price = float(product.standard_price or 0)

            new_total_val = (current_total_qty * current_price) + (qty * price)
            new_total_qty_global = current_total_qty + qty

            if new_total_qty_global > 0:
                product.standard_price = new_total_val / new_total_qty_global

            # D) Aumentar Stock Físico
            stock_entry.quantity = float(stock_entry.quantity) + qty

            # E) Kardex
            kardex = InventoryTransaction(
                product_id=product_id,
                warehouse_id=data['warehouse_id'],
                quantity_change=qty,
                new_quantity=stock_entry.quantity,
                type="Ingreso Manual",
                user_id=user_id,
                reference=f"Fac. {invoice_num}"
            )
            db.session.add(kardex)

        db.session.commit()
        return jsonify(success=True, message="Ingreso registrado correctamente")

    except Exception as e:
        db.session.rollback()
        print(f"--- ERROR INGRESO MANUAL: {str(e)} ---")
        import traceback
        traceback.print_exc()
        return jsonify(error=str(e)), 500