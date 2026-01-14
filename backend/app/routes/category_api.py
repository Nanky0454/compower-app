from flask import Blueprint, jsonify, request
from ..extensions import db
from ..models.product_catalog import Category
from ..services.auth_service import requires_auth
import pandas as pd # <-- Importar pandas

category_api = Blueprint('category_api', __name__)

# --- RUTA 1: Obtener TODAS las categorías ---
@category_api.route('/', methods=['GET'], strict_slashes=False)
@requires_auth(required_permission='view:catalog')
def get_categories(payload):
    """Devuelve una lista de todas las categorías."""
    try:
        categories = Category.query.order_by(Category.name).all()
        return jsonify([c.to_dict() for c in categories])
    except Exception as e:
        return jsonify(error=str(e)), 500

# --- RUTA 2: Crear una nueva categoría ---
@category_api.route('/', methods=['POST'], strict_slashes=False)
@requires_auth(required_permission='manage:catalog')
def create_category(payload):
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify(error="El campo 'name' es requerido"), 400

    try:
        new_cat = Category(
            name=data['name'],
            description=data.get('description', ''),
            # Si se envía un 'parent_id', se crea como subcategoría
            parent_id=data.get('parent_id')
        )
        db.session.add(new_cat)
        db.session.commit()
        return jsonify(new_cat.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500

# --- RUTA 3: Actualizar una categoría ---
@category_api.route('/<int:cat_id>', methods=['PUT'])
@requires_auth(required_permission='manage:catalog')
def update_category(cat_id, payload):
    data = request.get_json()
    cat = Category.query.get_or_404(cat_id)

    try:
        cat.name = data.get('name', cat.name)
        cat.description = data.get('description', cat.description)
        cat.parent_id = data.get('parent_id', cat.parent_id)

        db.session.commit()
        return jsonify(cat.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500

# --- RUTA 4: Eliminar una categoría ---
@category_api.route('/<int:cat_id>', methods=['DELETE'])
@requires_auth(required_permission='manage:catalog')
def delete_category(cat_id, payload):
    cat = Category.query.get_or_404(cat_id)

    try:
        db.session.delete(cat)
        db.session.commit()
        return jsonify(success=True, message="Categoría eliminada")
    except Exception as e:
        db.session.rollback()
        return jsonify(error=f"No se pudo eliminar: {str(e)}"), 500

# --- RUTA 5: Importación Masiva de Categorías desde Excel ---
@category_api.route('/import', methods=['POST'], strict_slashes=False)
@requires_auth(required_permission='manage:catalog')
def import_categories(payload):
    if 'file' not in request.files:
        return jsonify(error="No se envió ningún archivo"), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify(error="No se seleccionó ningún archivo"), 400

    try:
        df = pd.read_excel(file)

        required_columns = ['Nombre']
        if not all(col in df.columns for col in required_columns):
            return jsonify(error=f"El Excel debe tener al menos la columna: {', '.join(required_columns)}. La columna 'Padre' es opcional."), 400

        created_count = 0
        updated_count = 0
        errors = []

        # Para manejar las relaciones padre-hijo, procesamos en dos pasadas o de forma inteligente
        # Primero creamos todas las categorías sin padres, luego asignamos padres
        # O, más simple, procesamos en orden y creamos padres si no existen

        for index, row in df.iterrows():
            try:
                cat_name = str(row['Nombre']).strip()
                parent_name = str(row['Padre']).strip() if 'Padre' in row and pd.notna(row['Padre']) else None
                
                category = Category.query.filter(db.func.lower(Category.name) == cat_name.lower()).first()
                
                parent_id = None
                if parent_name:
                    parent_category = Category.query.filter(db.func.lower(Category.name) == parent_name.lower()).first()
                    if not parent_category:
                        # Crear la categoría padre si no existe
                        new_parent = Category(name=parent_name, description=f"Padre de {cat_name} (creado por importación)")
                        db.session.add(new_parent)
                        db.session.flush() # Para obtener el ID
                        parent_id = new_parent.id
                    else:
                        parent_id = parent_category.id

                if category:
                    # Actualizar existente
                    category.parent_id = parent_id
                    updated_count += 1
                else:
                    # Crear nueva
                    new_cat = Category(name=cat_name, parent_id=parent_id)
                    db.session.add(new_cat)
                    created_count += 1
            except Exception as row_e:
                errors.append(f"Fila {index + 2}: Error al procesar '{cat_name}' - {str(row_e)}")
                db.session.rollback() # Rollback de la fila actual si hay error

        db.session.commit()

        return jsonify({
            "message": "Importación de categorías completada",
            "created": created_count,
            "updated": updated_count,
            "errors": errors
        })

    except Exception as e:
        db.session.rollback()
        print(f"--- ERROR EN IMPORTACIÓN DE CATEGORÍAS: {e} ---")
        return jsonify(error=f"Error al procesar el archivo: {str(e)}"), 500