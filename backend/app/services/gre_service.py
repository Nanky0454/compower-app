import os
import io
import base64
import qrcode
import traceback
from lxml import etree
from flask import current_app, render_template
from weasyprint import HTML
import requests
from signxml import XMLSigner, methods
import zipfile
import hashlib
from datetime import datetime
import urllib.parse  # <--- IMPORTANTE: Para codificar el hash en la URL

# --- Namespaces para XML ---
NSMAP = {
    None: "urn:oasis:names:specification:ubl:schema:xsd:DespatchAdvice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance"
}


# ==============================================================================
# A. FUNCIONES DE UTILIDAD (HASH Y DIGEST)
# ==============================================================================

def extraer_digest_value(xml_firmado_bytes):
    """
    Lee el XML firmado y extrae el <ds:DigestValue> de la firma.
    Se añade .strip() para evitar espacios en blanco que rompen el QR.
    """
    try:
        root = etree.fromstring(xml_firmado_bytes)
        # Buscamos el nodo DigestValue dentro de la firma
        digest_node = root.find('.//ds:DigestValue', namespaces=NSMAP)
        if digest_node is not None and digest_node.text:
            return digest_node.text.strip()  # <--- CORRECCIÓN: .strip() elimina espacios
        return "NO-DIGEST-FOUND"
    except Exception as e:
        print(f"Error extrayendo DigestValue: {e}")
        return "ERROR-DIGEST"


def extraer_url_qr_del_cdr(cdr_base64):
    """
    Recibe el CDR (ZIP en base64), lo descomprime, lee el XML de respuesta
    y busca la etiqueta cbc:DocumentDescription que contiene la URL del QR.
    """
    try:
        if not cdr_base64:
            return None

        # 1. Decodificar Base64
        cdr_zip_bytes = base64.b64decode(cdr_base64)

        # 2. Abrir ZIP en memoria
        with zipfile.ZipFile(io.BytesIO(cdr_zip_bytes), 'r') as zf:
            # Buscar el archivo XML dentro del ZIP (suele terminar en .xml)
            nombre_xml = next((n for n in zf.namelist() if n.lower().endswith('.xml')), None)
            if not nombre_xml:
                return None

            xml_content = zf.read(nombre_xml)

        # 3. Parsear XML del CDR
        root_cdr = etree.fromstring(xml_content)

        # Namespaces específicos del CDR (ApplicationResponse)
        ns_cdr = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'
        }

        # 4. Buscar la URL en cbc:DocumentDescription
        # SUNAT coloca la URL del QR en esta etiqueta dentro del CDR
        node_url = root_cdr.find('.//cbc:DocumentDescription', namespaces=ns_cdr)

        if node_url is not None and node_url.text:
            return node_url.text.strip()  # Limpiamos espacios

        return None

    except Exception as e:
        print(f"Error extrayendo URL del CDR: {e}")
        return None

def guardar_xml_en_base(nombre_archivo, xml_contenido_bytes, subcarpeta="XML FIRMADO"):
    """
    Guarda el archivo en: backend/GRE/{subcarpeta}/nombre_archivo
    """
    try:
        ruta_backend = os.path.dirname(current_app.root_path)
        ruta_base_gre = os.path.join(ruta_backend, 'GRE', subcarpeta)
        os.makedirs(ruta_base_gre, exist_ok=True)

        ruta_completa = os.path.join(ruta_base_gre, nombre_archivo)
        with open(ruta_completa, 'wb') as f:
            f.write(xml_contenido_bytes)
        return ruta_completa
    except Exception as e:
        print(f"Error guardando archivo: {e}")
        return None


# ==============================================================================
# B. LÓGICA DE NEGOCIO (TOKEN, XML, ENVÍO)
# ==============================================================================

