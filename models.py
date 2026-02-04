from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# ==========================================
# 1. INITIALIZE DATABASE
# ==========================================
db = SQLAlchemy()

# ==========================================
# 2. DEFINE MODELS
# ==========================================

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)
    role_id = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    deal_owner = db.Column(db.String(100))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(150))
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    country = db.Column(db.String(50))
    gst_number = db.Column(db.String(50))
    gst_status = db.Column(db.String(20), default='Registered')
    gst_type = db.Column(db.String(20))
    currency = db.Column(db.String(10))
    joined_date = db.Column(db.Date)
    notes = db.Column(db.Text)

    def __init__(self, **kwargs):
        super(Customer, self).__init__(**kwargs)

class Service(db.Model):
    __tablename__ = 'services'
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.String(50))
    service_name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

    def __init__(self, **kwargs):
        super(Service, self).__init__(**kwargs)

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    project_name = db.Column(db.String(150), nullable=False)
    total_value = db.Column(db.Numeric(12, 2))
    payment_type = db.Column(db.String(30))
    status = db.Column(db.String(30), default='Active')

    def __init__(self, **kwargs):
        super(Project, self).__init__(**kwargs)

class PaymentSlab(db.Model):
    __tablename__ = 'payment_slabs'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    slab_name = db.Column(db.String(100))
    percentage = db.Column(db.Numeric(5, 2))
    amount = db.Column(db.Numeric(12, 2))
    due_condition = db.Column(db.String(50))

    def __init__(self, **kwargs):
        super(PaymentSlab, self).__init__(**kwargs)

# --- CONTRACTS MODULE ---
class Contract(db.Model):
    __tablename__ = 'contracts'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    contract_name = db.Column(db.String(150), nullable=False)
    po_reference = db.Column(db.String(255))
    total_value = db.Column(db.Numeric(15, 2), nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(30), default='Draft')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    customer = db.relationship('Customer', backref='contracts')

    def __init__(self, **kwargs):
        super(Contract, self).__init__(**kwargs)

class ContractSlab(db.Model):
    __tablename__ = 'contract_slabs'
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'))
    slab_name = db.Column(db.String(100))
    amount = db.Column(db.Numeric(15, 2))
    due_date = db.Column(db.Date)
    status = db.Column(db.String(30), default='Pending')
    due_condition = db.Column(db.String(50))

    def __init__(self, **kwargs):
        super(ContractSlab, self).__init__(**kwargs)

class ContractService(db.Model):
    __tablename__ = 'contract_services'
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'))

    # --- THIS WAS THE MISSING PIECE ---
    def __init__(self, **kwargs):
        super(ContractService, self).__init__(**kwargs)

# --- INVOICE MODULE ---
class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'), nullable=True)
    contract_slab_id = db.Column(db.Integer, nullable=True)
    
    invoice_date = db.Column(db.Date)
    due_date = db.Column(db.Date)
    invoice_amount = db.Column(db.Numeric(12, 2))
    tax_type = db.Column(db.String(20))
    tax_amount = db.Column(db.Numeric(12, 2))
    total_amount = db.Column(db.Numeric(12, 2))
    
    amount_received = db.Column(db.Numeric(12, 2), default=0.00)
    received_date = db.Column(db.Date, nullable=True)
    billing_type = db.Column(db.String(20), default='Full Payment')
    status = db.Column(db.String(30), default='Draft')
    
    pdf_path = db.Column(db.Text)
    excel_path = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    customer = db.relationship('Customer', backref='invoices')
    project = db.relationship('Project', backref='invoices')
    contract = db.relationship('Contract', backref='invoices')

    def __init__(self, **kwargs):
        super(Invoice, self).__init__(**kwargs)