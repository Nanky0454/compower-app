from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

class TransactionBase(BaseModel):
    date: date
    description: str
    amount: float
    type: str # 'INGRESO' or 'EGRESO'
    account_id: int
    expense_type_id: Optional[int] = None
    income_type_id: Optional[int] = None
    beneficiary_type: Optional[str] = None # 'PROVIDER', 'EMPLOYEE', 'ACCOUNT', 'OTHER'
    beneficiary_provider_id: Optional[int] = None
    beneficiary_employee_id: Optional[int] = None
    beneficiary_account_id: Optional[int] = None

class DocumentCreate(BaseModel):
    document_type_id: int
    series: str
    number: str
    issuer_ruc: Optional[str] = None
    issuer_name: Optional[str] = None
    issue_date: Optional[date] = None
    amount: Optional[float] = None

class TransactionCreate(TransactionBase):
    document: Optional[DocumentCreate] = None

class TransactionUpdate(BaseModel):
    date: Optional[date] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    type: Optional[str] = None
    account_id: Optional[int] = None
    expense_type_id: Optional[int] = None
    income_type_id: Optional[int] = None
    beneficiary_type: Optional[str] = None
    beneficiary_provider_id: Optional[int] = None
    beneficiary_employee_id: Optional[int] = None
    beneficiary_account_id: Optional[int] = None

class DocumentResponse(BaseModel):
    id: int
    document_type_id: int
    document_type_name: Optional[str] = None
    series: str
    number: str
    issuer_ruc: Optional[str] = None
    issuer_name: Optional[str] = None
    issue_date: Optional[date] = None
    amount: float

class TransactionResponse(TransactionBase):
    id: int
    correlative: Optional[str] = None
    account_alias: Optional[str] = None
    account_currency: Optional[str] = None
    expense_type_name: Optional[str] = None
    income_type_name: Optional[str] = None
    beneficiary_name: Optional[str] = None
    document: Optional[DocumentResponse] = None
    user_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
