# 1. Usar imagen base
FROM python:3.9-slim

# 2. Carpeta de trabajo
WORKDIR /app

# 3. --- EL BLOQUE "TANQUE" (INSTALA TODO) ---
# build-essential: Compiladores básicos (gcc, make, etc.)
# libkrb5-dev: Para gssapi
# libssl-dev y libffi-dev: Para criptografía y conexiones seguras
# python3-dev: Cabeceras de Python necesarias para compilar extensiones
RUN apt-get update && apt-get install -y \
    build-essential \
    libkrb5-dev \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. Actualizar pip (A veces pip viejo falla al buscar binarios)
RUN pip install --upgrade pip

# 5. Copiar requerimientos
COPY requirements.txt .

# 6. Instalar y forzar gunicorn
RUN pip install --no-cache-dir -r requirements.txt && pip install gunicorn

# 7. Copiar código
COPY . .

# 8. Exponer puerto
EXPOSE 5000

# 9. Arranque seguro
CMD ["python", "-m", "gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]