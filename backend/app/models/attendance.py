from app.extensions import db
from datetime import datetime

class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    document_number = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    raw_data = db.Column(db.String(255), nullable=True)
    external_name = db.Column(db.String(150), nullable=True) # <-- Nuevo campo

    employee = db.relationship('Employee', backref='attendance_records')

    def to_dict(self):
        name = "Desconocido"
        if self.employee:
            name = f"{self.employee.first_name} {self.employee.last_name}"
        elif self.external_name:
            name = self.external_name

        return {
            'id': self.id,
            'employee_name': name,
            'document_number': self.document_number,
            'timestamp': self.timestamp.isoformat(),
            'raw_data': self.raw_data
        }
