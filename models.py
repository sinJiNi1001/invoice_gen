from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# ==========================================
# 1. CUSTOMERS & PROJECTS
# ==========================================
class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)

    def __init__(self, **kwargs):
        super(Customer, self).__init__(**kwargs)

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(100), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))

    def __init__(self, **kwargs):
        super(Project, self).__init__(**kwargs)

# ==========================================
# 2. INVOICES & PAYMENTS
# ==========================================
class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    total_amount = db.Column(db.Float)
    tax_amount = db.Column(db.Float)
    invoice_date = db.Column(db.Date)
    tax_type = db.Column(db.String(20))
    status = db.Column(db.String(20), default='Raised')
    amount_received = db.Column(db.Float, default=0.0)
    billing_type = db.Column(db.String(50))
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'), nullable=True)

    # Relationships
    customer = db.relationship('Customer', backref='invoices')
    project = db.relationship('Project', backref='invoices')

    def __init__(self, **kwargs):
        super(Invoice, self).__init__(**kwargs)

class PaymentSlab(db.Model):
    __tablename__ = 'payment_slabs'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    slab_name = db.Column(db.String(100))
    amount = db.Column(db.Float)

    def __init__(self, **kwargs):
        super(PaymentSlab, self).__init__(**kwargs)

# ==========================================
# 3. SERVICES & CONTRACTS
# ==========================================
class Service(db.Model):
    __tablename__ = 'services'
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.String(50), unique=True)
    service_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

    def __init__(self, **kwargs):
        super(Service, self).__init__(**kwargs)

# Association Table
contract_services = db.Table('contract_services',
    db.Column('contract_id', db.Integer, db.ForeignKey('contracts.id'), primary_key=True),
    db.Column('service_id', db.Integer, db.ForeignKey('services.id'), primary_key=True)
)

class Contract(db.Model):
    __tablename__ = 'contracts'
    
    id = db.Column(db.Integer, primary_key=True)
    # FIX: Renamed 'client_id' to 'customer_id' to match DB
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    contract_name = db.Column(db.String(100), nullable=False)
    po_reference = db.Column(db.String(50))
    total_value = db.Column(db.Float, default=0.0)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='Draft')
    
    # Relationships
    # FIX: Renamed 'client' to 'customer'
    customer = db.relationship('Customer', backref='contracts')
    services = db.relationship('Service', secondary=contract_services, backref='contracts')

    def __init__(self, **kwargs):
        super(Contract, self).__init__(**kwargs)

class ContractSlab(db.Model):
    __tablename__ = 'contract_slabs'
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contracts.id'), nullable=False)
    slab_name = db.Column(db.String(100))
    amount = db.Column(db.Float)
    due_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='Pending')

    def __init__(self, **kwargs):
        super(ContractSlab, self).__init__(**kwargs)