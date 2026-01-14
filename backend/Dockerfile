# 1. Usamos tu versión exacta: Python 3.13
FROM python:3.13-slim

# 2. Carpeta de trabajo
WORKDIR /app

# 3. Instalación de dependencias del sistema
# Nota el cambio: libgdk-pixbuf-2.0-0 (con guion)
RUN apt-get update && apt-get install -y \
    build-essential \
    libkrb5-dev \
    libssl-dev \
    libffi-dev \
    python3-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# 4. Actualizar pip
RUN pip install --upgrade pip

# 5. Copiar requerimientos
COPY requirements.txt .

# 6. Instalar todo (gunicorn forzado)
RUN pip install --no-cache-dir -r requirements.txt && pip install gunicorn

# 7. Copiar código y exponer puerto
COPY . .
EXPOSE 5000

# 8. Arranque
CMD ["python", "-m", "gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]