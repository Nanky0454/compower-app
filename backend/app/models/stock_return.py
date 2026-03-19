from ..extensions import db
from datetime import datetime

class StockReturn(db.Model):
    __tablename__ = 'stock_returns'

    id = db.Column(db.Integer, primary_key=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey('stock_transfers.id'), nullable=False)
    return_date = db.Column(db.DateTime, default=datetime.now)
    user_id = db.Column(db.String(255), nullable=False)

    transfer = db.relationship('StockTransfer', backref='returns')
    items = db.relationship('StockReturnItem', backref='stock_return', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'transfer_id': self.transfer_id,
            'return_date': self.return_date.isoformat(),
            'user_id': self.user_id,
            'items': [item.to_dict() for item in self.items]
        }

class StockReturnItem(db.Model):
    __tablename__ = 'stock_return_items'

    id = db.Column(db.Integer, primary_key=True)
    stock_return_id = db.Column(db.Integer, db.ForeignKey('stock_returns.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False)

    product = db.relationship('Product')

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product.name if self.product else "N/A",
            'product_sku': self.product.sku if self.product else "N/A",
            'quantity': float(self.quantity)
        }
