from ..extensions import db
from .provider import Provider
from .employee import Employee
from .purchase_order import DocumentType

class AccountType(db.Model):
    __tablename__ = 'account_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    def to_dict(self):
        return {'id': self.id, 'name': self.name}

class Bank(db.Model):
    __tablename__ = 'banks'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    def to_dict(self):
        return {'id': self.id, 'name': self.name}

class BankAccount(db.Model):
    __tablename__ = 'bank_accounts'
    id = db.Column(db.Integer, primary_key=True)
    bank_id = db.Column(db.Integer, db.ForeignKey('banks.id'), nullable=False)
    account_type_id = db.Column(db.Integer, db.ForeignKey('account_types.id'), nullable=False)
    alias = db.Column(db.String(100), nullable=True)
    account_number = db.Column(db.String(50), unique=True, nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='PEN') # 'PEN' or 'USD'

    bank = db.relationship('Bank', backref='accounts')
    account_type = db.relationship('AccountType', backref='accounts')

    def to_dict(self):
        return {
            'id': self.id,
            'bank_id': self.bank_id,
            'bank_name': self.bank.name if self.bank else None,
            'account_type_id': self.account_type_id,
            'account_type_name': self.account_type.name if self.account_type else None,
            'alias': self.alias,
            'account_number': self.account_number,
            'currency': self.currency
        }

class ExpenseType(db.Model):
    __tablename__ = 'expense_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    acronym = db.Column(db.String(10), nullable=True) # Sigla

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'acronym': self.acronym
        }

class IncomeType(db.Model):
    __tablename__ = 'income_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    acronym = db.Column(db.String(10), nullable=True) # Sigla

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'acronym': self.acronym
        }

class TreasuryTransaction(db.Model):
    __tablename__ = 'treasury_transactions'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    type = db.Column(db.String(20), nullable=False) # 'INGRESO' or 'EGRESO'
    correlative = db.Column(db.String(20), nullable=True) # Generated correlative (e.g., ING-000001)
    
    account_id = db.Column(db.Integer, db.ForeignKey('bank_accounts.id'), nullable=False)
    expense_type_id = db.Column(db.Integer, db.ForeignKey('expense_types.id'), nullable=True)
    income_type_id = db.Column(db.Integer, db.ForeignKey('income_types.id'), nullable=True)
    
    # Beneficiary Fields
    beneficiary_type = db.Column(db.String(20), nullable=True) # 'PROVIDER', 'EMPLOYEE', 'ACCOUNT', 'OTHER'
    beneficiary_provider_id = db.Column(db.Integer, db.ForeignKey('providers.id'), nullable=True)
    beneficiary_employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    beneficiary_account_id = db.Column(db.Integer, db.ForeignKey('bank_accounts.id'), nullable=True)
    
    user_id = db.Column(db.Integer, nullable=True) # ID of user who created it (optional for now)
    
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    account = db.relationship('BankAccount', backref='transactions', foreign_keys=[account_id])
    expense_type = db.relationship('ExpenseType', backref='transactions')
    income_type = db.relationship('IncomeType', backref='transactions')
    
    # Beneficiary Relationships
    beneficiary_provider = db.relationship('Provider', backref='treasury_transactions')
    beneficiary_employee = db.relationship('Employee', backref='treasury_transactions')
    beneficiary_account = db.relationship('BankAccount', foreign_keys=[beneficiary_account_id], backref='beneficiary_transactions')
    
    # Document Relationship
    document = db.relationship('TreasuryTransactionDocument', uselist=False, backref='transaction', cascade='all, delete-orphan')

    def to_dict(self):
        beneficiary_name = None
        if self.beneficiary_type == 'PROVIDER' and self.beneficiary_provider:
            beneficiary_name = self.beneficiary_provider.name
        elif self.beneficiary_type == 'EMPLOYEE' and self.beneficiary_employee:
            beneficiary_name = f"{self.beneficiary_employee.first_name} {self.beneficiary_employee.last_name}"
        elif self.beneficiary_type == 'ACCOUNT' and self.beneficiary_account:
            beneficiary_name = self.beneficiary_account.alias or self.beneficiary_account.account_number
            
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'description': self.description,
            'amount': float(self.amount),
            'type': self.type,
            'correlative': self.correlative,
            'account_id': self.account_id,
            'account_alias': self.account.alias if self.account else None,
            'account_currency': self.account.currency if self.account else 'PEN',
            'expense_type_id': self.expense_type_id,
            'expense_type_name': self.expense_type.name if self.expense_type else None,
            'income_type_id': self.income_type_id,
            'income_type_name': self.income_type.name if self.income_type else None,
            'beneficiary_type': self.beneficiary_type,
            'beneficiary_name': beneficiary_name,
            'document': self.document.to_dict() if self.document else None,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class TreasuryTransactionDocument(db.Model):
    __tablename__ = 'treasury_transaction_documents'
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('treasury_transactions.id'), nullable=False)
    document_type_id = db.Column(db.Integer, db.ForeignKey('document_types.id'), nullable=False)
    series = db.Column(db.String(20), nullable=False)
    number = db.Column(db.String(20), nullable=False)
    issuer_ruc = db.Column(db.String(11), nullable=True)
    issuer_name = db.Column(db.String(255), nullable=True)
    issue_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    document_type = db.relationship('DocumentType')

    def to_dict(self):
        return {
            'id': self.id,
            'document_type_id': self.document_type_id,
            'document_type_name': self.document_type.name if self.document_type else None,
            'series': self.series,
            'number': self.number,
            'issuer_ruc': self.issuer_ruc,
            'issuer_name': self.issuer_name,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'amount': float(self.amount)
        }

class TreasuryAllocationRender(db.Model):
    __tablename__ = 'treasury_allocation_renders'
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('treasury_transactions.id'), nullable=False)
    correlative = db.Column(db.String(20), nullable=True) # e.g., R-00001
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relationship to the main transaction (Allocation)
    transaction = db.relationship('TreasuryTransaction', backref=db.backref('renders', cascade='all, delete-orphan'))
    
    # Relationship to the document (optional)
    document = db.relationship('TreasuryRenderDocument', uselist=False, backref='render', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'correlative': self.correlative,
            'amount': float(self.amount),
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'document': self.document.to_dict() if self.document else None
        }

class TreasuryRenderDocument(db.Model):
    __tablename__ = 'treasury_render_documents'
    id = db.Column(db.Integer, primary_key=True)
    render_id = db.Column(db.Integer, db.ForeignKey('treasury_allocation_renders.id'), nullable=False)
    document_type_id = db.Column(db.Integer, db.ForeignKey('document_types.id'), nullable=False)
    series = db.Column(db.String(20), nullable=False)
    number = db.Column(db.String(20), nullable=False)
    issuer_ruc = db.Column(db.String(11), nullable=True)
    issuer_name = db.Column(db.String(255), nullable=True)
    issue_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    document_type = db.relationship('DocumentType')

    def to_dict(self):
        return {
            'id': self.id,
            'document_type_id': self.document_type_id,
            'document_type_name': self.document_type.name if self.document_type else None,
            'series': self.series,
            'number': self.number,
            'issuer_ruc': self.issuer_ruc,
            'issuer_name': self.issuer_name,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'amount': float(self.amount)
        }
