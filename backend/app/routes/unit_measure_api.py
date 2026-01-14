from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError
import pandas as pd

# Importaciones de tu proyecto
from ..extensions import db
# AJUSTE AQUÍ: Importamos desde product_catalog porque ahí creaste la clase
from ..models.product_catalog import UnitMeasure
from ..services.auth_service import requires_auth

unit_measure_api = Blueprint('unit_measure_api', __name__)

# --- RUTA 1: Obtener TODAS las unidades ---
@unit_measure_api.route('/', methods=['GET'], strict_slashes=False)
@requires_auth(required_permission='view:catalog')
def get_units(payload):
    """Devuelve una lista de todas las unidades de medida."""
    try:
        # Ordenamos por descripción para que el dropdown se vea ordenado
        units = UnitMeasure.query.order_by(UnitMeasure.description).all()
        return jsonify([u.to_dict() for u in units])
    except Exception as e:
        return jsonify(error=str(e)), 500

# --- RUTA 2: Crear una nueva unidad ---
@unit_measure_api.route('/', methods=['POST'], strict_slashes=False)
@requires_auth(required_permission='manage:catalog')
def create_unit(payload):
    data = request.get_json()

    # Validaciones básicas
    if not data or not data.get('sunat_code') or not data.get('description'):
        return jsonify(error="Faltan datos: 'sunat_code' y 'description' son obligatorios"), 400

    try:
        # Forzamos mayúsculas en el código SUNAT
        code = data['sunat_code'].strip().upper()

        new_unit = UnitMeasure(
            sunat_code=code,
            description=data['description'].strip(),
            # Si no envían símbolo, usamos el mismo código SUNAT como fallback
            symbol=data.get('symbol', code).strip()
        )

        db.session.add(new_unit)
        db.session.commit()
        return jsonify(new_unit.to_dict()), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify(error=f"El código SUNAT '{data.get('sunat_code')}' ya existe."), 409
    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500

# --- RUTA 3: Actualizar una unidad ---
@unit_measure_api.route('/<int:unit_id>', methods=['PUT'])
@requires_auth(required_permission='manage:catalog')
def update_unit(unit_id, payload):
    data = request.get_json()
    unit = UnitMeasure.query.get_or_404(unit_id)

    try:
        # Permitimos editar descripción y símbolo
        if 'description' in data:
            unit.description = data['description'].strip()

        if 'symbol' in data:
            unit.symbol = data['symbol'].strip()

        # El código SUNAT es delicado cambiarlo, pero si lo envían, lo actualizamos
        if 'sunat_code' in data:
            unit.sunat_code = data['sunat_code'].strip().upper()

        db.session.commit()
        return jsonify(unit.to_dict())

    except IntegrityError:
        db.session.rollback()
        return jsonify(error="El código SUNAT ya está en uso por otra unidad."), 409
    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500

# --- RUTA 4: Eliminar una unidad ---
@unit_measure_api.route('/<int:unit_id>', methods=['DELETE'])
@requires_auth(required_permission='manage:catalog')
def delete_unit(unit_id, payload):
    unit = UnitMeasure.query.get_or_404(unit_id)

    try:
        db.session.delete(unit)
        db.session.commit()
        return jsonify(success=True, message="Unidad eliminada correctamente")
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="No se puede eliminar: Esta unidad está asignada a uno o más productos."), 409
    except Exception as e:
        db.session.rollback()
        return jsonify(error=f"Error al eliminar: {str(e)}"), 500

# --- RUTA 5: Importación Masiva desde Excel ---
@unit_measure_api.route('/import', methods=['POST'], strict_slashes=False)
@requires_auth(required_permission='manage:catalog')
def import_units(payload):
    if 'file' not in request.files:
        return jsonify(error="No se envió ningún archivo"), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify(error="No se seleccionó ningún archivo"), 400

    try:
        # Leer Excel usando Pandas
        df = pd.read_excel(file)

        # Verificar columnas requeridas
        required_columns = ['Codigo', 'Descripcion', 'Simbolo']
        if not all(col in df.columns for col in required_columns):
            return jsonify(error=f"El Excel debe tener las columnas exactas: {', '.join(required_columns)}"), 400

        created_count = 0
        updated_count = 0
        errors = []

        for index, row in df.iterrows():
            try:
                # Limpieza de datos
                code = str(row['Codigo']).strip().upper()
                desc = str(row['Descripcion']).strip()
                sym = str(row['Simbolo']).strip()

                if not code or code == 'NAN':
                    continue

                    # Buscamos si existe por código SUNAT
                unit = UnitMeasure.query.filter_by(sunat_code=code).first()

                if unit:
                    # Actualizar
                    unit.description = desc
                    unit.symbol = sym
                    updated_count += 1
                else:
                    # Crear
                    new_unit = UnitMeasure(sunat_code=code, description=desc, symbol=sym)
                    db.session.add(new_unit)
                    created_count += 1

            except Exception as row_e:
                errors.append(f"Fila {index + 2} ({row.get('Codigo')}): {str(row_e)}")

        # Commit final
        try:
            db.session.commit()
        except Exception as commit_e:
            db.session.rollback()
            return jsonify(error=f"Error al guardar en base de datos: {str(commit_e)}"), 500

        return jsonify({
            "message": "Proceso completado",
            "created": created_count,
            "updated": updated_count,
            "errors": errors
        })

    except Exception as e:
        return jsonify(error=f"Error procesando el archivo: {str(e)}"), 500