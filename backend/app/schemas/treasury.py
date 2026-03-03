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
    status: str # NEW
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

class RenderDocumentCreate(BaseModel):
    document_type_id: int
    series: str
    number: str
    issuer_ruc: Optional[str] = None
    issuer_name: Optional[str] = None
    issue_date: Optional[date] = None
    amount: Optional[float] = None

class RenderDocumentResponse(BaseModel):
    id: int
    document_type_id: int
    document_type_name: Optional[str] = None
    series: str
    number: str
    issuer_ruc: Optional[str] = None
    issuer_name: Optional[str] = None
    issue_date: Optional[date] = None
    amount: float

class TreasuryRenderDetailCreate(BaseModel):
    date: date
    provider_id: Optional[int] = None
    invoice_series: Optional[str] = None
    invoice_number: Optional[str] = None
    description: str
    amount: float

class TreasuryRenderDetailUpdate(TreasuryRenderDetailCreate):
    id: Optional[int] = None # Make ID optional for updates (new details might be included)

class TreasuryRenderDetailResponse(BaseModel):
    id: int
    render_id: int
    date: date
    provider_id: Optional[int] = None
    provider_name: Optional[str] = None
    invoice_series: Optional[str] = None
    provider_ruc: Optional[str] = None
    invoice_number: Optional[str] = None
    description: str
    amount: float

    class Config:
        from_attributes = True

class RenderCreate(BaseModel):
    correlative: Optional[str] = None
    amount: float
    description: str
    cost_center_id: Optional[int] = None
    document: Optional[RenderDocumentCreate] = None
    details: Optional[list[TreasuryRenderDetailCreate]] = None

class RenderUpdate(BaseModel):
    correlative: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    cost_center_id: Optional[int] = None
    document: Optional[RenderDocumentCreate] = None
    details: Optional[list[TreasuryRenderDetailUpdate]] = None

class RenderResponse(BaseModel):
    id: int
    transaction_id: int
    correlative: Optional[str] = None
    amount: float
    description: str
    cost_center_id: Optional[int] = None
    cost_center_name: Optional[str] = None
    cost_center_code: Optional[str] = None
    created_at: Optional[datetime] = None
    document: Optional[RenderDocumentResponse] = None
    details: Optional[list[TreasuryRenderDetailResponse]] = None

    class Config:
        from_attributes = True
