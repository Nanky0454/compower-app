from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy import MetaData

# --- ESTA ES LA MAGIA QUE FALTA ---
# Define cómo se deben llamar las restricciones automáticamente para que SQLite no falle
convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
# ----------------------------------

# Al inicializar SQLAlchemy, le pasamos la metadata con la convención
db = SQLAlchemy(metadata=metadata)
cors = CORS()