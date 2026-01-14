from flask import Blueprint, jsonify, request
from ..extensions import db
from ..models.ubigeo import Ubigeo
from ..services.auth_service import requires_auth
import pandas as pd
from sqlalchemy import func # <--- ¡IMPORTANTE! Necesario para agrupar (group_by)

ubigeo_api = Blueprint('ubigeo_api', __name__)

# ==========================================
#   RUTAS DE LECTURA (Read-Only)
# ==========================================

# --- RUTA 1: Listar Todos ---
@ubigeo_api.route('/', methods=['GET'])
@requires_auth(required_permission='view:ubigeo')
def get_all_ubigeos(payload):
    try:
        ubigeos = Ubigeo.query.limit(100).all()
        return jsonify([u.to_dict() for u in ubigeos])
    except Exception as e:
        return jsonify(error=str(e)), 500

# --- RUTA 2: Obtener Departamentos (ÚNICOS) ---
# Esta es la ruta que tu Frontend estaba buscando y daba 404
@ubigeo_api.route('/departamentos', methods=['GET'])
@requires_auth(required_permission='view:ubigeo')
def get_departamentos(payload):
    try:
        # Consulta inteligente: Agrupa por departamento y toma los primeros 2 dígitos del código
        # SELECT substr(ubigeo_inei, 1, 2) as code, departamento FROM ubigeo GROUP BY departamento ORDER BY departamento
        results = db.session.query(
            func.substr(Ubigeo.ubigeo_inei, 1, 2).label('code'),
            Ubigeo.departamento
        ).group_by(Ubigeo.departamento).order_by(Ubigeo.departamento).all()

        return jsonify([{'code': r.code, 'name': r.departamento} for r in results])
    except Exception as e:
        return jsonify(error=str(e)), 500

# --- RUTA 3: Obtener Hijos (Provincias o Distritos) ---
# Esta ruta maneja la cascada: Si le das Dept -> Devuelve Provincias. Si le das Prov -> Devuelve Distritos.
@ubigeo_api.route('/children/<string:parent_code>', methods=['GET'])
@requires_auth(required_permission='view:ubigeo')
def get_children(parent_code, payload):
    try:
        parent_code = parent_code.strip()

        # CASO A: Tenemos un Departamento (2 dígitos, ej: "15" Lima)
        # Queremos las PROVINCIAS que empiecen con "15"
        if len(parent_code) == 2:
            results = db.session.query(
                func.substr(Ubigeo.ubigeo_inei, 1, 4).label('code'),
                Ubigeo.provincia
            ).filter(Ubigeo.ubigeo_inei.like(f"{parent_code}%")) \
                .group_by(Ubigeo.provincia) \
                .order_by(Ubigeo.provincia).all()

            return jsonify([{'code': r.code, 'name': r.provincia} for r in results])

        # CASO B: Tenemos una Provincia (4 dígitos, ej: "1501" Lima)
        # Queremos los DISTRITOS que empiecen con "1501"
        elif len(parent_code) == 4:
            results = db.session.query(
                Ubigeo.ubigeo_inei.label('code'),
                Ubigeo.distrito
            ).filter(Ubigeo.ubigeo_inei.like(f"{parent_code}%")) \
                .order_by(Ubigeo.distrito).all()

            return jsonify([{'code': r.code, 'name': r.distrito} for r in results])

        return jsonify([])

    except Exception as e:
        return jsonify(error=str(e)), 500

# --- RUTA 4: Búsqueda Global ---
@ubigeo_api.route('/search', methods=['GET'])
@requires_auth(required_permission='view:ubigeo')
def search_ubigeo(payload):
    query = request.args.get('q', '')
    if len(query) < 3:
        return jsonify([])
    try:
        results = Ubigeo.query.filter(
            (Ubigeo.distrito.ilike(f'%{query}%')) |
            (Ubigeo.provincia.ilike(f'%{query}%')) |
            (Ubigeo.departamento.ilike(f'%{query}%')) |
            (Ubigeo.ubigeo_inei.ilike(f'%{query}%'))
        ).limit(20).all()
        return jsonify([u.to_dict() for u in results])
    except Exception as e:
        return jsonify(error=str(e)), 500

# ==========================================
#   RUTAS ADMINISTRATIVAS
# ==========================================

@ubigeo_api.route('/import', methods=['POST'], strict_slashes=False)
@requires_auth(required_permission='admin:system_setup')
def import_ubigeos(payload):
    # ... (MANTÉN TU CÓDIGO DE IMPORTACIÓN IGUAL QUE ANTES) ...
    # Solo pego la cabecera para no ocupar espacio, pero NO borres tu lógica de importación
    # Simplemente asegúrate de que el resto del archivo sigue igual abajo.
    print("--- INICIO IMPORTACION UBIGEOS ---")
    if 'file' not in request.files: return jsonify(error="No file"), 400
    file = request.files['file']

    try:
        filename = file.filename.lower()
        if filename.endswith('.csv'): df = pd.read_csv(file, encoding='utf-8') # Simplificado para el ejemplo
        else: df = pd.read_excel(file)

        df.columns = [col.upper().strip() for col in df.columns]
        new_records = 0

        for index, row in df.iterrows():
            code = str(row['UBIGEO_INEI']).strip().zfill(6)
            # Lógica simple de upsert
            existing = Ubigeo.query.filter_by(ubigeo_inei=code).first()
            if not existing:
                db.session.add(Ubigeo(
                    ubigeo_inei=code,
                    departamento=str(row['DEPARTAMENTO']).upper(),
                    provincia=str(row['PROVINCIA']).upper(),
                    distrito=str(row['DISTRITO']).upper()
                ))
                new_records += 1

        db.session.commit()
        return jsonify({"message": "Importado", "created": new_records})
    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500

# ==========================================
#   RUTAS CRUD RESTANTES
# ==========================================
# (Mantén tus rutas POST, PUT, DELETE igual que en tu archivo original)
@ubigeo_api.route('/', methods=['POST'])
@requires_auth(required_permission='admin:system_setup')
def create_ubigeo(payload):
    data = request.get_json()
    new_ubigeo = Ubigeo(
        ubigeo_inei=data['ubigeo_inei'],
        departamento=data['departamento'],
        provincia=data['provincia'],
        distrito=data['distrito']
    )
    db.session.add(new_ubigeo)
    db.session.commit()
    return jsonify(new_ubigeo.to_dict()), 201

@ubigeo_api.route('/<int:id>', methods=['DELETE'])
@requires_auth(required_permission='admin:system_setup')
def delete_ubigeo(id, payload):
    u = Ubigeo.query.get_or_404(id)
    db.session.delete(u)
    db.session.commit()
    return jsonify(message="Borrado")