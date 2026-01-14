from flask import Blueprint, jsonify, request, send_file
# 1. IMPORTAR UnitMeasure
from ..models.product_catalog import Product, Category, UnitMeasure # <--- CAMBIO: Agregado UnitMeasure
from ..extensions import db
from ..services.auth_service import requires_auth
from sqlalchemy import or_
import pandas as pd
import io

product_api = Blueprint('product_api', __name__)

# --- API 1: Buscar Productos ---
# (Sin cambios mayores, solo asegurarte de que p.to_dict() en el modelo esté actualizado)
@product_api.route('/search')
@requires_auth(required_permission='view:catalog')
def search_products(payload):
    query = request.args.get('q', '')
    if not query:
        return jsonify([])

    try:
        search_term = f"%{query.lower()}%"
        products = Product.query.filter(
            or_(
                db.func.lower(Product.name).like(search_term),
                db.func.lower(Product.sku).like(search_term)
            )
        ).limit(20).all()

        return jsonify([p.to_dict() for p in products])

    except Exception as e:
        return jsonify(error=str(e)), 500

# --- API 2: Obtener TODOS los productos ---
@product_api.route('/', strict_slashes=False)
@requires_auth(required_permission='view:catalog')
def get_all_products(payload):
    try:
        products = Product.query.order_by(Product.name).all()
        return jsonify([p.to_dict() for p in products])
    except Exception as e:
        return jsonify(error=str(e)), 500


