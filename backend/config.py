import os

# Obtiene la ruta absoluta de la carpeta 'backend'
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SUNAT_API_KEY = 'sk_11278.I8mPTaArw5Na8wXOR7aUV9XdZviJZWyi'
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-clave-secreta-muy-dificil'

    # Configuración de la base de datos SQLite
    # Se guardará en backend/instance/app.db
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'instance', 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # --- ¡AÑADE TODAS ESTAS LÍNEAS! ---
    SUNAT_CLIENT_ID = os.environ.get('SUNAT_CLIENT_ID') or "752147d4-0e07-4a13-80f8-dd9988c700e0"
    SUNAT_CLIENT_SECRET = os.environ.get('SUNAT_CLIENT_SECRET') or "y1Z4Cqr0S/LnZXy3UB8AjQ=="
    TU_RUC = os.environ.get('TU_RUC') or "20522348831"
    TU_RAZON_SOCIAL = os.environ.get('TU_RAZON_SOCIAL') or "COMPOWER INGENIERIA ESPECIALIZADA S.A.C."
    SUNAT_SOL_USER = os.environ.get('SUNAT_SOL_USER') or "CPUSER01"
    SUNAT_SOL_PASS = os.environ.get('SUNAT_SOL_PASS') or "Prueba01"

    # ¡IMPORTANTE! Asegúrate de que esta ruta sea correcta para tu servidor de Flask
    # Te recomiendo mover el PFX a la carpeta 'backend/instance/'
    CERTIFICADO_PFX_PATH = os.environ.get('CERTIFICADO_PFX_PATH') or os.path.join(basedir, 'instance',
                                                                                  'certificado.pfx')
    CERTIFICADO_PASS = os.environ.get('CERTIFICADO_PASS') or "SOVOS1234"