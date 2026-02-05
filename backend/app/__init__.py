import os
import requests  # <--- NUEVO
from datetime import date  # <--- NUEVO
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_apscheduler import APScheduler  # <--- NUEVO
from .extensions import db, cors
from config import Config

# --- 1. IMPORTACIÓN DE MODELOS ---
from .models.role import Role
from .models.permission import Permission
from .models.cost_center import CostCenter
from .models.provider import Provider
from .models.product_catalog import Category, Product
from .models.warehouse import Warehouse
from .models.inventory_models import InventoryStock, InventoryTransaction
from .models.purchase_order import PurchaseOrder, DocumentType, OrderStatus, PurchaseOrderItem
from .models.stock_transfer import StockTransfer, StockTransferItem
from .models.employee import Employee, EmployeeLicense
from .models.attendance import AttendanceRecord
from .models.reception import ProductReceipt, ProductReceiptItem
# Asegúrate de tener tu modelo ExchangeRate expuesto en tus modelos
# from .models.exchange_rate import ExchangeRate
from .services.auth_service import AuthError, requires_auth

# --- INICIALIZAR SCHEDULER (Global) ---
scheduler = APScheduler()


# --- FUNCIÓN DE TAREA AUTOMÁTICA ---
def tarea_actualizar_tipo_cambio():
    """Consulta la API de Decolecta y guarda el tipo de cambio."""
    with scheduler.app.app_context():
        # Importamos aquí dentro para evitar referencias circulares
        # AJUSTA ESTE IMPORT según dónde guardaste el modelo ExchangeRate
        from .models.exchange_rate import ExchangeRate, db
        from flask import current_app

        print("Ejecutando tarea automática de Tipo de Cambio...")

        hoy = date.today()
        try:
            api_key = current_app.config.get('SUNAT_API_KEY', '')
            url = "https://api.decolecta.com/v1/tipo-cambio/sunat"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            # Guardar en BD
            nuevo_cambio = ExchangeRate(
                currency='USD',
                buy_rate=data.get('compra') or data.get('buy_price'),
                sell_rate=data.get('venta') or data.get('sell_price'),
                date=hoy
            )

            db.session.add(nuevo_cambio)
            db.session.commit()
            print(f"ÉXITO: Tipo de cambio guardado. Venta: {nuevo_cambio.sell_rate}")

        except Exception as e:
            db.session.rollback()
            print(f"ERROR actualizando tipo de cambio: {str(e)}")


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    # --- 2. INICIALIZACIÓN DE EXTENSIONES ---
    db.init_app(app)
    migrate = Migrate(app, db)

    cors.init_app(
        app,
        resources={r"/api/*": {"origins": "*"}},
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["Authorization"],
        supports_credentials=True
    )

    # --- CONFIGURACIÓN E INICIO DEL SCHEDULER ---
    app.config['SCHEDULER_API_ENABLED'] = True
    scheduler.init_app(app)
    scheduler.start()

    # Agregar el trabajo (Job) para las 8:00 AM
    scheduler.add_job(
        id='actualizar_cambio_8am',
        func=tarea_actualizar_tipo_cambio,
        trigger='cron',
        hour=12,
        minute=45,
        replace_existing=True
    )

    # --- 3. REGISTRO DE BLUEPRINTS (Rutas) ---
    from .routes.main_api import main_api
    from .routes.admin_api import admin_api
    from .routes.cost_center_api import cost_center_api
    from .routes.purchase_api import purchase_api
    from .routes.product_api import product_api
    from .routes.inventory_api import inventory_api
    from .routes.warehouse_api import warehouse_api
    from .routes.category_api import category_api
    from .routes.transfer_api import transfer_api
    from .routes.gre_api import gre_bp
    from .routes.hr_api import hr_bp
    from .routes.location_api import location_api
    from .routes.ubigeo_api import ubigeo_api
    from .routes.treasury_api import treasury_api
    from .routes.unit_measure_api import unit_measure_api
    from .routes.stock_transfer_report_api import stock_transfer_report_api
    from .routes.report_api import report_api

    app.register_blueprint(transfer_api, url_prefix='/api/transfers')
    app.register_blueprint(warehouse_api, url_prefix='/api/warehouses')
    app.register_blueprint(category_api, url_prefix='/api/categories')
    app.register_blueprint(inventory_api, url_prefix='/api/inventory')
    app.register_blueprint(main_api, url_prefix='/api')
    app.register_blueprint(admin_api, url_prefix='/api/admin')
    app.register_blueprint(cost_center_api, url_prefix='/api/cost-centers')
    app.register_blueprint(purchase_api, url_prefix='/api/purchases')
    app.register_blueprint(product_api, url_prefix='/api/products')
    app.register_blueprint(gre_bp, url_prefix='/api/gre')
    app.register_blueprint(hr_bp, url_prefix='/api/hr')
    app.register_blueprint(location_api, url_prefix='/api/locations')
    app.register_blueprint(ubigeo_api, url_prefix='/api/ubigeos')
    app.register_blueprint(treasury_api, url_prefix='/api/treasury')
    app.register_blueprint(unit_measure_api, url_prefix='/api/units')
    app.register_blueprint(stock_transfer_report_api, url_prefix='/api')
    app.register_blueprint(report_api, url_prefix='/api/reports')

    # --- 4. MANEJADOR DE ERRORES ---
    @app.errorhandler(AuthError)
    def handle_auth_error(ex):
        response = jsonify(ex.error)
        response.status_code = ex.status_code
        return response

    # --- 5. CREACIÓN DE BASE DE DATOS Y SEEDING ---
    with app.app_context():
        os.makedirs(app.instance_path, exist_ok=True)
        db.create_all()
        _seed_database()

    return app