# --- API 3: Crear un nuevo Producto ---
@product_api.route('/', methods=['POST'])
@requires_auth(required_permission='manage:catalog')
def create_product(payload):
    data = request.get_json()
    # Validación básica
    if not data.get('sku') or not data.get('name') or not data.get('category_id'):
        return jsonify(error="SKU, Nombre y Categoría son requeridos"), 400

    try:
        locations_list = data.get('location', [])
        location_str = ', '.join(locations_list) if isinstance(locations_list, list) else None

        new_prod = Product(
            sku=data['sku'],
            name=data['name'],
            description=data.get('description', ''),
            standard_price=data.get('standard_price', 0.00),
            category_id=data['category_id'],
            # 2. CAMBIO: Recibimos el ID, no el texto
            unit_measure_id=data.get('unit_measure_id'), # <--- CAMBIO: Usar ID
            location=location_str
        )
        # Nota: Ya no asignamos 'unit_of_measure' como string

        db.session.add(new_prod)
        db.session.commit()
        return jsonify(new_prod.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500

# --- API 4: Actualizar un Producto ---
@product_api.route('/<int:product_id>', methods=['PUT'])
@requires_auth(required_permission='manage:catalog')
def update_product(product_id, payload):
    data = request.get_json()
    prod = Product.query.get_or_404(product_id)

    try:
        prod.sku = data.get('sku', prod.sku)
        prod.name = data.get('name', prod.name)
        prod.description = data.get('description', prod.description)
        prod.standard_price = data.get('standard_price', prod.standard_price)
        prod.category_id = data.get('category_id', prod.category_id)

        # 3. CAMBIO: Actualizar el ID de la unidad
        if 'unit_measure_id' in data: # <--- CAMBIO
            prod.unit_measure_id = data['unit_measure_id']

        if 'location' in data:
            locations_list = data.get('location', [])
            prod.location = ', '.join(locations_list) if isinstance(locations_list, list) else None

        db.session.commit()
        return jsonify(prod.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500


# --- API 5: Importación Masiva desde Excel ---
@product_api.route('/import', methods=['POST'], strict_slashes=False)
@requires_auth(required_permission='manage:catalog')
def import_products(payload):
    if 'file' not in request.files:
        return jsonify(error="No se envió ningún archivo"), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify(error="No se seleccionó ningún archivo"), 400

    try:
        df = pd.read_excel(file)
        required_columns = ['SKU', 'Nombre', 'Categoria']
        if not all(col in df.columns for col in required_columns):
            return jsonify(error=f"El Excel debe tener las columnas: {', '.join(required_columns)}"), 400

        # Pre-cargar unidades para no consultar la BD en cada fila (Optimización)
        # Crea un diccionario: {'UND': 1, 'KG': 2, ...}
        all_units = UnitMeasure.query.all()
        units_map = {u.symbol.upper(): u.id for u in all_units}
        # También mapeamos por código SUNAT por si acaso
        for u in all_units:
            units_map[u.sunat_code.upper()] = u.id

        prefix_counters = {}
        created_count = 0
        updated_count = 0

        for index, row in df.iterrows():
            sku_input = str(row['SKU']).strip()
            name = str(row['Nombre']).strip()
            cat_name = str(row['Categoria']).strip()

            # --- Lógica SKU (Igual que antes) ---
            if sku_input.isalpha() and sku_input.isupper():
                prefix = sku_input
                count = prefix_counters.get(prefix, 0) + 1
                prefix_counters[prefix] = count
                sku = f"{prefix}-{count:03d}"
            else:
                sku = sku_input

            # --- Lógica Categoría (Igual que antes) ---
            category = Category.query.filter(db.func.lower(Category.name) == cat_name.lower()).first()
            if not category:
                category = Category(name=cat_name, description="Creada por importación")
                db.session.add(category)
                db.session.flush()

            # --- 4. CAMBIO: Lógica Unidad de Medida (Búsqueda) ---
            um_id = None
            if 'UM' in row and pd.notna(row['UM']):
                um_text = str(row['UM']).strip().upper() # Ej: "UND"
                um_id = units_map.get(um_text) # Busca el ID en el mapa
                # Si no encuentra la unidad, quedará como None (o podrías asignar una por defecto)

            # Buscar Producto
            product = Product.query.filter_by(sku=sku).first()

            if product:
                # ACTUALIZAR
                product.name = name
                product.category_id = category.id
                if 'Descripcion' in row and pd.notna(row['Descripcion']):
                    product.description = str(row['Descripcion'])

                # Actualizar UM solo si viene en el Excel y la encontramos
                if um_id: # <--- CAMBIO
                    product.unit_measure_id = um_id

                if 'Precio' in row and pd.notna(row['Precio']):
                    product.standard_price = float(row['Precio'])
                updated_count += 1
            else:
                # CREAR
                new_prod = Product(
                    sku=sku,
                    name=name,
                    category_id=category.id,
                    description=str(row['Descripcion']) if 'Descripcion' in row and pd.notna(row['Descripcion']) else '',
                    unit_measure_id=um_id, # <--- CAMBIO: Asignar ID encontrado o None
                    standard_price=float(row['Precio']) if 'Precio' in row and pd.notna(row['Precio']) else 0.00
                )
                db.session.add(new_prod)
                created_count += 1

        db.session.commit()
        return jsonify({
            "message": "Importación completada",
            "created": created_count,
            "updated": updated_count
        })

    except Exception as e:
        db.session.rollback()
        print(f"--- ERROR EN IMPORTACIÓN: {e} ---")
        return jsonify(error=f"Error al procesar el archivo: {str(e)}"), 500

# --- API 6: Eliminar (Sin cambios) ---
@product_api.route('/<int:product_id>', methods=['DELETE'])
@requires_auth(required_permission='manage:catalog')
def delete_product(product_id, payload):
    prod = Product.query.get_or_404(product_id)
    try:
        db.session.delete(prod)
        db.session.commit()
        return jsonify(message="Producto eliminado correctamente"), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500

# --- API 7: Exportar Productos a Excel ---
@product_api.route('/export', methods=['GET'])
@requires_auth(required_permission='view:catalog')
def export_products(payload):
    try:
        products = Product.query.order_by(Product.name).all()

        data = []
        for p in products:
            # 5. CAMBIO: Obtener símbolo desde la relación
            um_symbol = p.unit_measure.symbol if p.unit_measure else '' # <--- CAMBIO

            data.append({
                'SKU': p.sku,
                'Nombre': p.name,
                'Categoria': p.category.name if p.category else '',
                'Descripcion': p.description,
                'UM': um_symbol, # <--- Usamos el valor recuperado
                'Precio': p.standard_price
            })

        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Productos')
        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='productos.xlsx'
        )

    except Exception as e:
        print(f"--- ERROR EN EXPORTACIÓN: {e} ---")
        return jsonify(error=f"Error al exportar el archivo: {str(e)}"), 500