FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN apt-get update && apt-get install -y \
    gcc \
    libkrb5-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . .

EXPOSE 5000

# Asegúrate de que "app:app" coincida con tu archivo principal
# Si tu archivo se llama "main.py", pon "main:app"
CMD ["python", "-m", "gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]