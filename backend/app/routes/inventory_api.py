from flask import Blueprint, jsonify, request, send_file, current_app
from ..extensions import db
from ..models.warehouse import Warehouse
from ..models.purchase_order import PurchaseOrder, PurchaseOrderItem, OrderStatus
from ..models.inventory_models import InventoryStock, InventoryTransaction
from ..models.product_catalog import Product, Category
from ..services.auth_service import requires_auth
from sqlalchemy import or_, and_
from sqlalchemy.orm import joinedload
import pandas as pd
import os
from fpdf import FPDF
from PIL import Image

inventory_api = Blueprint('inventory_api', __name__)

# --- API de Etiquetas ---
class PDF(FPDF):
    def header(self):
        pass
    def footer(self):
        pass

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

        # --- Dimensiones y Posicionamiento ---
        label_width = 60
        label_height = 30
        margin_x = 10
        margin_y = 10
        gap_x = 5
        gap_y = 5
        
        # Logo - Asegúrate que la ruta es correcta
        logo_path = os.path.join(current_app.instance_path, 'logo_v2.png')
        if not os.path.exists(logo_path):
            return jsonify(error=f"No se encontró el logo en la ruta: {logo_path}"), 500
        
        # Obtener dimensiones del logo para mantener el aspect ratio
        with Image.open(logo_path) as img:
            logo_orig_w, logo_orig_h = img.size
            aspect_ratio = logo_orig_w / logo_orig_h

        x = margin_x
        y = margin_y

        for product in products:
            quantity = int(product.get('quantity', 1))
            for _ in range(quantity):
                # --- Dibujar el borde del sticker ---
                pdf.rect(x, y, label_width, label_height)

                # --- Logo (Centrado y sin distorsión) ---
                logo_h = 8 # Altura fija para el logo
                logo_w = logo_h * aspect_ratio # Ancho calculado para mantener proporción
                x_logo = x + (label_width - logo_w) / 2
                pdf.image(logo_path, x_logo, y + 2, w=logo_w, h=logo_h)

                # --- SKU ---
                pdf.set_font('Arial', 'B', 12)
                pdf.set_xy(x + 1, y + 12) # Se baja un poco el SKU para dar espacio al logo
                pdf.cell(label_width - 2, 5, f"SKU: {product.get('product_sku', 'N/A')}", align='C')

                # --- Nombre del Producto ---
                pdf.set_font('Arial', '', 8)
                pdf.set_xy(x + 1, y + 18) # Se baja el nombre
                # MultiCell para auto-ajuste de texto
                pdf.multi_cell(label_width - 2, 5, product.get('product_name', 'Sin Nombre'), align='C')

                # --- Avanzar a la siguiente posición ---
                x += label_width + gap_x
                if x + label_width > pdf.w - margin_x:
                    x = margin_x
                    y += label_height + gap_y
                    if y + label_height > pdf.h - margin_y:
                        pdf.add_page()
                        y = margin_y

        # --- Generar y enviar el PDF ---
        pdf_output_path = os.path.join(current_app.instance_path, 'etiquetas.pdf')
        pdf.output(pdf_output_path)

        return send_file(
            pdf_output_path,
            as_attachment=True,
            download_name='etiquetas.pdf',
            mimetype='application/pdf'
        )

    except Exception as e:
        print(f"--- ERROR GENERANDO ETIQUETAS: {e} ---")
        return jsonify(error=str(e)), 500

# --- API 1: Obtener la lista de almacenes ---
@inventory_api.route('/warehouses', methods=['GET'])
@requires_auth(required_permission='manage:inventory')
def get_warehouses(payload):
    try:
        warehouses = Warehouse.query.all()
        return jsonify([w.to_dict() for w in warehouses])
    except Exception as e:
        return jsonify(error=str(e)), 500

