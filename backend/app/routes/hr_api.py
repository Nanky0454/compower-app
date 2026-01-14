from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.employee import Employee
# from app.services.auth_service import require_auth # Placeholder for auth

hr_bp = Blueprint('hr_bp', __name__, url_prefix='/api/hr')

@hr_bp.route('/employees', methods=['GET'])
# @require_auth('view:employees') # Placeholder for auth
def get_employees():
    try:
        employees = Employee.query.all()
        return jsonify([employee.to_dict() for employee in employees]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@hr_bp.route('/employees', methods=['POST'])
# @require_auth('create:employees') # Placeholder for auth
def create_employee():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    try:
        from datetime import datetime

        def parse_date(date_str):
            if not date_str: return None
            return datetime.strptime(date_str, '%Y-%m-%d').date()

        new_employee = Employee(
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            document_type=data.get('document_type'),
            document_number=data.get('document_number'),
            position=data.get('position'),
            salary=data.get('salary'),
            start_date=parse_date(data.get('start_date')),
            birth_date=parse_date(data.get('birth_date')),
            phone=data.get('phone'),
            email=data.get('email')
        )
        db.session.add(new_employee)
        
        # Agregar licencias
        if 'licenses' in data and isinstance(data['licenses'], list):
            from app.models.employee import EmployeeLicense
            for lic in data['licenses']:
                new_lic = EmployeeLicense(
                    employee=new_employee,
                    license_number=lic.get('license_number'),
                    category=lic.get('category'),
                    expiration_date=parse_date(lic.get('expiration_date'))
                )
                db.session.add(new_lic)

        db.session.commit()
        return jsonify(new_employee.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# --- ASISTENCIA ---

@hr_bp.route('/attendance/upload', methods=['POST'])
def upload_attendance():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        from app.models.attendance import AttendanceRecord
        from datetime import datetime
        import requests
        from config import Config

        # Leer archivo línea por línea
        content = file.read().decode('utf-8')
        lines = content.splitlines()
        
        count = 0
        cutoff_date = datetime(2025, 11, 21)
        
        # Cache simple para no consultar la API repetidamente por el mismo DNI en una carga
        dni_cache = {}

        for line in lines:
            # Ignorar encabezados o líneas vacías
            if not line.strip() or "No" in line and "Mchn" in line:
                continue

            parts = line.split()
            if len(parts) < 6: continue

            doc_number = parts[2]
            
            # Fix: El log trae un 0 adelante extra (ej: 0406... -> 406...). 
            if len(doc_number) > 8 and doc_number.startswith('0'):
                doc_number = doc_number[1:]

            date_str = parts[-2]
            time_str = parts[-1]
            
            try:
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")
            except ValueError:
                continue 

            if dt < cutoff_date:
                continue

            # Buscar empleado localmente
            employee = Employee.query.filter_by(document_number=doc_number).first()
            external_name = None
            
            # Si no es empleado, intentar obtener nombre de API (si no está en cache)
            if not employee:
                if doc_number in dni_cache:
                    external_name = dni_cache[doc_number]
                else:
                    # Consultar API
                    # Verificar si ya existe un registro previo con nombre externo para ahorrar API calls
                    existing_record = AttendanceRecord.query.filter(
                        AttendanceRecord.document_number == doc_number,
                        AttendanceRecord.external_name != None
                    ).first()
                    
                    if existing_record:
                        external_name = existing_record.external_name
                        dni_cache[doc_number] = external_name
                    else:
                        # Llamada real a la API
                        try:
                            api_url = f"https://api.decolecta.com/v1/reniec/dni?numero={doc_number}"
                            headers = {'Authorization': f'Bearer {Config.SUNAT_API_KEY}'}
                            resp = requests.get(api_url, headers=headers, timeout=5)
                            if resp.status_code == 200:
                                data = resp.json()
                                # Construir nombre completo
                                # La API devuelve: first_name, first_last_name, second_last_name
                                full_name = f"{data.get('first_name', '')} {data.get('first_last_name', '')} {data.get('second_last_name', '')}".strip()
                                if full_name:
                                    external_name = full_name
                                    dni_cache[doc_number] = external_name
                        except Exception as e:
                            print(f"Error consultando API para DNI {doc_number}: {e}")

            # Verificar si ya existe el registro
            exists = AttendanceRecord.query.filter_by(
                document_number=doc_number, 
                timestamp=dt
            ).first()

            if not exists:
                record = AttendanceRecord(
                    employee_id=employee.id if employee else None,
                    document_number=doc_number,
                    timestamp=dt,
                    raw_data=line,
                    external_name=external_name # Guardar nombre externo
                )
                db.session.add(record)
                count += 1
        
        db.session.commit()
        return jsonify({'message': f'Se procesaron {count} registros nuevos.'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@hr_bp.route('/attendance', methods=['GET'])
def get_attendance():
    try:
        from app.models.attendance import AttendanceRecord
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        # Obtener todos los registros ordenados
        records = AttendanceRecord.query.order_by(AttendanceRecord.timestamp).all()
        
        # Agrupar en memoria
        data = {}
        
        # Hora de entrada esperada: 08:30:00
        EXPECTED_START = datetime.strptime("08:30:00", "%H:%M:%S").time()
        
        for r in records:
            dni = r.document_number
            date_key = r.timestamp.strftime('%Y-%m-%d')
            time_obj = r.timestamp.time()
            time_str = r.timestamp.strftime('%H:%M:%S')
            
            # Determinar nombre
            name = f"DNI: {dni}"
            if r.employee:
                name = f"{r.employee.first_name} {r.employee.last_name}"
            elif r.external_name:
                name = r.external_name
            
            if dni not in data:
                data[dni] = {
                    'employee_name': name,
                    'days': {}
                }
            
            if date_key not in data[dni]['days']:
                data[dni]['days'][date_key] = {
                    'first': time_str, 
                    'first_obj': time_obj,
                    'last': time_str,
                    'last_obj': time_obj
                }
            else:
                # Actualizar last si es mayor
                if time_obj > data[dni]['days'][date_key]['last_obj']:
                    data[dni]['days'][date_key]['last'] = time_str
                    data[dni]['days'][date_key]['last_obj'] = time_obj
                # Actualizar first si es menor
                if time_obj < data[dni]['days'][date_key]['first_obj']:
                    data[dni]['days'][date_key]['first'] = time_str
                    data[dni]['days'][date_key]['first_obj'] = time_obj

        # Calcular tardanzas y formatear
        result = []
        all_dates = set()
        
        for dni, info in data.items():
            row = {
                'employee': info['employee_name'],
                'dni': dni,
                'attendance': {}
            }
            for date_key, times in info['days'].items():
                all_dates.add(date_key)
                
                # Calcular tardanza
                delay_str = "00:00:00"
                if times['first_obj'] > EXPECTED_START:
                    # Calcular diferencia
                    dummy_date = datetime(2000, 1, 1)
                    t1 = datetime.combine(dummy_date, times['first_obj'])
                    t2 = datetime.combine(dummy_date, EXPECTED_START)
                    diff = t1 - t2
                    delay_str = str(diff)

                row['attendance'][date_key] = {
                    'ingreso': times['first'],
                    'salida': times['last'] if times['last'] != times['first'] else '',
                    'tardanza': delay_str
                }
            
            result.append(row)
            
        return jsonify({
            'dates': sorted(list(all_dates)),
            'employees': result
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- AGREGAR ESTO EN hr_api.py ---

@hr_bp.route('/drivers', methods=['GET'])
# @require_auth('view:employees')
def search_drivers():
    """Busca empleados que tengan Licencia de Conducir"""
    q = request.args.get('q', '').strip()

    try:
        from app.models.employee import Employee, EmployeeLicense

        # Hacemos JOIN para traer solo los que tienen licencia
        query = Employee.query.join(EmployeeLicense)

        if q:
            # Filtrar por Nombre, Apellido o DNI
            query = query.filter(
                (Employee.first_name.ilike(f'%{q}%')) |
                (Employee.last_name.ilike(f'%{q}%')) |
                (Employee.document_number.like(f'{q}%'))
            )

        # Distinct para no repetir si tienen varias licencias
        drivers = query.distinct().limit(20).all()

        return jsonify([d.to_dict() for d in drivers]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500