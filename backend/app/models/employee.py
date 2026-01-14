from app.extensions import db

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    document_type = db.Column(db.String(20), nullable=False)
    document_number = db.Column(db.String(20), nullable=False, unique=True)
    position = db.Column(db.String(100))
    salary = db.Column(db.Float)
    start_date = db.Column(db.Date)
    birth_date = db.Column(db.Date)
    phone = db.Column(db.String(20)) # <-- Nuevo campo
    email = db.Column(db.String(100)) # <-- Nuevo campo

    licenses = db.relationship('EmployeeLicense', backref='employee', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'document_type': self.document_type,
            'document_number': self.document_number,
            'position': self.position,
            'salary': self.salary,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'birth_date': self.birth_date.isoformat() if self.birth_date else None,
            'phone': self.phone,
            'email': self.email,
            'licenses': [l.to_dict() for l in self.licenses]
        }

class EmployeeLicense(db.Model):
    __tablename__ = 'employee_licenses'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    license_number = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(20), nullable=False) # A-I, A-IIb, etc.
    expiration_date = db.Column(db.Date)

    def to_dict(self):
        return {
            'id': self.id,
            'license_number': self.license_number,
            'category': self.category,
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None
        }