# --- API 2: Procesar la Recepción de Inventario ---
@inventory_api.route('/receive', methods=['POST'])
@requires_auth(required_permission='manage:inventory')
def receive_inventory(payload):
    """
    Esta es la API principal. Recibe una lista de items a recepcionar.
    Payload esperado:
    {
        "warehouse_id": 1,
        "order_id": 5,
        "items": [
            { "po_item_id": 10, "product_id": 2, "quantity_received": 50, "location": "A1-B2" },
            { "po_item_id": 11, "product_id": 1, "quantity_received": 20, "location": "C3-D4" }
        ]
    }
    """
    data = request.get_json()
    user_id = payload['sub']

    required_fields = ['warehouse_id', 'order_id', 'items']
    if not all(field in data for field in required_fields):
        return jsonify(error="Faltan datos (warehouse_id, order_id, items)"), 400

    try:
        warehouse_id = data['warehouse_id']
        order_id = data['order_id']

        # 1. Recorrer cada item que el usuario está recepcionando
        for item_data in data['items']:
            po_item_id = item_data['po_item_id']
            product_id = item_data['product_id']
            quantity_received = float(item_data['quantity_received'])
            # --- CAMBIO: Obtener la ubicación opcional ---
            location = item_data.get('location')

            if quantity_received <= 0:
                continue # Ignorar items que no se están recibiendo

            # 2. Actualizar el PurchaseOrderItem (le asignamos el product_id)
            po_item = PurchaseOrderItem.query.get(po_item_id)
            if not po_item:
                raise Exception(f"No se encontró el item de orden {po_item_id}")

            po_item.product_id = product_id

            # 3. Encontrar (o crear) el registro de Stock para este producto/almacén
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

            # --- CÁLCULO DE COSTO PROMEDIO PONDERADO Y UBICACIÓN ---
            product = Product.query.get(product_id)

            # --- CAMBIO: Actualizar la ubicación si se proporciona ---
            # --- CAMBIO: Actualizar la ubicación (Append, no overwrite) ---
            if location:
                if not product.location:
                    product.location = location
                else:
                    # Dividir por comas, limpiar espacios y verificar si ya existe
                    existing_locs = [loc.strip() for loc in product.location.split(',')]
                    if location not in existing_locs:
                        existing_locs.append(location)
                        product.location = ",".join(existing_locs)

            current_total_stock = db.session.query(db.func.sum(InventoryStock.quantity)).filter_by(
                product_id=product_id).scalar() or 0.0
            current_total_stock = float(current_total_stock)
            current_avg_price = float(product.standard_price)

            incoming_price = float(po_item.unit_price)
            current_total_value = current_total_stock * current_avg_price
            incoming_total_value = quantity_received * incoming_price
            new_total_quantity = current_total_stock + quantity_received

            if new_total_quantity > 0:
                new_avg_price = (current_total_value + incoming_total_value) / new_total_quantity
                product.standard_price = new_avg_price
            # -------------------------------------------

            # 4. Actualizar la cantidad de stock
            new_stock_quantity = float(stock_entry.quantity) + quantity_received
            stock_entry.quantity = new_stock_quantity

            # 5. Crear la Transacción de Inventario (Kardex)
            transaction = InventoryTransaction(
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity_change=quantity_received,
                new_quantity=new_stock_quantity,
                type="Recepción de Compra",
                user_id=user_id,
                reference=f"Orden #{order_id} - Item {po_item_id}"
            )
            db.session.add(transaction)

        # 6. Actualizar el estado de la Orden de Compra a "Recibida"
        order = PurchaseOrder.query.get(order_id)
        received_status = OrderStatus.query.filter_by(name='Recibida').first()
        if order and received_status:
            order.status_id = received_status.id

        # 7. Guardar todos los cambios en la BD
        db.session.commit()

        return jsonify(success=True, message="Inventario actualizado correctamente.")

    except Exception as e:
        db.session.rollback()
        print(f"--- ERROR AL RECEPCIONAR: {str(e)} ---")
        return jsonify(error=str(e)), 500


# --- API 3: Reporte de Stock Detallado por Almacén ---
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
            # --- CORRECCIÓN: Validar que el producto exista ---
            if not entry.product:
                # Opcional: Imprimir en consola para detectar el ID corrupto
                print(f"⚠️ ALERTA: Stock huérfano encontrado (ID Stock: {entry.id}, Product ID: {entry.product_id})")
                continue

            qty = float(entry.quantity)
            # Validamos también que standard_price no sea None
            price = float(entry.product.standard_price or 0.0)

            # Validamos que la categoría exista para evitar otro error similar
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
        print(f"--- ERROR AL OBTENER REPORTE DE STOCK: {str(e)} ---")
        return jsonify(error=str(e)), 500

