# models.py
from datetime import datetime
from ..extensions import db

class ExchangeRate(db.Model):
    __tablename__ = 'exchange_rates'

    id = db.Column(db.Integer, primary_key=True)
    currency = db.Column(db.String(3), nullable=False) # 'USD', 'EUR'
    buy_rate = db.Column(db.Numeric(10, 4), nullable=False)  # Antes: compra
    sell_rate = db.Column(db.Numeric(10, 4), nullable=False) # Antes: venta
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow) # Antes: fecha
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ExchangeRate {self.currency} - {self.date}: {self.sell_rate}>'