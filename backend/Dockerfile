# 1. CAMBIO IMPORTANTE: Usamos Python 3.11 en lugar de 3.9
FROM python:3.13-slim

# 2. Carpeta de trabajo
WORKDIR /app

# 3. Instalamos dependencias del sistema (WeasyPrint, GSSAPI, Criptografía)
RUN apt-get update && apt-get install -y \
    build-essential \
    libkrb5-dev \
    libssl-dev \
    libffi-dev \
    python3-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# 4. Actualizar pip
RUN pip install --upgrade pip

# 5. Copiar requerimientos
COPY requirements.txt .

# 6. Instalar todo (Ahora sí funcionará Alembic porque tenemos Python 3.11)
RUN pip install --no-cache-dir -r requirements.txt && pip install gunicorn

# 7. Copiar código y exponer puerto
COPY . .
EXPOSE 5000

# 8. Arranque
CMD ["python", "-m", "gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]