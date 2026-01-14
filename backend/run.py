import os
from flask import send_from_directory
from app import create_app

app = create_app()

# --- BLOQUE NUEVO PARA PRODUCCIÓN ---
# Mapeamos la carpeta donde Docker pondrá los archivos compilados
FRONTEND_FOLDER = os.path.join(os.getcwd(), 'frontend_build')

@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_FOLDER, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    file_path = os.path.join(FRONTEND_FOLDER, path)
    if os.path.exists(file_path):
        return send_from_directory(FRONTEND_FOLDER, path)
    return send_from_directory(FRONTEND_FOLDER, 'index.html')
# ------------------------------------

if __name__ == '__main__':
    app.run(debug=True, port=5000)