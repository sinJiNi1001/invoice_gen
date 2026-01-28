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
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), nullable=False)
    address =  db.Column(db.String(150))
    country = db.Column(db.String(50))
    tax_id = db.Column(db.String(50))
    currency = db.Column(db.String(10))

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    project_name = db.Column(db.String(150), nullable=False)
    total_value = db.Column(db.Numeric(12, 2))
    payment_type = db.Column(db.String(30))

# ADD THIS CLASS - This fixes your ImportError
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
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    slab_id = db.Column(db.Integer, db.ForeignKey('payment_slabs.id')) # Reference to Slabs
    invoice_date = db.Column(db.Date)
    due_date = db.Column(db.Date)
    tax_type = db.Column(db.String(20))
    tax_amount = db.Column(db.Numeric(12, 2))
    total_amount = db.Column(db.Numeric(12, 2))
    status = db.Column(db.String(30), default='Raised')

    class Service(db.Model):
        __tablename__ = 'services'
        id = db.Column(db.Integer, primary_key=True)
        service_name = db.Column(db.String(150), nullable=False)
        default_rate = db.Column(db.Float, default=0.0)
        description = db.Column(db.Text)
        

    # Relationships to help pull names in HTML
    customer = db.relationship('Customer', backref='invoices')
    project = db.relationship('Project', backref='invoices')