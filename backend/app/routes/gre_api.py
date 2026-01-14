from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import time
import base64
from sqlalchemy import func
import io
from flask import send_file

# --- IMPORTACIONES ---
from ..extensions import db
from ..services.auth_service import requires_auth
from ..services import gre_service

# Modelos
from ..models.stock_transfer import StockTransfer, StockTransferItem
from ..models.inventory_models import InventoryStock, InventoryTransaction
from ..models.product_catalog import Product, UnitMeasure
from ..models.warehouse import Warehouse
from ..models.gre import Gre, GreDetail
from ..models.ubigeo import Ubigeo  # <--- IMPORTANTE: Importar modelo Ubigeo

gre_bp = Blueprint('gre_api', __name__, url_prefix='/api/gre')


# ... (Las rutas 'next-correlative' se mantienen igual) ...
@gre_bp.route('/next-correlative', methods=['GET'])
@requires_auth(required_permission='manage:transfers')
def get_next_correlative(payload):
    serie = request.args.get('serie')
    if not serie: return jsonify({"next_number": 1})
    try:
        max_num = db.session.query(func.max(Gre.numero)).filter_by(serie=serie).scalar()
        return jsonify({"next_number": (max_num + 1) if max_num else 1})
    except Exception as e:
        return jsonify({"next_number": 1})


