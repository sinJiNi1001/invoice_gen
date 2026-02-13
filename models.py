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
    address = db.Column(db.String(255))
    address2 = db.Column(db.String(255))
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    pincode = db.Column(db.String(20))
    country = db.Column(db.String(50))
    gst_number = db.Column(db.String(50))
    gst_file_path = db.Column(db.String(50))
    gst_status = db.Column(db.String(20), default='Registered')
    gst_type = db.Column(db.String(20))
    tax_disclaimer = db.Column(db.Text)
    currency = db.Column(db.String(10))
    joined_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    documents = db.relationship('CustomerDocument', backref='customer', cascade="all, delete-orphan")
    
    # REMOVED: Redundant relationship definitions here.
    # The backrefs in Contract and Invoice will automatically 
    # create 'customer.contracts' and 'customer.invoices' for you.


    def __init__(self, **kwargs):
        super(Customer, self).__init__(**kwargs)

class CustomerDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.now)


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
    
    # Relationships
    # This backref='contracts' AUTOMATICALLY creates Customer.contracts
    customer = db.relationship('Customer', backref='contracts')
    services = db.relationship('Service', secondary='contract_services', backref='contracts')
    slabs = db.relationship('ContractSlab', backref='contract', lazy=True)

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

    def __init__(self, **kwargs):
        super(ContractService, self).__init__(**kwargs)        

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
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id', ondelete='CASCADE'))
    project_name = db.Column(db.String(150), nullable=False)
    po_number = db.Column(db.String(100)) # Added this line
    service_type = db.Column(db.String(100)) # Web App, VAPT, etc.
    description = db.Column(db.String(100))
    service_breakdown = db.Column(db.Text)
    start_date = db.Column(db.Date)
    total_value = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(10), default='INR')
    payment_type = db.Column(db.String(30)) # Full Payment / Milestone-based
    status = db.Column(db.Enum('Active', 'Completed', 'On Hold', 'Cancelled'), default='Active')

    customer = db.relationship('Customer', backref=db.backref('projects', lazy=True))
    slabs = db.relationship('PaymentSlab', backref='project', cascade="all, delete-orphan")

class PaymentSlab(db.Model):
    __tablename__ = 'payment_slabs'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'))
    slab_name = db.Column(db.String(100))
    percentage = db.Column(db.Numeric(5, 2))
    amount = db.Column(db.Numeric(12, 2))
    due_condition = db.Column(db.String(50), default='Immediate')

# --- INVOICE MODULE ---
class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'), nullable=True)
    contract_slab_id = db.Column(db.Integer, nullable=True)
    
    # Matches selected_slab in your create_invoice route
    slab_name = db.Column(db.String(200), nullable=True) 
    
    invoice_date = db.Column(db.Date)
    due_date = db.Column(db.Date)
    
    # Financial Fields
    invoice_amount = db.Column(db.Numeric(12, 2)) # Base amount before tax
    tax_type = db.Column(db.String(20))
    tax_amount = db.Column(db.Numeric(12, 2))     # tax calculated by JS
    total_amount = db.Column(db.Numeric(12, 2))   # invoice_amount + tax_amount
    
    amount_received = db.Column(db.Numeric(12, 2), default=0.00)
    received_date = db.Column(db.Date, nullable=True)
    
    # Matches request.form.get('payment_type')
    billing_type = db.Column(db.String(20), default='Full Payment') 
    status = db.Column(db.String(30), default='Raised') # Default changed from Draft
    
    pdf_path = db.Column(db.Text)
    excel_path = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # --- Relationships ---
    customer = db.relationship('Customer', backref='invoices')
    project = db.relationship('Project', backref='invoices')
    contract = db.relationship('Contract', backref='invoices')
   
    # ADD THIS: This links to the line items table so they show in invoice_list
    items = db.relationship('InvoiceItem', backref='invoice', cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        # Handle date conversion if strings are passed
        if 'invoice_date' in kwargs and isinstance(kwargs['invoice_date'], str):
            kwargs['invoice_date'] = datetime.strptime(kwargs['invoice_date'], '%Y-%m-%d').date()
        if 'due_date' in kwargs and isinstance(kwargs['due_date'], str):
            kwargs['due_date'] = datetime.strptime(kwargs['due_date'], '%Y-%m-%d').date()
            
        super(Invoice, self).__init__(**kwargs)

class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=True)
    amount = db.Column(db.Numeric(12, 2), default=0.00)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'), nullable=True)
    # Links to get names easily in the list view
    project = db.relationship('Project')
    service = db.relationship('Service')        