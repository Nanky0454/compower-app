from flask import Blueprint, jsonify, request
from ..extensions import db
from sqlalchemy.orm import joinedload
from ..services.auth_service import requires_auth
from datetime import datetime

# Importamos TODOS los modelos que necesitamos
from ..models.stock_transfer import StockTransfer, StockTransferItem
from ..models.inventory_models import InventoryStock, InventoryTransaction
from ..models.product_catalog import Product
from ..models.warehouse import Warehouse
from ..models.stock_return import StockReturn, StockReturnItem
from decimal import Decimal


transfer_api = Blueprint('transfer_api', __name__)


# --- RUTA 1: Obtener TODAS las transferencias ---
@transfer_api.route('/', methods=['GET'], strict_slashes=False)
@requires_auth(required_permission='view:transfers')
def get_transfers(payload):
    """Devuelve una lista de todas las transferencias."""
    try:
        transfers = StockTransfer.query.options(
            joinedload(StockTransfer.origin_warehouse),
            joinedload(StockTransfer.destination_warehouse)
        ).order_by(StockTransfer.id.desc()).all()

        return jsonify([t.to_dict() for t in transfers])
    except Exception as e:
        return jsonify(error=str(e)), 500


# --- RUTA 2: Crear una nueva transferencia (SIN GRE) ---
@transfer_api.route('/', methods=['POST'], strict_slashes=False)
@requires_auth(required_permission='manage:transfers')
def create_transfer(payload):
    data = request.get_json()
    user_id = payload['sub']

    # 1. Validaciones de estructura
    transfer_data = data.get('transfer_data')
    if not transfer_data:
        return jsonify(error="Falta el objeto 'transfer_data'"), 400

    if not transfer_data.get('origin_warehouse_id') or not transfer_data.get('items'):
        return jsonify(error="Faltan 'origin_warehouse_id' o 'items'"), 400

    try:
        # --- 2. Crear la Cabecera (Transferencia) ---
        new_transfer = StockTransfer(
            user_id=user_id,
            origin_warehouse_id=transfer_data['origin_warehouse_id'],
            destination_warehouse_id=transfer_data.get('destination_warehouse_id'),
            destination_external_address=transfer_data.get('destination_external_address'),

            # AQUI YA ESTÁ CORRECTO EL CENTRO DE COSTOS:
            cost_center_id=transfer_data.get('cost_center_id'),

            status="Completada",
            transfer_date=datetime.now()
        )
        db.session.add(new_transfer)

        # Hacemos flush para obtener el ID de la transferencia antes de guardar items
        db.session.flush()

        # --- 3. Crear los items y mover el stock ---
        for item_data in transfer_data['items']:
            product_id = item_data['product_id']
            quantity = float(item_data['quantity'])

            if quantity <= 0:
                raise ValueError("La cantidad debe ser mayor a 0.")

            # Verificamos que el producto exista
            product = Product.query.get(product_id)
            if not product:
                raise ValueError(f"Producto ID {product_id} no encontrado.")

            # --- ¡MODIFICACIÓN AQUÍ! Guardamos los Snapshots ---
            new_item = StockTransferItem(
                transfer_id=new_transfer.id,  # Usamos el ID generado por el flush
                product_id=product_id,
                quantity=quantity,
                # Guardamos el nombre y SKU actuales como "foto" histórica
                product_name_snapshot=product.name,
                product_sku_snapshot=product.sku
            )
            db.session.add(new_item)
            # --------------------------------------------------

            # --- Lógica de Stock (Salida del Origen) ---
            stock_origen = InventoryStock.query.filter_by(
                product_id=product_id,
                warehouse_id=transfer_data['origin_warehouse_id']
            ).first()

            if not stock_origen or float(stock_origen.quantity) < quantity:
                raise ValueError(f"Stock insuficiente para {product.name} en el almacén de origen.")

            stock_origen.quantity = float(stock_origen.quantity) - quantity

            trans_salida = InventoryTransaction(
                product_id=product_id,
                warehouse_id=transfer_data['origin_warehouse_id'],
                quantity_change=-quantity,
                new_quantity=stock_origen.quantity,
                type="Transferencia Salida",
                user_id=user_id
            )
            db.session.add(trans_salida)

            # --- Lógica de Stock (Entrada al Destino - Solo si es almacén interno) ---
            if new_transfer.destination_warehouse_id:
                stock_destino = InventoryStock.query.filter_by(
                    product_id=product_id,
                    warehouse_id=new_transfer.destination_warehouse_id
                ).first()

                if not stock_destino:
                    stock_destino = InventoryStock(product_id=product_id,
                                                   warehouse_id=new_transfer.destination_warehouse_id, quantity=0.0)
                    db.session.add(stock_destino)

                stock_destino.quantity = float(stock_destino.quantity) + quantity

                trans_entrada = InventoryTransaction(
                    product_id=product_id,
                    warehouse_id=new_transfer.destination_warehouse_id,
                    quantity_change=quantity,
                    new_quantity=stock_destino.quantity,
                    type="Transferencia Entrada",
                    user_id=user_id
                )
                db.session.add(trans_entrada)

        # 4. Guardar todo
        db.session.commit()

        print(f"--- Transferencia ID {new_transfer.id} creada exitosamente. ---")
        return jsonify(new_transfer.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        print(f"--- ERROR AL CREAR TRANSFERENCIA: {str(e)} ---")
        return jsonify(error=str(e)), 500


# --- RUTA 3: Obtener el detalle de UNA transferencia ---
@transfer_api.route('/<int:transfer_id>', methods=['GET'])
@requires_auth(required_permission='view:transfers')
def get_transfer_detail(transfer_id, payload):
    """Devuelve el detalle de una transferencia específica."""
    try:
        transfer = StockTransfer.query.options(
            joinedload(StockTransfer.origin_warehouse),
            joinedload(StockTransfer.destination_warehouse),
            joinedload(StockTransfer.items).joinedload(StockTransferItem.product)
        ).get(transfer_id)

        if not transfer:
            return jsonify(error="Transferencia no encontrada"), 404

        return jsonify(transfer.to_dict())
    except Exception as e:
        print(f"--- ERROR OBTENIENDO DETALLE DE TRANSFERENCIA: {e} ---")
        return jsonify(error=str(e)), 500


# --- RUTA 4: Devolver stock de una transferencia ---
@transfer_api.route('/<int:transfer_id>/return', methods=['POST'])
@requires_auth(required_permission='manage:transfers')
def return_stock(transfer_id, payload):
    data = request.get_json()
    user_id = payload['sub']
    items_to_return = data.get('items')

    if not items_to_return:
        return jsonify(error="No se especificaron items para devolver"), 400

    try:
        transfer = StockTransfer.query.get_or_404(transfer_id)
        if transfer.status == 'Anulada':
            return jsonify(error="No se puede devolver stock de una transferencia anulada"), 400

        new_return = StockReturn(
            transfer_id=transfer.id,
            user_id=user_id
        )
        db.session.add(new_return)
        db.session.flush()

        for item_data in items_to_return:
            transfer_item_id = item_data.get('id')
            return_quantity = Decimal(item_data.get('return_quantity', 0))

            if return_quantity <= 0:
                continue

            transfer_item = StockTransferItem.query.get(transfer_item_id)
            if not transfer_item or transfer_item.transfer_id != transfer.id:
                raise ValueError(f"Item de transferencia ID {transfer_item_id} no es válido para esta transferencia.")

            # Validar que no se devuelve más de lo que se envió
            available_to_return = transfer_item.quantity - transfer_item.returned_quantity
            if return_quantity > available_to_return:
                raise ValueError(f"Intenta devolver {return_quantity} pero solo puede devolver {available_to_return} para el producto {transfer_item.product.name}.")

            # Actualizar la cantidad devuelta en el item de la transferencia
            transfer_item.returned_quantity += return_quantity

            # Crear el item de la devolución
            return_item = StockReturnItem(
                stock_return_id=new_return.id,
                product_id=transfer_item.product_id,
                quantity=return_quantity
            )
            db.session.add(return_item)

            # Lógica de reingreso de stock al almacén de origen
            stock_origen = InventoryStock.query.filter_by(
                product_id=transfer_item.product_id,
                warehouse_id=transfer.origin_warehouse_id
            ).first()

            if not stock_origen:
                # Esto no debería pasar si la transferencia se hizo correctamente
                stock_origen = InventoryStock(
                    product_id=transfer_item.product_id,
                    warehouse_id=transfer.origin_warehouse_id,
                    quantity=0
                )
                db.session.add(stock_origen)

            new_stock_quantity = stock_origen.quantity + return_quantity
            stock_origen.quantity = new_stock_quantity

            # Registrar la transacción de devolución en el kardex
            trans_devolucion = InventoryTransaction(
                product_id=transfer_item.product_id,
                warehouse_id=transfer.origin_warehouse_id,
                quantity_change=return_quantity,
                new_quantity=new_stock_quantity,
                type="Devolución de Stock",
                user_id=user_id,
                reference=f"Retorno de GRE-{transfer.gre_series}-{transfer.gre_number}"
            )
            db.session.add(trans_devolucion)

        db.session.commit()
        return jsonify(success=True, message="Stock devuelto correctamente."), 200

    except ValueError as ve:
        db.session.rollback()
        return jsonify(error=str(ve)), 400
    except Exception as e:
        db.session.rollback()
        print(f"--- ERROR AL DEVOLVER STOCK: {str(e)} ---")
        return jsonify(error=str(e)), 500