@gre_bp.route('/enviar', methods=['POST'])
@requires_auth(required_permission='manage:transfers')
def enviar_guia_endpoint(payload):
    datos_guia = request.get_json()
    user_id = payload['sub']
    tipo_gre = datos_guia.get('gre_type', 'remitente')

    print(f"\n--- 🚀 INICIANDO PROCESO GRE ({tipo_gre.upper()}) ---")

    access_token = gre_service.obtener_token_oauth2()
    if not access_token:
        return jsonify({"error": "Error al obtener el token de SUNAT"}), 401

    try:
        datos_guia['fecha_de_emision'] = datetime.strptime(datos_guia['fecha_de_emision'], '%Y-%m-%d').date()
        datos_guia['fecha_de_inicio_de_traslado'] = datetime.strptime(datos_guia['fecha_de_inicio_de_traslado'],
                                                                      '%Y-%m-%d').date()

        # 1. Crear XML
        xml_sin_firmar_bytes = gre_service.crear_xml_guia_remision(datos_guia)

        # 2. Firmar XML
        nombre_base_archivo = f"{datos_guia['serie']}-{datos_guia['numero']}"
        xml_firmado_bytes = gre_service.firmar_xml(xml_sin_firmar_bytes, nombre_base_archivo)

        # --- [MODIFICACIÓN] USAR EL SERVICIO PARA EXTRAER EL HASH ---
        # Esto es más limpio que poner 'from lxml...' aquí dentro
        digest_value = gre_service.extraer_digest_value(xml_firmado_bytes)
        print(f"--- 🔑 DigestValue extraído: {digest_value} ---")
        # ------------------------------------------------------------

        # 3. Guardar y Comprimir
        nombre_xml_firmado = f"{nombre_base_archivo}.xml"
        gre_service.guardar_xml_en_base(nombre_xml_firmado, xml_firmado_bytes, "XML FIRMADO")

        nombre_zip = f"{current_app.config['TU_RUC']}-09-{nombre_base_archivo}.zip"
        zip_base64, _, hash_zip = gre_service.comprimir_y_codificar_base64(xml_firmado_bytes, nombre_zip)

        # 4. Enviar
        respuesta_envio = gre_service.enviar_guia_sunat_oauth2(nombre_zip, zip_base64, access_token, hash_zip)

        if not respuesta_envio: return jsonify({"error": "Error sin respuesta de envío SUNAT"}), 500
        ticket_id = respuesta_envio.get('numTicket')
        if not ticket_id: return jsonify({"error": f"SUNAT no devolvió Ticket: {respuesta_envio}"}), 500

        print(f"--- Ticket {ticket_id}. Esperando... ---")

        # 5. Polling
        resultado_consulta = None
        for i in range(1, 4):
            time.sleep(3)
            resultado_consulta = gre_service.consultar_ticket_sunat(ticket_id, access_token)
            if resultado_consulta.get('codRespuesta') in ['0', '99']: break
            if resultado_consulta.get('codRespuesta') == '98': continue

        if not resultado_consulta: return jsonify({"error": "Timeout consultando ticket"}), 500

        # 6. Procesar Resultado
        cod_respuesta = resultado_consulta.get('codRespuesta')

        if cod_respuesta == '0':
            print(f"--- ✅ GRE Aceptada. ---")

            # --- [MODIFICACIÓN CLAVE] EXTACCIÓN DEL QR DEL CDR ---
            # Por defecto usamos el hash del XML (digest_value)
            dato_para_qr = digest_value

            if resultado_consulta.get('arcCdr'):
                cdr_b64 = resultado_consulta['arcCdr']

                # 1. Guardar el CDR físico (Tu código original)
                try:
                    gre_service.guardar_xml_en_base(f"R-{nombre_base_archivo}.zip",
                                                    base64.b64decode(cdr_b64), "CDR")
                except:
                    pass

                # 2. Intentar extraer la URL oficial del QR
                # Asegúrate de haber agregado 'extraer_url_qr_del_cdr' en gre_service
                url_oficial = gre_service.extraer_url_qr_del_cdr(cdr_b64)

                if url_oficial:
                    print(f"--- 🔗 URL Oficial QR detectada: {url_oficial} ---")
                    dato_para_qr = url_oficial
                else:
                    print("--- ⚠️ No se encontró URL en el CDR, usando Hash como respaldo ---")
            # -----------------------------------------------------

            try:
                # --- REGISTRO EN BD ---
                new_gre = Gre(
                    # ... (tus otros campos se mantienen igual) ...
                    serie=datos_guia['serie'],
                    numero=datos_guia['numero'],
                    fecha_de_emision=datos_guia['fecha_de_emision'],
                    fecha_de_inicio_de_traslado=datos_guia['fecha_de_inicio_de_traslado'],
                    cliente_tipo_de_documento=str(datos_guia['cliente_tipo_de_documento']),
                    cliente_numero_de_documento=datos_guia['cliente_numero_de_documento'],
                    cliente_denominacion=datos_guia['cliente_denominacion'],
                    gre_type=tipo_gre,
                    remitente_original_ruc=datos_guia.get('remitente_original_ruc'),
                    remitente_original_rs=datos_guia.get('remitente_original_rs'),
                    motivo_de_traslado=datos_guia['motivo_de_traslado'],
                    motivo=datos_guia.get('motivo'),
                    peso_bruto_total=datos_guia.get('peso_bruto_total', 0),
                    tipo_de_transporte=datos_guia['tipo_de_transporte'],
                    transportista_placa_numero=datos_guia.get('transportista_placa_numero'),
                    marca=datos_guia.get('marca'),
                    conductor_documento_tipo=datos_guia.get('conductor_documento_tipo'),
                    conductor_documento_numero=datos_guia.get('conductor_documento_numero'),
                    licencia=datos_guia.get('licencia'),
                    conductor_nombre=datos_guia.get('conductor_nombre'),
                    conductor_apellidos=datos_guia.get('conductor_apellidos'),
                    punto_de_partida_ubigeo=datos_guia['punto_de_partida_ubigeo'],
                    punto_de_partida_direccion=datos_guia['punto_de_partida_direccion'],
                    punto_de_llegada_ubigeo=datos_guia['punto_de_llegada_ubigeo'],
                    punto_de_llegada_direccion=datos_guia['punto_de_llegada_direccion'],

                    # [CAMBIO AQUÍ] Guardamos 'dato_para_qr' (URL o Hash) en lugar de solo 'digest_value'
                    xml_hash=dato_para_qr,

                    created_at=datetime.now()
                )
                db.session.add(new_gre)
                db.session.flush()

                for item in datos_guia['items']:
                    prod = Product.query.filter_by(sku=item.get('codigo')).first()
                    db.session.add(GreDetail(
                        gre_id=new_gre.id,
                        unidad_de_medida=item.get('unidad_de_medida', 'NIU'),
                        codigo=item.get('codigo'),
                        descripcion=item.get('descripcion'),
                        cantidad=item.get('cantidad', 0),
                        product_id=prod.id if prod else None
                    ))

                # --- LÓGICA DE STOCK (Igual que antes) ---
                origin_address = datos_guia.get('punto_de_partida_direccion')
                warehouse_origen = Warehouse.query.filter_by(address=origin_address).first()
                if not warehouse_origen and datos_guia.get('origin_warehouse_id'):
                    warehouse_origen = Warehouse.query.get(datos_guia.get('origin_warehouse_id'))

                if warehouse_origen:
                    new_transfer = StockTransfer(
                        user_id=user_id,
                        origin_warehouse_id=warehouse_origen.id,
                        destination_external_address=datos_guia.get('punto_de_llegada_direccion'),
                        status=f"Completada (GRE {tipo_gre.capitalize()})",
                        transfer_date=datetime.now(),
                        gre_series=datos_guia.get('serie'),
                        gre_number=datos_guia.get('numero'),
                        gre_ticket=ticket_id,
                        cost_center_id=datos_guia.get('cost_center_id')
                    )
                    db.session.add(new_transfer)
                    db.session.flush()

                    for item_data in datos_guia['items']:
                        item_sku = item_data.get('codigo')
                        qty = float(item_data.get('cantidad', 0))
                        product = Product.query.filter_by(sku=item_sku).first()

                        if product:
                            db.session.add(StockTransferItem(
                                transfer=new_transfer, product_id=product.id, quantity=qty,
                                product_name_snapshot=product.name, product_sku_snapshot=product.sku
                            ))

                            if tipo_gre == 'remitente':
                                stock_origen = InventoryStock.query.filter_by(product_id=product.id,
                                                                              warehouse_id=warehouse_origen.id).first()
                                current_qty = float(stock_origen.quantity) if stock_origen else 0
                                if stock_origen: stock_origen.quantity = current_qty - qty

                                db.session.add(InventoryTransaction(
                                    product_id=product.id, warehouse_id=warehouse_origen.id,
                                    quantity_change=-qty, new_quantity=current_qty - qty,
                                    type="Envío GRE Remitente", user_id=user_id,
                                    reference=f"GRE: {datos_guia.get('serie')}-{datos_guia.get('numero')}"
                                ))

                db.session.commit()
                resultado_consulta['transfer_id'] = new_transfer.id
                return jsonify(resultado_consulta), 200

            except Exception as db_error:
                db.session.rollback()
                print(f"Error BD: {db_error}")
                resultado_consulta['advertencia_interna'] = f"Error BD: {str(db_error)}"
                return jsonify(resultado_consulta), 500
        else:
            return jsonify({"error": f"SUNAT rechazó: {cod_respuesta}", "details": resultado_consulta}), 400

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@gre_bp.route('/download-pdf/<int:transfer_id>', methods=['GET'])
@requires_auth(required_permission='view:transfers')
def download_gre_pdf(payload, transfer_id):
    transfer = StockTransfer.query.get_or_404(transfer_id)
    if not transfer.gre_series or not transfer.gre_number:
        return jsonify({"error": "Sin GRE asociada"}), 400

    gre_record = Gre.query.filter_by(serie=transfer.gre_series, numero=transfer.gre_number).first()
    if not gre_record: return jsonify({"error": "Datos fiscales no encontrados"}), 404

    try:
        # 1. Resolver Texto Ubigeo
        def get_ubigeo_texto(codigo):
            if not codigo: return ""
            # Nota: Mantenemos tu campo 'ubigeo_inei' que veo en tu código
            ubi = Ubigeo.query.filter_by(ubigeo_inei=codigo).first()
            if ubi:
                # Nota: Asumo que tus campos son departamento, provincia, distrito (minúsculas)
                # Si en tu BD son mayúsculas, cámbialo aquí.
                return f"{ubi.departamento} - {ubi.provincia} - {ubi.distrito}"
            return codigo

        txt_partida = get_ubigeo_texto(gre_record.punto_de_partida_ubigeo)
        txt_llegada = get_ubigeo_texto(gre_record.punto_de_llegada_ubigeo)

        # 2. Limpiar Motivo ("01" -> "1")
        motivo_clean = str(
            int(gre_record.motivo_de_traslado)) if gre_record.motivo_de_traslado.isdigit() else gre_record.motivo_de_traslado

        datos_guia = {
            'serie': gre_record.serie,
            'numero': int(gre_record.numero),
            'fecha_de_emision': gre_record.fecha_de_emision,
            'fecha_de_inicio_de_traslado': gre_record.fecha_de_inicio_de_traslado,

            # --- [MODIFICACIÓN] CONCATENAMOS AQUÍ LA DIRECCIÓN Y EL UBIGEO ---
            # Esto es vital para que salga "Dirección (Lima - Lima - Lima)" en el PDF
            'punto_de_partida_direccion': f"{gre_record.punto_de_partida_direccion} \n({txt_partida})",
            'punto_de_llegada_direccion': f"{gre_record.punto_de_llegada_direccion} \n({txt_llegada})",
            'punto_de_partida_ubigeo': "",  # Ya lo unimos arriba
            'punto_de_llegada_ubigeo': "",
            # ----------------------------------------------------------------

            'cliente_denominacion': gre_record.cliente_denominacion,
            'cliente_tipo_de_documento': gre_record.cliente_tipo_de_documento,
            'cliente_numero_de_documento': gre_record.cliente_numero_de_documento,

            'motivo_de_traslado': motivo_clean,
            'motivo': gre_record.motivo,

            'transportista_placa_numero': gre_record.transportista_placa_numero,
            'marca': gre_record.marca,
            'licencia': gre_record.licencia,
            'conductor_nombre': gre_record.conductor_nombre,
            'conductor_apellidos': gre_record.conductor_apellidos,
            'observaciones': 'REIMPRESIÓN DESDE SISTEMA',
            'items': []
        }

        # Asegúrate de importar el modelo UnitMeasure al inicio de tu archivo
        # from ..models.unit_measure import UnitMeasure

        detalles = GreDetail.query.filter_by(gre_id=gre_record.id).all()
        for d in detalles:
            # 1. Valor por defecto (ej: NIU)
            unidad_visual = d.unidad_de_medida

            # 2. Buscamos la equivalencia en tu tabla UnitMeasure
            # Buscamos donde sunat_code sea "NIU"
            medida = UnitMeasure.query.filter_by(sunat_code=unidad_visual).first()

            # 3. Si encontramos la medida, tomamos el 'symbol' (UND)
            if medida:
                unidad_visual = medida.symbol

            datos_guia['items'].append({
                'codigo': d.codigo,
                'descripcion': d.descripcion,
                'cantidad': float(d.cantidad),
                'unidad': unidad_visual  # Ahora será "UND"
            })

        # 3. Usar el Hash Real para el QR
        hash_real = gre_record.xml_hash if hasattr(gre_record,
                                                   'xml_hash') and gre_record.xml_hash else "HASH-NO-DISPONIBLE"

        pdf_bytes = gre_service.generar_pdf_guia(datos_guia, hash_real)

        if not pdf_bytes: return jsonify({"error": "Falló generación PDF"}), 500

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"GRE-{gre_record.serie}-{gre_record.numero}.pdf"
        )

    except Exception as e:
        print(f"Error descargando PDF: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500