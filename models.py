from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)
    role_id = db.Column(db.Integer)

class Customer(db.Model):
    __tablename__ = 'customers'
    # Use BigInteger to match SERIAL/BIGINT UNSIGNED
    id = db.Column(db.BigInteger, primary_key=True)
    company_name = db.Column(db.String(150), nullable=False)
    first_name = db.Column(db.String(50)) # Added
    last_name = db.Column(db.String(50))  # Added
    deal_owner = db.Column(db.String(100)) # Added
    address = db.Column(db.String(150))
    city = db.Column(db.String(50))   # Added
    state = db.Column(db.String(50))  # Added
    country = db.Column(db.String(50))
    tax_id = db.Column(db.String(50))
    gst_status = db.Column(db.Enum('Registered', 'No_Forex', 'No_SEZ'), default='Registered') # Added
    gst_type = db.Column(db.Enum('CGST_SGST', 'IGST')) # Added
    gst_number = db.Column(db.String(50)) # Added
    currency = db.Column(db.String(10))
    notes = db.Column(db.Text) # Added

class Service(db.Model):
    __tablename__ = 'services'
    id = db.Column(db.BigInteger, primary_key=True)
    service_id = db.Column(db.String(50)) # The custom code column (e.g. VAPT-01)
    service_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

class Contract(db.Model):
    __tablename__ = 'contracts'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.BigInteger, db.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False)
    contract_name = db.Column(db.String(150), nullable=False)
    po_reference = db.Column(db.String(255))
    total_value = db.Column(db.Numeric(15, 2), nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.Enum('Draft', 'Active', 'On Hold', 'Completed', 'Terminated'), default='Draft')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.BigInteger, db.ForeignKey('customers.id'))
    project_name = db.Column(db.String(150), nullable=False)
    total_value = db.Column(db.Numeric(12, 2))
    payment_type = db.Column(db.String(30))

class PaymentSlab(db.Model):
    __tablename__ = 'payment_slabs'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    slab_name = db.Column(db.String(100))
    percentage = db.Column(db.Numeric(5, 2))
    amount = db.Column(db.Numeric(12, 2))

class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.BigInteger, db.ForeignKey('customers.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    
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

    # Relationships
    customer = db.relationship('Customer', backref='invoices')
    project = db.relationship('Project', backref='invoices')