def obtener_token_oauth2():
    try:
        client_id = current_app.config['SUNAT_CLIENT_ID']
        client_secret = current_app.config['SUNAT_CLIENT_SECRET']
        ruc = current_app.config['TU_RUC']
        sol_user = current_app.config['SUNAT_SOL_USER']
        sol_pass = current_app.config['SUNAT_SOL_PASS']

        username_completo = f"{ruc}{sol_user}"
        token_url = f'https://api-seguridad.sunat.gob.pe/v1/clientessol/{client_id}/oauth2/token/'

        data = {
            'grant_type': 'password',
            'scope': 'https://api.sunat.gob.pe/v1/contribuyente/contribuyentes',
            'client_id': client_id,
            'client_secret': client_secret,
            'username': username_completo,
            'password': sol_pass
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        response = requests.post(token_url, data=data, headers=headers)
        if response.status_code == 200:
            return response.json().get('access_token')
        print(f"Error Token SUNAT: {response.text}")
        return None
    except Exception as e:
        print(f"Excepción Token: {e}")
        return None


def crear_xml_guia_remision(datos_guia):
    # NOTA: Aunque en la BD sea 'transportista', para SUNAT generaremos SIEMPRE 'remitente' (09)

    tipo_gre_sunat = "09"  # Forzamos Tipo 09 (Guía Remitente)

    # --- 1. CONFIGURACIÓN DE ACTORES ---
    signer_ruc = current_app.config['TU_RUC']
    signer_rs = current_app.config['TU_RAZON_SOCIAL']

    # En tipo 09, el Emisor y el Remitente son la misma entidad (TÚ)
    emisor_doc_ruc = signer_ruc
    emisor_doc_rs = signer_rs

    # --- 2. CONSTRUCCIÓN DEL XML ---
    root = etree.Element(etree.QName(NSMAP[None], "DespatchAdvice"), nsmap=NSMAP)

    # Extensiones
    ext_ubl = etree.SubElement(root, etree.QName(NSMAP["ext"], "UBLExtensions"))
    ext_sig = etree.SubElement(ext_ubl, etree.QName(NSMAP["ext"], "UBLExtension"))
    etree.SubElement(ext_sig, etree.QName(NSMAP["ext"], "ExtensionContent"))

    # Cabeceras
    etree.SubElement(root, etree.QName(NSMAP["cbc"], "UBLVersionID")).text = "2.1"
    etree.SubElement(root, etree.QName(NSMAP["cbc"], "CustomizationID")).text = "2.0"
    etree.SubElement(root, etree.QName(NSMAP["cbc"], "ID")).text = f"{datos_guia['serie']}-{datos_guia['numero']}"
    etree.SubElement(root, etree.QName(NSMAP["cbc"], "IssueDate")).text = datos_guia['fecha_de_emision'].strftime(
        '%Y-%m-%d')
    etree.SubElement(root, etree.QName(NSMAP["cbc"], "IssueTime")).text = datetime.now().strftime('%H:%M:%S')
    etree.SubElement(root, etree.QName(NSMAP["cbc"], "DespatchAdviceTypeCode")).text = tipo_gre_sunat

    if datos_guia.get('observaciones'):
        etree.SubElement(root, etree.QName(NSMAP["cbc"], "Note")).text = datos_guia['observaciones']

    # --- 3. FIRMA (Placeholder) ---
    sig_block = etree.SubElement(root, etree.QName(NSMAP["cac"], "Signature"))
    etree.SubElement(sig_block, etree.QName(NSMAP["cbc"], "ID")).text = signer_ruc
    sig_party = etree.SubElement(sig_block, etree.QName(NSMAP["cac"], "SignatoryParty"))
    sig_party_id = etree.SubElement(sig_party, etree.QName(NSMAP["cac"], "PartyIdentification"))
    etree.SubElement(sig_party_id, etree.QName(NSMAP["cbc"], "ID")).text = signer_ruc
    sig_party_name = etree.SubElement(sig_party, etree.QName(NSMAP["cac"], "PartyName"))
    etree.SubElement(sig_party_name, etree.QName(NSMAP["cbc"], "Name")).text = signer_rs
    sig_attach = etree.SubElement(sig_block, etree.QName(NSMAP["cac"], "DigitalSignatureAttachment"))
    sig_ext_ref = etree.SubElement(sig_attach, etree.QName(NSMAP["cac"], "ExternalReference"))
    etree.SubElement(sig_ext_ref, etree.QName(NSMAP["cbc"], "URI")).text = "#Sign"

    # --- 4. DESPATCH SUPPLIER PARTY (Emisor) ---
    supplier_party = etree.SubElement(root, etree.QName(NSMAP["cac"], "DespatchSupplierParty"))
    etree.SubElement(supplier_party, etree.QName(NSMAP["cbc"], "CustomerAssignedAccountID"),
                     schemeID="6").text = emisor_doc_ruc
    party_supplier = etree.SubElement(supplier_party, etree.QName(NSMAP["cac"], "Party"))
    party_id_supplier = etree.SubElement(party_supplier, etree.QName(NSMAP["cac"], "PartyIdentification"))
    etree.SubElement(party_id_supplier, etree.QName(NSMAP["cbc"], "ID"), schemeID="6",
                     schemeName="Documento de Identidad", schemeAgencyName="PE:SUNAT",
                     schemeURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06").text = emisor_doc_ruc
    party_legal_supplier = etree.SubElement(party_supplier, etree.QName(NSMAP["cac"], "PartyLegalEntity"))
    etree.SubElement(party_legal_supplier, etree.QName(NSMAP["cbc"], "RegistrationName")).text = emisor_doc_rs

    # --- 5. DESTINATARIO ---
    customer_party = etree.SubElement(root, etree.QName(NSMAP["cac"], "DeliveryCustomerParty"))
    party_customer = etree.SubElement(customer_party, etree.QName(NSMAP["cac"], "Party"))
    party_id_customer = etree.SubElement(party_customer, etree.QName(NSMAP["cac"], "PartyIdentification"))
    etree.SubElement(party_id_customer, etree.QName(NSMAP["cbc"], "ID"),
                     schemeID=str(datos_guia['cliente_tipo_de_documento'])).text = datos_guia[
        'cliente_numero_de_documento']
    party_legal_customer = etree.SubElement(party_customer, etree.QName(NSMAP["cac"], "PartyLegalEntity"))
    etree.SubElement(party_legal_customer, etree.QName(NSMAP["cbc"], "RegistrationName")).text = datos_guia[
        'cliente_denominacion']

    # --- 7. SHIPMENT ---
    shipment = etree.SubElement(root, etree.QName(NSMAP["cac"], "Shipment"))
    etree.SubElement(shipment, etree.QName(NSMAP["cbc"], "ID")).text = "SUNAT_Envio"
    etree.SubElement(shipment, etree.QName(NSMAP["cbc"], "HandlingCode"), listAgencyName="PE:SUNAT",
                     listName="Motivo de traslado", listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo20").text = \
    datos_guia['motivo_de_traslado']
    etree.SubElement(shipment, etree.QName(NSMAP["cbc"], "HandlingInstructions")).text = datos_guia.get('motivo',
                                                                                                        'TRASLADO')
    etree.SubElement(shipment, etree.QName(NSMAP["cbc"], "GrossWeightMeasure"), unitCode="KGM").text = str(
        datos_guia['peso_bruto_total'])

    shipment_stage = etree.SubElement(shipment, etree.QName(NSMAP["cac"], "ShipmentStage"))
    etree.SubElement(shipment_stage, etree.QName(NSMAP["cbc"], "TransportModeCode"), listName="Modalidad de traslado",
                     listAgencyName="PE:SUNAT", listURI="urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo18").text = \
    datos_guia['tipo_de_transporte']

    transit_period = etree.SubElement(shipment_stage, etree.QName(NSMAP["cac"], "TransitPeriod"))
    etree.SubElement(transit_period, etree.QName(NSMAP["cbc"], "StartDate")).text = datos_guia[
        'fecha_de_inicio_de_traslado'].strftime('%Y-%m-%d')

    # === LÓGICA DE TRANSPORTE ===
    if datos_guia['tipo_de_transporte'] == '01':
        # Transporte PÚBLICO
        carrier_party = etree.SubElement(shipment_stage, etree.QName(NSMAP["cac"], "CarrierParty"))
        party_id_carrier = etree.SubElement(carrier_party, etree.QName(NSMAP["cac"], "PartyIdentification"))
        etree.SubElement(party_id_carrier, etree.QName(NSMAP["cbc"], "ID"), schemeID="6").text = datos_guia[
            'transportista_documento_numero']
        party_legal_carrier = etree.SubElement(carrier_party, etree.QName(NSMAP["cac"], "PartyLegalEntity"))
        etree.SubElement(party_legal_carrier, etree.QName(NSMAP["cbc"], "RegistrationName")).text = datos_guia[
            'transportista_denominacion']

    elif datos_guia['tipo_de_transporte'] == '02':
        # Transporte PRIVADO
        transport_means = etree.SubElement(shipment_stage, etree.QName(NSMAP["cac"], "TransportMeans"))
        road_transport = etree.SubElement(transport_means, etree.QName(NSMAP["cac"], "RoadTransport"))

        # Limpieza de placa
        placa_raw = datos_guia.get('transportista_placa_numero', '')
        placa_clean = str(placa_raw).replace('-', '').replace(' ', '').strip()
        if not placa_clean:
            placa_clean = "000000"

        etree.SubElement(road_transport, etree.QName(NSMAP["cbc"], "LicensePlateID")).text = placa_clean

        # Conductor
        driver_person = etree.SubElement(shipment_stage, etree.QName(NSMAP["cac"], "DriverPerson"))
        etree.SubElement(driver_person, etree.QName(NSMAP["cbc"], "ID"),
                         schemeID=str(datos_guia.get('conductor_documento_tipo', '1'))).text = datos_guia.get(
            'conductor_documento_numero')
        etree.SubElement(driver_person, etree.QName(NSMAP["cbc"], "FirstName")).text = datos_guia.get(
            'conductor_nombre', '')
        etree.SubElement(driver_person, etree.QName(NSMAP["cbc"], "FamilyName")).text = datos_guia.get(
            'conductor_apellidos', '')

        # --- AGREGADO SEGÚN LA GUÍA DE REFERENCIA ---
        etree.SubElement(driver_person, etree.QName(NSMAP["cbc"], "JobTitle")).text = "Principal"

        if datos_guia.get('licencia'):
            licence = etree.SubElement(driver_person, etree.QName(NSMAP["cac"], "IdentityDocumentReference"))
            etree.SubElement(licence, etree.QName(NSMAP["cbc"], "ID")).text = datos_guia['licencia']

    # --- 8. DELIVERY Y DESPATCH ---
    delivery_block = etree.SubElement(shipment, etree.QName(NSMAP["cac"], "Delivery"))
    delivery_address = etree.SubElement(delivery_block, etree.QName(NSMAP["cac"], "DeliveryAddress"))
    etree.SubElement(delivery_address, etree.QName(NSMAP["cbc"], "ID"), schemeAgencyName="PE:INEI",
                     schemeName="Ubigeos").text = datos_guia['punto_de_llegada_ubigeo']
    delivery_address_line = etree.SubElement(delivery_address, etree.QName(NSMAP["cac"], "AddressLine"))
    etree.SubElement(delivery_address_line, etree.QName(NSMAP["cbc"], "Line")).text = datos_guia[
        'punto_de_llegada_direccion']

    despatch_block = etree.SubElement(delivery_block, etree.QName(NSMAP["cac"], "Despatch"))
    despatch_address = etree.SubElement(despatch_block, etree.QName(NSMAP["cac"], "DespatchAddress"))
    etree.SubElement(despatch_address, etree.QName(NSMAP["cbc"], "ID"), schemeAgencyName="PE:INEI",
                     schemeName="Ubigeos").text = datos_guia['punto_de_partida_ubigeo']
    despatch_address_line = etree.SubElement(despatch_address, etree.QName(NSMAP["cac"], "AddressLine"))
    etree.SubElement(despatch_address_line, etree.QName(NSMAP["cbc"], "Line")).text = datos_guia[
        'punto_de_partida_direccion']

    # --- 9. EQUIPAMIENTO (Si es privado, se repite placa como HandlingUnit) ---
    if datos_guia['tipo_de_transporte'] == '02':
        handling_unit = etree.SubElement(shipment, etree.QName(NSMAP["cac"], "TransportHandlingUnit"))
        equipment = etree.SubElement(handling_unit, etree.QName(NSMAP["cac"], "TransportEquipment"))

        placa_eq = str(datos_guia.get('transportista_placa_numero', '')).replace('-', '').replace(' ', '').strip()
        if not placa_eq: placa_eq = "000000"

        etree.SubElement(equipment, etree.QName(NSMAP["cbc"], "ID")).text = placa_eq

    # --- 10. ITEMS ---
    line_count = 0
    for item_data in datos_guia.get('items', []):
        line_count += 1
        despatch_line = etree.SubElement(root, etree.QName(NSMAP["cac"], "DespatchLine"))
        etree.SubElement(despatch_line, etree.QName(NSMAP["cbc"], "ID")).text = str(line_count)
        etree.SubElement(despatch_line, etree.QName(NSMAP["cbc"], "DeliveredQuantity"),
                         unitCode=item_data.get('unidad_de_medida', 'NIU')).text = str(item_data['cantidad'])

        order_line_ref = etree.SubElement(despatch_line, etree.QName(NSMAP["cac"], "OrderLineReference"))
        etree.SubElement(order_line_ref, etree.QName(NSMAP["cbc"], "LineID")).text = str(line_count + 1)

        item = etree.SubElement(despatch_line, etree.QName(NSMAP["cac"], "Item"))
        etree.SubElement(item, etree.QName(NSMAP["cbc"], "Description")).text = item_data['descripcion']
        if item_data.get('codigo'):
            sellers_item_id = etree.SubElement(item, etree.QName(NSMAP["cac"], "SellersItemIdentification"))
            etree.SubElement(sellers_item_id, etree.QName(NSMAP["cbc"], "ID")).text = item_data['codigo']

    xml_bytes = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='utf-8')
    return xml_bytes


def firmar_xml(xml_string_sin_firmar, nombre_base_archivo):
    try:
        certificado_path = current_app.config['CERTIFICADO_PFX_PATH']
        certificado_pass = current_app.config['CERTIFICADO_PASS']

        with open(certificado_path, "rb") as f:
            pfx_data = f.read()

        # 1. Parseamos el XML original
        root = etree.fromstring(xml_string_sin_firmar)

        # Preparamos las librerías de criptografía
        from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, NoEncryption, PrivateFormat
        from cryptography.hazmat.backends import default_backend

        password_bytes = certificado_pass.encode('utf-8') if certificado_pass else None
        private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
            pfx_data, password_bytes, backend=default_backend()
        )

        private_key_bytes = private_key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
        certificate_bytes = certificate.public_bytes(Encoding.PEM)

        signer = XMLSigner(
            method=methods.enveloped,
            digest_algorithm='sha256',
            signature_algorithm='rsa-sha256',
            c14n_algorithm='http://www.w3.org/2001/10/xml-exc-c14n#'
        )

        # 2. Firmamos
        signed_root = signer.sign(
            root,
            key=private_key_bytes,
            cert=certificate_bytes
        )

        # 3. Mover la firma a su lugar correcto DENTRO del árbol firmado
        xpath_nsmap = {k: v for k, v in NSMAP.items() if k is not None}

        # A. Encontramos la firma
        signature_node = signed_root.xpath("//ds:Signature", namespaces=xpath_nsmap)[0]

        # B. Encontramos la carpeta 'ExtensionContent'
        extension_content_node = \
            signed_root.xpath("//ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent", namespaces=xpath_nsmap)[0]

        # C. Configuramos el ID y movemos la firma adentro
        signature_node.set("Id", "Sign")
        extension_content_node.append(signature_node)

        return etree.tostring(signed_root, pretty_print=True, xml_declaration=True, encoding='utf-8')

    except Exception as e:
        print(f"ERROR al firmar el XML: {e}")
        traceback.print_exc()
        return None


def comprimir_y_codificar_base64(xml_firmado_bytes, nombre_archivo_zip):
    try:
        nombre_archivo_xml = nombre_archivo_zip.replace('.zip', '.xml')
        in_memory_zip = io.BytesIO()
        with zipfile.ZipFile(in_memory_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(nombre_archivo_xml, xml_firmado_bytes)
        in_memory_zip.seek(0)
        contenido_zip_bytes = in_memory_zip.read()

        # Hash del ZIP (para el envío API)
        hash_zip = hashlib.sha256(contenido_zip_bytes).hexdigest()

        contenido_zip_base64 = base64.b64encode(contenido_zip_bytes).decode('utf-8')
        return contenido_zip_base64, nombre_archivo_xml, hash_zip
    except:
        return None, None, None


def enviar_guia_sunat_oauth2(nombre_zip, zip_base64, access_token, hash_zip):
    try:
        base_envio_url = 'https://api-cpe.sunat.gob.pe/v1/contribuyente/gem/comprobantes/'
        parametros_url = nombre_zip.replace('.zip', '')
        envio_url = f"{base_envio_url}{parametros_url}"
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        payload = {'archivo': {'nomArchivo': nombre_zip, 'arcGreZip': zip_base64, 'hashZip': hash_zip}}

        response = requests.post(envio_url, json=payload, headers=headers)
        if response.status_code == 200: return response.json()
        print(f"Error Envío SUNAT: {response.status_code} - {response.text}")
        return None
    except:
        return None


def consultar_ticket_sunat(ticket_id, access_token):
    try:
        base_url = "https://api-cpe.sunat.gob.pe/v1/contribuyente/gem/comprobantes/envios/"
        response = requests.get(f"{base_url}{ticket_id}",
                                headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'})
        if response.status_code == 200: return response.json()
        return None
    except:
        return None


# ==============================================================================
# C. GENERACIÓN DE PDF Y QR (LÓGICA CORREGIDA)
# ==============================================================================

def generar_qr_base64(data: dict, qr_data: str | None):
    """
    Genera el QR.
    - Prioridad 1: Si qr_data es una URL (http...), usa eso (viene del CDR).
    - Prioridad 2: Si qr_data es un Hash, construye la URL manualmente.
    - Fallback: Si no hay nada, usa datos concatenados con pipes (|).
    """
    qr_text = ""

    # Validar si hay datos externos (URL o Hash)
    if qr_data and qr_data != "HASH-NO-DISPONIBLE":
        qr_data_clean = qr_data.strip()

        if qr_data_clean.startswith("http"):
            # CASO 1: URL OFICIAL DEL CDR (Lo ideal)
            print(f"--- (QR) Usando URL oficial del CDR: {qr_data_clean[:50]}... ---")
            qr_text = qr_data_clean
        else:
            # CASO 2: Solo tenemos el HASH (DigestValue)
            # Construimos la URL manualmente
            hash_encoded = urllib.parse.quote(qr_data_clean)
            print(f"--- (QR) Usando DigestValue para URL: {qr_data_clean} ---")
            qr_text = f"https://e-factura.sunat.gob.pe/v1/contribuyente/gre/comprobantes/descargaqr?hashqr={hash_encoded}"

    else:
        # CASO 3: Fallback (Pipes) - Por si falla la conexión con SUNAT pero quieres el PDF
        print("--- ADVERTENCIA (QR): Sin Hash/URL. Usando fallback plano. ---")
        try:
            # Usamos .get para evitar errores si faltan claves
            qr_text = "|".join([
                current_app.config.get('TU_RUC', ''),
                "09",
                data['serie_numero'].split('-')[0],
                data['serie_numero'].split('-')[1],
                data.get('fecha_emision', datetime.now().strftime('%Y-%m-%d')),
                data['destinatario']['tipo_doc'],
                data['destinatario']['ruc']
            ])
        except Exception as e:
            qr_text = "ERROR-QR-DATA-MISSING"

    # Generación de la imagen
    qr = qrcode.QRCode(version=1, box_size=4, border=1)
    qr.add_data(qr_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return img_base64


def generar_pdf_guia(datos_guia, hash_xml_firmado):
    """
    Genera el PDF en memoria.
    Recibe 'hash_xml_firmado' que puede ser el HASH (DigestValue) o una URL.
    """
    try:
        # 2. LOGO EN BASE64
        ruta_backend = os.path.dirname(current_app.root_path)
        ruta_logo = os.path.join(ruta_backend, 'instance', 'logo_v2.png')
        logo_data = ""
        if os.path.exists(ruta_logo):
            with open(ruta_logo, "rb") as f:
                logo_data = f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

        # 3. CONTEXTO PARA JINJA2
        context_data = {
            'logo_path': logo_data,
            'serie_numero': f"{datos_guia['serie']}-{str(datos_guia['numero']).zfill(7) if isinstance(datos_guia['numero'], int) else datos_guia['numero']}",
            'fecha_traslado': datos_guia['fecha_de_inicio_de_traslado'].strftime('%d/%m/%Y'),

            'partida': {'direccion': datos_guia['punto_de_partida_direccion']},
            'llegada': {'direccion': datos_guia['punto_de_llegada_direccion']},

            'destinatario': {
                'razon_social': datos_guia['cliente_denominacion'],
                'ruc': datos_guia['cliente_numero_de_documento'],
                'tipo_doc': datos_guia['cliente_tipo_de_documento']
            },
            'remitente': {'ruc': current_app.config['TU_RUC']},

            'conductor': {
                'placa': datos_guia.get('transportista_placa_numero', ''),
                'marca': datos_guia.get('marca', ''),
                'licencia': datos_guia.get('licencia', ''),
                'nombre': f"{datos_guia.get('conductor_nombre', '')} {datos_guia.get('conductor_apellidos', '')}"
            },

            'motivo_traslado': datos_guia['motivo_de_traslado'],
            'motivo': datos_guia.get('motivo', ''),
            'items': datos_guia['items'],
            'observaciones': datos_guia.get('observaciones', '-'),
            'fecha_emision': datos_guia['fecha_de_emision'].strftime('%Y-%m-%d')
        }

        # 4. GENERAR QR USANDO LA NUEVA FUNCIÓN
        qr_base64 = generar_qr_base64(context_data, hash_xml_firmado)
        context_data['qr_base64'] = qr_base64
        context_data['hash_qr'] = hash_xml_firmado

        # 5. RENDERIZAR
        html_string = render_template('guia_remision.html', data=context_data)

        # 6. RETORNAR BYTES
        return HTML(string=html_string, base_url=current_app.root_path).write_pdf()

    except Exception as e:
        print(f"Error generando PDF: {e}")
        traceback.print_exc()
        return None