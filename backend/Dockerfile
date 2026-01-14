# 1. Usar imagen base
FROM python:3.9-slim

# 2. Carpeta de trabajo
WORKDIR /app

# 3. --- EL BLOQUE DE SEGURIDAD (CRÍTICO) ---
# Instalamos gcc y librerías necesarias para que gssapi no falle
RUN apt-get update && apt-get install -y \
    gcc \
    libkrb5-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. Copiar requerimientos e instalarlos
COPY requirements.txt .

# 5. Instalamos los requerimientos Y forzamos gunicorn en la misma línea
RUN pip install --no-cache-dir -r requirements.txt && pip install gunicorn

# 6. Copiar el resto del código
COPY . .

# 7. Exponer puerto
EXPOSE 5000

# 8. Comando de arranque a prueba de fallos
CMD ["python", "-m", "gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]