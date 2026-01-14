FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install gunicorn

COPY . .

EXPOSE 5000

# Asegúrate de que "app:app" coincida con tu archivo principal
# Si tu archivo se llama "main.py", pon "main:app"
CMD ["python", "-m", "gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]