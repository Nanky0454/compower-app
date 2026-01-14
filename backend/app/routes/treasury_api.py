from flask import Blueprint, request, jsonify
from ..extensions import db
from ..models.treasury import TreasuryTransaction, BankAccount, ExpenseType, IncomeType, Bank, AccountType, TreasuryTransactionDocument, TreasuryAllocationRender, TreasuryRenderDocument
from ..models.purchase_order import DocumentType
from ..models.provider import Provider
from ..models.employee import Employee
import requests
from flask import current_app
from ..schemas.treasury import TransactionCreate, TransactionUpdate, TransactionResponse
from ..services.auth_service import requires_auth
from datetime import datetime

treasury_api = Blueprint('treasury_api', __name__)

import pandas as pd
import io
from flask import send_file

@treasury_api.route('/export', methods=['GET'])
@requires_auth(required_permission='view:treasury')
def export_transactions(payload):
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = TreasuryTransaction.query
    
    if start_date:
        query = query.filter(TreasuryTransaction.date >= start_date)
    
    if end_date:
        query = query.filter(TreasuryTransaction.date <= end_date)
        
    transactions = query.order_by(TreasuryTransaction.date.asc()).all()
    
    if not transactions:
        return jsonify({'error': 'No transactions found for this period'}), 404
        
    # Prepare data for DataFrame
    data = []
    for t in transactions:
        # Determine category name
        category = ""
        if t.type == 'INGRESO' and t.income_type:
            category = t.income_type.name
        elif t.type == 'EGRESO' and t.expense_type:
            category = t.expense_type.name
            
        # Determine beneficiary
        beneficiary = t.to_dict().get('beneficiary_name', '')
        
        # Determine Account Name for grouping
        account_name = "Sin Cuenta"
        if t.account:
            account_name = t.account.alias or f"{t.account.bank.name} {t.account.currency}"

        data.append({
            'Fecha': t.date,
            'Correlativo': t.correlative,
            'Descripción': t.description,
            'Cuenta': account_name,
            'Moneda': t.account.currency if t.account else '',
            'Tipo': t.type,
            'Categoría': category,
            'Beneficiario': beneficiary,
            'Monto': float(t.amount) * (-1 if t.type == 'EGRESO' else 1)
        })
        
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Group by Account and write to separate sheets
        for account_name, group_df in df.groupby('Cuenta'):
            # Sheet name limit is 31 chars
            sheet_name = account_name[:31]
            # Remove invalid characters for sheet name if any (basic check)
            invalid_chars = ['\\', '/', '*', '[', ']', ':', '?']
            for char in invalid_chars:
                sheet_name = sheet_name.replace(char, '')
            
            group_df.drop(columns=['Cuenta']).to_excel(writer, sheet_name=sheet_name, index=False)
            
    output.seek(0)
    
    filename = f"Movimientos_{start_date}_al_{end_date}.xlsx"
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@treasury_api.route('/transactions', methods=['GET'])
@requires_auth(required_permission='view:treasury')
def get_transactions(payload):
    account_id = request.args.get('account_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = TreasuryTransaction.query

    if account_id:
        query = query.filter_by(account_id=account_id)
    
    if start_date:
        query = query.filter(TreasuryTransaction.date >= start_date)
    
    if end_date:
        query = query.filter(TreasuryTransaction.date <= end_date)

    transactions = query.order_by(TreasuryTransaction.date.desc(), TreasuryTransaction.created_at.desc()).all()
    return jsonify([t.to_dict() for t in transactions]), 200

@treasury_api.route('/transactions', methods=['POST'])
@requires_auth(required_permission='manage:treasury')
def create_transaction(payload):
    data = request.get_json()
    try:
        # Validate with Pydantic
        transaction_data = TransactionCreate(**data)
        
        # Generate Correlative
        correlative = None
        acronym = None
        
        if transaction_data.type == 'EGRESO' and transaction_data.expense_type_id:
            et = ExpenseType.query.get(transaction_data.expense_type_id)
            if et and et.acronym:
                acronym = et.acronym
                count = TreasuryTransaction.query.filter_by(expense_type_id=transaction_data.expense_type_id).count()
                correlative = f"{acronym}-{str(count + 1).zfill(6)}"
        
        elif transaction_data.type == 'INGRESO' and transaction_data.income_type_id:
            it = IncomeType.query.get(transaction_data.income_type_id)
            if it and it.acronym:
                acronym = it.acronym
                count = TreasuryTransaction.query.filter_by(income_type_id=transaction_data.income_type_id).count()
                correlative = f"{acronym}-{str(count + 1).zfill(6)}"

        new_transaction = TreasuryTransaction(
            date=transaction_data.date,
            description=transaction_data.description,
            amount=transaction_data.amount,
            type=transaction_data.type,
            correlative=correlative,
            account_id=transaction_data.account_id,
            expense_type_id=transaction_data.expense_type_id,
            income_type_id=transaction_data.income_type_id,
            beneficiary_type=transaction_data.beneficiary_type,
            beneficiary_provider_id=transaction_data.beneficiary_provider_id,
            beneficiary_employee_id=transaction_data.beneficiary_employee_id,
            beneficiary_account_id=transaction_data.beneficiary_account_id,
            # user_id will be handled via auth context in future, for now optional or passed
        )
        
        db.session.add(new_transaction)
        db.session.flush() # Flush to get ID

        # Handle Document
        if 'document' in data and data['document']:
            doc_data = data['document']
            # Basic validation
            if doc_data.get('document_type_id') and doc_data.get('series') and doc_data.get('number'):
                new_doc = TreasuryTransactionDocument(
                    transaction_id=new_transaction.id,
                    document_type_id=doc_data['document_type_id'],
                    series=doc_data['series'],
                    number=doc_data['number'],
                    issuer_ruc=doc_data.get('issuer_ruc'),
                    issuer_name=doc_data.get('issuer_name'),
                    issue_date=datetime.strptime(doc_data['issue_date'], '%Y-%m-%d').date() if doc_data.get('issue_date') else None,
                    amount=doc_data.get('amount') or 0
                )
                db.session.add(new_doc)

        db.session.commit()
        
        return jsonify(new_transaction.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@treasury_api.route('/transactions/<int:id>', methods=['PUT'])
@requires_auth(required_permission='manage:treasury')
def update_transaction(id, payload):
    transaction = TreasuryTransaction.query.get_or_404(id)
    data = request.get_json()
    
    try:
        # Validate with Pydantic (partial update)
        update_data = TransactionUpdate(**data)
        
        if update_data.date:
            transaction.date = update_data.date
        if update_data.description:
            transaction.description = update_data.description
        if update_data.amount is not None:
            transaction.amount = update_data.amount
        if update_data.type:
            transaction.type = update_data.type
        if update_data.account_id:
            transaction.account_id = update_data.account_id
        if update_data.expense_type_id is not None:
            transaction.expense_type_id = update_data.expense_type_id
        if update_data.income_type_id is not None:
            transaction.income_type_id = update_data.income_type_id
        if update_data.beneficiary_type:
            transaction.beneficiary_type = update_data.beneficiary_type
        if update_data.beneficiary_provider_id is not None:
            transaction.beneficiary_provider_id = update_data.beneficiary_provider_id
        if update_data.beneficiary_employee_id is not None:
            transaction.beneficiary_employee_id = update_data.beneficiary_employee_id
        if update_data.beneficiary_account_id is not None:
            transaction.beneficiary_account_id = update_data.beneficiary_account_id
            
        db.session.commit()
        return jsonify(transaction.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@treasury_api.route('/transactions/<int:id>', methods=['DELETE'])
@requires_auth(required_permission='manage:treasury')
def delete_transaction(id, payload):
    transaction = TreasuryTransaction.query.get_or_404(id)
    try:
        db.session.delete(transaction)
        db.session.commit()
        return jsonify({'message': 'Transaction deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# Endpoint to get accounts for the tabs
@treasury_api.route('/accounts', methods=['GET'])
@requires_auth(required_permission='view:treasury')
def get_accounts(payload):
    accounts = BankAccount.query.all()
    return jsonify([a.to_dict() for a in accounts]), 200

# Endpoint to get expense types for the form
@treasury_api.route('/expense-types', methods=['GET'])
@requires_auth(required_permission='view:treasury')
def get_expense_types(payload):
    types = ExpenseType.query.all()
    return jsonify([t.to_dict() for t in types]), 200

# Endpoint to get income types for the form
@treasury_api.route('/income-types', methods=['GET'])
@requires_auth(required_permission='view:treasury')
def get_income_types(payload):
    types = IncomeType.query.all()
    return jsonify([t.to_dict() for t in types]), 200

# --- CATALOG ENDPOINTS (Restored) ---

# 1. Banks
@treasury_api.route('/banks', methods=['GET'])
@requires_auth(required_permission='view:treasury')
def get_banks(payload):
    banks = Bank.query.all()
    return jsonify([b.to_dict() for b in banks]), 200

@treasury_api.route('/banks', methods=['POST'])
@requires_auth(required_permission='manage:treasury')
def create_bank(payload):
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400
    try:
        bank = Bank(name=data['name'])
        db.session.add(bank)
        db.session.commit()
        return jsonify(bank.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@treasury_api.route('/banks/<int:id>', methods=['PUT'])
@requires_auth(required_permission='manage:treasury')
def update_bank(id, payload):
    bank = Bank.query.get_or_404(id)
    data = request.get_json()
    if 'name' in data:
        bank.name = data['name']
    try:
        db.session.commit()
        return jsonify(bank.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@treasury_api.route('/banks/<int:id>', methods=['DELETE'])
@requires_auth(required_permission='manage:treasury')
def delete_bank(id, payload):
    bank = Bank.query.get_or_404(id)
    try:
        db.session.delete(bank)
        db.session.commit()
        return jsonify({'message': 'Bank deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# 2. Account Types
@treasury_api.route('/account-types', methods=['GET'])
@requires_auth(required_permission='view:treasury')
def get_account_types(payload):
    types = AccountType.query.all()
    return jsonify([t.to_dict() for t in types]), 200

@treasury_api.route('/account-types', methods=['POST'])
@requires_auth(required_permission='manage:treasury')
def create_account_type(payload):
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400
    try:
        type_ = AccountType(name=data['name'])
        db.session.add(type_)
        db.session.commit()
        return jsonify(type_.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@treasury_api.route('/account-types/<int:id>', methods=['PUT'])
@requires_auth(required_permission='manage:treasury')
def update_account_type(id, payload):
    type_ = AccountType.query.get_or_404(id)
    data = request.get_json()
    if 'name' in data:
        type_.name = data['name']
    try:
        db.session.commit()
        return jsonify(type_.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@treasury_api.route('/account-types/<int:id>', methods=['DELETE'])
@requires_auth(required_permission='manage:treasury')
def delete_account_type(id, payload):
    type_ = AccountType.query.get_or_404(id)
    try:
        db.session.delete(type_)
        db.session.commit()
        return jsonify({'message': 'Account Type deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# 3. Bank Accounts
@treasury_api.route('/bank-accounts', methods=['GET'])
@requires_auth(required_permission='view:treasury')
def get_bank_accounts(payload):
    accounts = BankAccount.query.all()
    return jsonify([a.to_dict() for a in accounts]), 200

@treasury_api.route('/bank-accounts', methods=['POST'])
@requires_auth(required_permission='manage:treasury')
def create_bank_account(payload):
    data = request.get_json()
    try:
        acc = BankAccount(
            bank_id=data['bank_id'],
            account_type_id=data['account_type_id'],
            alias=data.get('alias'),
            account_number=data['account_number'],
            currency=data.get('currency', 'PEN')
        )
        db.session.add(acc)
        db.session.commit()
        return jsonify(acc.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@treasury_api.route('/bank-accounts/<int:id>', methods=['PUT'])
@requires_auth(required_permission='manage:treasury')
def update_bank_account(id, payload):
    acc = BankAccount.query.get_or_404(id)
    data = request.get_json()
    try:
        if 'bank_id' in data: acc.bank_id = data['bank_id']
        if 'account_type_id' in data: acc.account_type_id = data['account_type_id']
        if 'alias' in data: acc.alias = data['alias']
        if 'account_number' in data: acc.account_number = data['account_number']
        if 'currency' in data: acc.currency = data['currency']
        
        db.session.commit()
        return jsonify(acc.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@treasury_api.route('/bank-accounts/<int:id>', methods=['DELETE'])
@requires_auth(required_permission='manage:treasury')
def delete_bank_account(id, payload):
    acc = BankAccount.query.get_or_404(id)
    try:
        db.session.delete(acc)
        db.session.commit()
        return jsonify({'message': 'Bank Account deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# 4. Expense Types (CRUD)
@treasury_api.route('/expense-types', methods=['POST'])
@requires_auth(required_permission='manage:treasury')
def create_expense_type(payload):
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400
    try:
        et = ExpenseType(name=data['name'], acronym=data.get('acronym'))
        db.session.add(et)
        db.session.commit()
        return jsonify(et.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@treasury_api.route('/expense-types/<int:id>', methods=['PUT'])
@requires_auth(required_permission='manage:treasury')
def update_expense_type(id, payload):
    et = ExpenseType.query.get_or_404(id)
    data = request.get_json()
    try:
        if 'name' in data: et.name = data['name']
        if 'acronym' in data: et.acronym = data['acronym']
        db.session.commit()
        return jsonify(et.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@treasury_api.route('/expense-types/<int:id>', methods=['DELETE'])
@requires_auth(required_permission='manage:treasury')
def delete_expense_type(id, payload):
    et = ExpenseType.query.get_or_404(id)
    try:
        db.session.delete(et)
        db.session.commit()
        return jsonify({'message': 'Expense Type deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
        return jsonify({'error': str(e)}), 400

# 5. Income Types (CRUD)
@treasury_api.route('/income-types', methods=['POST'])
@requires_auth(required_permission='manage:treasury')
def create_income_type(payload):
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400
    try:
        it = IncomeType(name=data['name'], acronym=data.get('acronym'))
        db.session.add(it)
        db.session.commit()
        return jsonify(it.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@treasury_api.route('/income-types/<int:id>', methods=['PUT'])
@requires_auth(required_permission='manage:treasury')
def update_income_type(id, payload):
    it = IncomeType.query.get_or_404(id)
    data = request.get_json()
    try:
        if 'name' in data: it.name = data['name']
        if 'acronym' in data: it.acronym = data['acronym']
        db.session.commit()
        return jsonify(it.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@treasury_api.route('/income-types/<int:id>', methods=['DELETE'])
@requires_auth(required_permission='manage:treasury')
def delete_income_type(id, payload):
    it = IncomeType.query.get_or_404(id)
    try:
        db.session.delete(it)
        db.session.commit()
        return jsonify({'message': 'Income Type deleted'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@treasury_api.route('/document-types', methods=['GET'])
@requires_auth(required_permission='view:treasury')
def get_document_types(payload):
    types = DocumentType.query.all()
    return jsonify([t.to_dict() for t in types]), 200

# --- BENEFICIARY SEARCH ENDPOINTS ---

@treasury_api.route('/lookup-provider/<string:ruc>')
@requires_auth(required_permission='manage:treasury')
def lookup_provider(ruc, payload):
    # 1. Buscar en BD Local primero
    provider = Provider.query.filter_by(ruc=ruc).first()
    if provider:
        return jsonify(provider.to_dict())

    print(f"Consultando RUC {ruc} a la API externa...")
    try:
        api_key = current_app.config.get('SUNAT_API_KEY', '')
        url = f"https://api.decolecta.com/v1/sunat/ruc?numero={ruc}"
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        name = data.get('razon_social') or data.get('nombre') or ''
        
        # Crear proveedor
        try:
            new_provider = Provider(
                ruc=data['numero_documento'],
                name=name
            )
            # Si tuviera address, se agregaría aquí
            
            db.session.add(new_provider)
            db.session.commit()
            
            return jsonify(new_provider.to_dict())
            
        except Exception as db_err:
            print("Error guardando proveedor:", db_err)
            db.session.rollback()
            # Si falla guardar, devolvemos estructura similar
            return jsonify({
                'id': None,
                'ruc': data.get('numero_documento'),
                'name': name
            })

    except requests.exceptions.RequestException as e:
        return jsonify(error=f"Error conectando a SUNAT: {str(e)}"), 404
    except Exception as e:
        return jsonify(error=str(e)), 500

@treasury_api.route('/providers', methods=['GET'])
@requires_auth(required_permission='view:treasury')
def search_providers(payload):
    q = request.args.get('q', '').strip()
    query = Provider.query
    if q:
        query = query.filter(
            (Provider.name.ilike(f'%{q}%')) |
            (Provider.ruc.like(f'{q}%'))
        )
    providers = query.order_by(Provider.name).limit(20).all()
    return jsonify([p.to_dict() for p in providers])

@treasury_api.route('/employees', methods=['GET'])
@requires_auth(required_permission='view:treasury')
def search_employees(payload):
    q = request.args.get('q', '').strip()
    query = Employee.query
    if q:
        query = query.filter(
            (Employee.first_name.ilike(f'%{q}%')) |
            (Employee.last_name.ilike(f'%{q}%')) |
            (Employee.document_number.like(f'{q}%'))
        )
    employees = query.order_by(Employee.last_name).limit(20).all()
    return jsonify([e.to_dict() for e in employees])

# --- ALLOCATION RENDER ENDPOINTS ---

@treasury_api.route('/transactions/<int:id>/renders', methods=['GET'])
@requires_auth(required_permission='view:treasury')
def get_transaction_renders(id, payload):
    transaction = TreasuryTransaction.query.get_or_404(id)
    renders = TreasuryAllocationRender.query.filter_by(transaction_id=id).order_by(TreasuryAllocationRender.created_at.desc()).all()
    return jsonify([r.to_dict() for r in renders]), 200

@treasury_api.route('/transactions/<int:id>/renders', methods=['POST'])
@requires_auth(required_permission='manage:treasury')
def create_transaction_render(id, payload):
    transaction = TreasuryTransaction.query.get_or_404(id)
    data = request.get_json()
    
    try:
        # Validate amount and description
        if not data.get('amount') or not data.get('description'):
             return jsonify({'error': 'Amount and Description are required'}), 400

        # Generate Correlative
        count = TreasuryAllocationRender.query.count()
        correlative = f"R-{str(count + 1).zfill(5)}"

        new_render = TreasuryAllocationRender(
            transaction_id=id,
            correlative=correlative,
            amount=data['amount'],
            description=data['description']
        )
        db.session.add(new_render)
        db.session.flush() # Get ID

        # Handle Document if present
        if 'document' in data and data['document']:
            doc_data = data['document']
            if doc_data.get('document_type_id') and doc_data.get('series') and doc_data.get('number'):
                new_doc = TreasuryRenderDocument(
                    render_id=new_render.id,
                    document_type_id=doc_data['document_type_id'],
                    series=doc_data['series'],
                    number=doc_data['number'],
                    issuer_ruc=doc_data.get('issuer_ruc'),
                    issuer_name=doc_data.get('issuer_name'),
                    issue_date=datetime.strptime(doc_data['issue_date'], '%Y-%m-%d').date() if doc_data.get('issue_date') else None,
                    amount=doc_data.get('amount') or 0
                )
                db.session.add(new_doc)

        db.session.commit()
        return jsonify(new_render.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@treasury_api.route('/renders/<int:id>', methods=['DELETE'])
@requires_auth(required_permission='manage:treasury')
def delete_render(id, payload):
    render = TreasuryAllocationRender.query.get_or_404(id)
    try:
        db.session.delete(render)
        db.session.commit()
        return jsonify({'message': 'Render deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