# --- API 4: Carga Masiva de Stock (Ajuste de Inventario) ---
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

        # --- CAMBIO: Se añade 'Locacion' a las columnas esperadas ---
        expected_columns = ['SKU', 'Cantidad', 'Locacion']
        if not all(col in df.columns for col in expected_columns):
            return jsonify(error="El Excel debe tener las columnas: SKU, Cantidad, Locacion"), 400

        updated_count = 0
        errors = []

        for index, row in df.iterrows():
            sku = str(row['SKU']).strip()
            try:
                real_quantity = float(row['Cantidad'])
                # --- CAMBIO: Se extrae la ubicación ---
                location = str(row['Locacion']).strip() if pd.notna(row['Locacion']) else None
            except (ValueError, TypeError):
                errors.append(f"SKU {sku}: Cantidad inválida.")
                continue

            # 1. Buscar el producto
            product = Product.query.filter_by(sku=sku).first()
            if not product:
                errors.append(f"SKU no encontrado: {sku}")
                continue

            # --- CAMBIO: Actualizar la ubicación del producto ---
            if location:
                product.location = location

            # 2. Buscar (o crear) el registro de stock actual
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

            # 3. Calcular la diferencia
            difference = real_quantity - current_qty

            if difference != 0:
                # 4. Actualizar Stock
                stock_entry.quantity = real_quantity

                # 5. Crear Transacción (Kardex)
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

        return jsonify({
            "message": "Proceso completado",
            "updated_products": updated_count,
            "errors": errors
        })

    except Exception as e:
        db.session.rollback()
        print(f"--- ERROR CARGA MASIVA: {e} ---")
        return jsonify(error=str(e)), 500

# --- API 5: Obtener Transacciones de Inventario (Kardex) ---
inventory_api.route('/transactions', methods=['GET'], strict_slashes=False)


@requires_auth(required_permission='view:inventory')
def get_kardex_transactions(payload):
    """Devuelve una lista de todas las transacciones de inventario (Kardex) con filtros."""
    try:
        # Construir la consulta base
        query = InventoryTransaction.query.options(
            joinedload(InventoryTransaction.product),
            joinedload(InventoryTransaction.warehouse)
        ).order_by(InventoryTransaction.timestamp.desc())

        # Aplicar filtros desde los query params
        product_id = request.args.get('product_id')
        warehouse_id = request.args.get('warehouse_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if product_id:
            query = query.filter(InventoryTransaction.product_id == product_id)

        if warehouse_id:
            query = query.filter(InventoryTransaction.warehouse_id == warehouse_id)

        if start_date:
            query = query.filter(InventoryTransaction.timestamp >= start_date)

        if end_date:
            query = query.filter(InventoryTransaction.timestamp <= end_date)

        transactions = query.all()

        return jsonify([t.to_dict() for t in transactions])

    except Exception as e:
        print(f"--- ERROR OBTENIENDO KARDEX: {e} ---")
        return jsonify(error=str(e)), 500


@inventory_api.route('/warehouse/<int:warehouse_id>/products', methods=['GET'])
@requires_auth(required_permission='view:inventory')
def get_products_in_warehouse(payload, warehouse_id):
    try:
        # LÓGICA ANTERIOR (Eliminada): Solo traía lo que tenía stock > 0
        # stocks = InventoryStock.query ... .filter(quantity > 0)

        # LÓGICA NUEVA:
        # 1. Traemos TODOS los productos del catálogo (Product).
        # 2. Hacemos un "Outer Join" con el Stock de ESTE almacén específico.
        #    Así, si el producto existe en catálogo pero no en el almacén, saldrá con stock 0.

        results = db.session.query(Product, InventoryStock).outerjoin(
            InventoryStock,
            and_(InventoryStock.product_id == Product.id, InventoryStock.warehouse_id == warehouse_id)
        ).all()

        response = []
        for product, stock_entry in results:

            # Obtener código SUNAT de forma segura
            sunat_code = 'NIU'  # Default
            if product.unit_measure:
                sunat_code = product.unit_measure.sunat_code

            # Si existe entrada de stock, usamos su cantidad. Si no (es None), es 0.
            current_stock = float(stock_entry.quantity) if stock_entry else 0.0

            response.append({
                'id': product.id,
                'sku': product.sku,
                'name': product.name,
                'sunat_code': sunat_code,
                'stock': current_stock  # Puede ser 0, pero el producto aparecerá en la lista
            })

        return jsonify(response)

    except Exception as e:
        print(f"Error fetching warehouse products: {e}")
        return jsonify(error=str(e)), 500