# --- FUNCIÓN DE SEEDING (Limpia) ---
def _seed_database():
    """
    Crea los roles, permisos y catálogos por defecto.
    """
    print("Verificando permisos...")
    permissions_list = [
        Permission(name='view:home', display_name='Novedades', description='Acceso a la página de bienvenida'),
        Permission(name='view:modulo_1', display_name='Módulo 1', description='Acceso al Módulo 1'),
        Permission(name='view:modulo_2', display_name='Módulo 2', description='Acceso al Módulo 2'),
        Permission(name='view:modulo_3', display_name='Módulo 3', description='Acceso al Módulo 3'),
        Permission(name='access:admin_panel', display_name='Panel de Admin', description='Acceso para gestionar roles'),
        Permission(name='view:cost_centers', display_name='Ver Centros de Costos',
                   description='Ver la lista de centros de costos'),
        Permission(name='create:cost_centers', display_name='Crear Centros de Costos',
                   description='Crear nuevos centros de costos'),
        Permission(name='edit:cost_centers', display_name='Editar Centros de Costos',
                   description='Editar centros de costos'),
        Permission(name='view:purchases', display_name='Ver Órdenes de Compra',
                   description='Ver la lista de órdenes de compra'),
        Permission(name='create:purchases', display_name='Crear Órdenes de Compra',
                   description='Crear nuevas órdenes de compra'),
        Permission(name='view:catalog', display_name='Ver Catálogo', description='Ver lista de productos y categorías'),
        Permission(name='manage:catalog', display_name='Gestionar Catálogo',
                   description='Crear/editar productos y categorías'),
        Permission(name='view:inventory', display_name='Ver Inventario', description='Ver stock actual'),
        Permission(name='manage:inventory', display_name='Gestionar Inventario',
                   description='Hacer recepciones y ajustes de stock'),
        Permission(name='view:transfers', display_name='Ver Movimientos de Stock',
                   description='Ver la lista de transferencias de stock'),
        Permission(name='manage:transfers', display_name='Gestionar Movimientos',
                   description='Crear transferencias y enviar GRE a SUNAT'),
        Permission(name='view:employees', display_name='Ver Empleados', description='Ver lista de empleados'),
        Permission(name='manage:employees', display_name='Gestionar Empleados',
                   description='Crear, editar y eliminar empleados'),
        Permission(name='admin:system_setup', display_name='Configuración del Sistema',
                   description='Acceso a configuración avanzada y cargas masivas'),
        Permission(name='view:ubigeo', display_name='Ver Ubigeos', description='Ver y buscar ubicaciones geográficas'),
        Permission(name='view:treasury', display_name='Ver Caja', description='Ver movimientos de caja'),
        Permission(name='manage:treasury', display_name='Gestionar Caja', description='Registrar ingresos y egresos')
    ]

    for perm in permissions_list:
        existing = Permission.query.filter_by(name=perm.name).first()
        if not existing:
            print(f"Creando permiso faltante: {perm.name}")
            db.session.add(perm)

    db.session.commit()

    if Category.query.count() == 0:
        print("Creando categorías por defecto...")
        cat_cables = Category(name='Cables', description='Cables eléctricos y de red')
        cat_herr = Category(name='Herramientas', description='Herramientas manuales')
        db.session.add_all([cat_cables, cat_herr])
        db.session.commit()

        prod_cable = Product(
            sku='CB-THW-14',
            name='CABLE/THW #14',
            unit_of_measure='Metros',
            standard_price=2.50,
            category_id=cat_cables.id
        )
        prod_clavo = Product(
            sku='HR-CLV-3',
            name='Clavos de 3"',
            unit_of_measure='Kilos',
            standard_price=15.00,
            category_id=cat_herr.id
        )
        db.session.add_all([prod_cable, prod_clavo])
        db.session.commit()

    if Warehouse.query.count() == 0:
        print("Creando almacenes por defecto...")
        db.session.add_all([
            Warehouse(name='Almacén Surco', location='Lima'),
            Warehouse(name='Almacén Cusco', location='Cusco')
        ])
        db.session.commit()

    if DocumentType.query.count() == 0:
        print("Creando tipos de documento...")
        db.session.add_all([
            DocumentType(name='Factura'),
            DocumentType(name='Orden de Compra'),
            DocumentType(name='Boleta')
        ])
        db.session.commit()

    if OrderStatus.query.count() == 0:
        print("Creando estados de orden...")
        db.session.add_all([
            OrderStatus(name='Borrador'),
            OrderStatus(name='Aprobada'),
            OrderStatus(name='Recibida')
        ])
        db.session.commit()

    permissions_map = {p.name: p for p in Permission.query.all()}

    admin_role = Role.query.filter_by(name='Admin').first()
    if admin_role is None:
        print("Creando rol 'Admin' por defecto...")
        admin_role = Role(name='Admin')
        db.session.add(admin_role)

    admin_role.permissions = list(permissions_map.values())
    db.session.commit()

    user_role = Role.query.filter_by(name='Usuario').first()
    if user_role is None:
        print("Creando rol 'Usuario' por defecto...")
        user_role = Role(name='Usuario')
        db.session.add(user_role)

    user_perms_names = [
        'view:home', 'view:modulo_1', 'view:cost_centers',
        'view:purchases', 'create:purchases', 'view:catalog', 'view:inventory',
        'view:transfers', 'manage:transfers', 'view:employees', 'view:ubigeo',
        'view:treasury', 'manage:treasury'
    ]
    user_perms = [permissions_map.get(name) for name in user_perms_names if permissions_map.get(name)]
    user_role.permissions = user_perms
    db.session.commit()