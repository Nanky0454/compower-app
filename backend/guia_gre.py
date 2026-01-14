@app.post("/enviar-guia")
async def enviar_guia(datos_guia: dict):
    # ... (Pasos 1-5: Obtener Token, Convertir Fechas, Crear XML, Firmar, Comprimir) ...
    # (Copio los pasos 1-5 de tu código, ya que funcionan)

    # --- Paso 1: Obtener el Token primero ---
    print("\n--- Paso 1: Obteniendo Token de SUNAT... ---")
    access_token = sunat.obtener_token_oauth2()

    if not access_token:
        print("--- ERROR FATAL: No se pudo obtener el token. Abortando. ---")
        raise HTTPException(status_code=401, detail="Error al obtener el token de SUNAT. Verifique credenciales.")

    print("--- Paso 1: Token obtenido exitosamente. ---")

    try:
        # --- Paso 2: Convertir Fechas ---
        datos_guia['fecha_de_emision'] = datetime.strptime(
            datos_guia['fecha_de_emision'], '%Y-%m-%d'
        ).date()
        datos_guia['fecha_de_inicio_de_traslado'] = datetime.strptime(
            datos_guia['fecha_de_inicio_de_traslado'], '%Y-%m-%d'
        ).date()

        # --- Paso 3: Crear el XML ---
        print("--- Paso 2: Creando XML de la Guía... ---")
        xml_sin_firmar_bytes = sunat.crear_xml_guia_remision(datos_guia)
        if not xml_sin_firmar_bytes:
            raise HTTPException(status_code=500, detail="Error al crear el XML")

        # --- Paso 4: Firmar el XML ---
        print("--- Paso 3: Firmando el XML... ---")
        nombre_base_archivo = f"{datos_guia['serie']}-{datos_guia['numero']}"

        xml_firmado_bytes = sunat.firmar_xml(
            xml_sin_firmar_bytes,
            nombre_base_archivo
        )

        if not xml_firmado_bytes:
            raise HTTPException(status_code=500, detail="Error al firmar el XML.")

        # --- Paso 5: Comprimir, Hashear y Codificar ---
        print("--- Paso 4: Comprimiendo y Hasheando XML... ---")
        ruc_emisor = settings.TU_RUC
        tipo_doc = "09"  # Guía de Remisión
        nombre_zip = f"{ruc_emisor}-{tipo_doc}-{nombre_base_archivo}.zip"

        zip_base64, _, hash_zip = sunat.comprimir_y_codificar_base64(xml_firmado_bytes, nombre_zip)

        if not zip_base64 or not hash_zip:
            raise HTTPException(status_code=500, detail="Error al comprimir o hashear el XML")

        # --- Paso 6: Enviar a SUNAT ---
        print("--- Paso 5: Enviando XML a SUNAT... ---")
        respuesta_envio_json = sunat.enviar_guia_sunat_oauth2(
            nombre_zip,
            zip_base64,
            access_token,
            hash_zip
        )

        if not respuesta_envio_json:
            raise HTTPException(status_code=500, detail="Error en la respuesta de SUNAT (Envío)")

        # --- Paso 7: Consultar el Ticket ---
        ticket_id = respuesta_envio_json.get('numTicket')
        if not ticket_id:
            print("--- ERROR: SUNAT devolvió 200 pero no hay numTicket. ---")
            raise HTTPException(status_code=500, detail="Respuesta exitosa de SUNAT pero sin numTicket.")

        print(f"--- Paso 6: Ticket {ticket_id} recibido. Esperando 3 segundos para consulta... ---")
        time.sleep(3)

        print(f"--- Paso 7: Consultando estado del ticket... ---")
        resultado_consulta = sunat.consultar_ticket_sunat(ticket_id, access_token)

        if not resultado_consulta:
            raise HTTPException(status_code=500, detail=f"Error al consultar el ticket {ticket_id}.")

        # --- ¡INICIO DE LA LÓGICA DE PDF MODIFICADA! ---
        if resultado_consulta and resultado_consulta.get("codRespuesta") == "0":
            print("--- ¡ÉXITO! Guía aceptada por SUNAT (codRespuesta=0). ---")

            # 1. Obtener el 'arcCdr' (ZIP en Base64) de la respuesta
            cdr_base64 = resultado_consulta.get("arcCdr")

            if not cdr_base64:
                print("--- ERROR: Guía aceptada (codRespuesta=0) pero no se encontró 'arcCdr' en la respuesta. ---")
                raise HTTPException(status_code=500, detail="Guía aceptada pero no se pudo obtener el CDR de SUNAT.")

            # 2. Procesar el CDR para extraer la URL del QR
            print("--- (PDF) Procesando CDR para extraer URL del QR... ---")
            cdr_data = procesar_cdr(cdr_base64)
            qr_url_from_cdr = cdr_data.get("qr_url")  # <--- ¡Aquí está tu URL!

            if qr_url_from_cdr:

                # --- Guardar la URL del QR en un archivo (opcional, pero útil) ---
                try:
                    qr_url_filename = f"{nombre_base_archivo}.qrurl"
                    with open(qr_url_filename, "w") as f:
                        f.write(qr_url_from_cdr)
                    print(f"--- URL del QR guardada en: {qr_url_filename} ---")
                except Exception as e:
                    print(f"--- ADVERTENCIA: No se pudo guardar la URL del QR: {e} ---")

                # --- INICIO: CÓDIGO PARA GENERAR Y GUARDAR PDF ---
                try:
                    print("--- (PDF) Iniciando generación de PDF para guardado... ---")

                    # 1. Parsear el XML firmado que ya tenemos en memoria
                    print("--- (PDF) Parseando XML firmado... ---")
                    data_para_template = parsear_guia_xml(xml_firmado_bytes)

                    # 2. Generar el QR Base64 (pasándole la URL completa)
                    print("--- (PDF) Generando QR Base64... ---")
                    data_para_template['qr_base64'] = generar_qr_base64(data_para_template, qr_url_from_cdr)

                    try:
                        base_dir = os.getcwd()
                        logo_file_path = os.path.join(base_dir, "img", "logo.svg")
                        # Convertimos la ruta del disco a un formato URI (ej: file:///C:/Users/...)
                        data_para_template['logo_path'] = pathlib.Path(logo_file_path).as_uri()
                        print(f"--- (PDF) Usando logo desde: {data_para_template['logo_path']} ---")
                    except Exception as e:
                        print(f"--- ADVERTENCIA (PDF): No se pudo encontrar el logo: {e} ---")
                        data_para_template['logo_path'] = ""  # Dejarlo vacío si no se encuentra

                    # --- ¡INICIO DEL CAMBIO! INYECTAR MARCA DESDE EL JSON ORIGINAL ---
                    try:
                            # Comprobamos si el dict 'conductor' existe (para evitar errores)
                        if 'conductor' in data_para_template:
                            # ¡IMPORTANTE! Asegúrate que la clave 'marca_vehiculo'
                            # sea la misma que usas en tu JSON original (datos_guia)
                            marca_json = datos_guia.get('marca')  # O 'marca', 'transportista_marca', etc.
                            if marca_json:
                                data_para_template['conductor']['marca'] = marca_json
                                print(f"--- (PDF) Inyectando marca desde JSON: {marca_json} ---")
                            else:
                                # Si no vino en el JSON, la dejamos vacía
                                data_para_template['conductor']['marca'] = ""
                    except Exception as e:
                        print(f"--- ADVERTENCIA (PDF): No se pudo inyectar la marca: {e} ---")
                        if 'conductor' in data_para_template:
                            data_para_template['conductor']['marca'] = ""  # Asegurar que exista
                    # --- ¡FIN DEL CAMBIO! ---

                    placa = datos_guia.get('transportista_placa_numero')
                    data_para_template['conductor']['placa'] = placa

                    # --- INICIO: FORMATEAR SERIE Y NÚMERO ---
                    try:
                        # 1. Obtener la serie y el número del JSON original
                        serie = datos_guia.get('serie')  # Ej: 'T002'
                        numero = datos_guia.get('numero')  # Ej: 9 o '9'

                        if serie and numero is not None:
                            # 2. Convertir el número a string y rellenar con ceros a 7 dígitos
                            numero_formateado = str(numero).zfill(7)  # '9' -> '0000009'

                            # 3. Sobrescribir la clave 'serie_numero' que usará la plantilla
                            data_para_template['serie_numero'] = f"{serie}-{numero_formateado}"

                            print(f"--- (PDF) Formateando serie_numero a: {data_para_template['serie_numero']} ---")
                    except Exception as e:
                        print(f"--- ADVERTENCIA (PDF): No se pudo re-formatear serie_numero: {e} ---")
                        # Si falla, la plantilla usará el valor leído del XML (ej: 'T002-9')
                    # --- FIN: FORMATEAR SERIE Y NÚMERO ---


                    # 3. Renderizar el HTML desde la plantilla
                    print("--- (PDF) Renderizando plantilla HTML... ---")
                    template = env.get_template("guia_remision.html")
                    html_string = template.render(data=data_para_template)

                    # 4. Generar el PDF en memoria
                    print("--- (PDF) Creando PDF con WeasyPrint... ---")
                    pdf_bytes = HTML(string=html_string).write_pdf()

                    # 5. Guardar el PDF en la carpeta "GRE"
                    output_folder = "GRE"
                    os.makedirs(output_folder, exist_ok=True)

                    pdf_filename = f"{nombre_base_archivo}.pdf"
                    pdf_path = os.path.join(output_folder, pdf_filename)

                    with open(pdf_path, "wb") as f:
                        f.write(pdf_bytes)

                    print(f"--- ¡PDF guardado exitosamente en: {pdf_path}! ---")

                except Exception as e:
                    print(f"--- ERROR (PDF): No se pudo generar el PDF: {e} ---")
                    traceback.print_exc()
                # --- FIN: CÓDIGO PARA GENERAR Y GUARDAR PDF ---

            else:
                print(
                    "--- ADVERTENCIA: Guía aceptada pero no se encontró 'DocumentDescription' (URL del QR) en el CDR. No se pudo generar PDF. ---")

        else:
            # --- Manejar rechazo de SUNAT ---
            print(f"--- ERROR: Guía RECHAZADA por SUNAT. Código: {resultado_consulta.get('codRespuesta')} ---")
            print(f"--- Mensaje: {resultado_consulta.get('desRespuesta')} ---")
            # Devolvemos el error al cliente
            raise HTTPException(
                status_code=400,  # Bad Request, porque el documento fue rechazado
                detail=f"Guía Rechazada: {resultado_consulta.get('desRespuesta')}"
            )
        # --- FIN DE LA LÓGICA DE PDF ---

        print("--- ¡Proceso completado (Envío + Consulta)! ---")
        # Devolvemos la respuesta final de SUNAT al cliente
        return resultado_consulta

    except Exception as e:
        print(f"Error general en /enviar-guia: {e}")
        traceback.print_exc()
        # Si ya es un HTTPException (como nuestro rechazo), lo relanzamos
        if isinstance(e, HTTPException):
            raise e
        # Si es un error genérico, lo envolvemos
        raise HTTPException(status_code=500, detail=str(e))