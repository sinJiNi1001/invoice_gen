#from sqlalchemy import create_engine
#from sqlalchemy.ext.declarative import declarative_base
#from sqlalchemy.orm import sessionmaker

# Correct URL-encoded password
#SQLALCHEMY_DATABASE_URL = "mysql+pymysql://invoice_user:Sinu%40123@localhost/invoice_app"

#engine = create_engine(
#    SQLALCHEMY_DATABASE_URL,
#    echo=True,  # prints SQL queries for debugging
#)

#SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#Base = declarative_base()

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# --- DATABASE MODELS ---

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(150), nullable=False)
    
    # NEW FIELDS (Matches your recent updates)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    
    address =  db.Column(db.String(150))
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    country = db.Column(db.String(50))
    
    # NEW GST LOGIC
    gst_status = db.Column(db.Enum('Registered', 'No_Forex', 'No_SEZ'))
    gst_type = db.Column(db.Enum('CGST_SGST', 'IGST')) # The Tax Type
    gst_number = db.Column(db.String(50)) 
    
    deal_owner = db.Column(db.String(100))
    joined_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    currency = db.Column(db.String(10))

    # REMOVED: po_ref

class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    
    # LINKED DIRECTLY TO CUSTOMER (Since Projects are gone)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    
    invoice_date = db.Column(db.Date)
    due_date = db.Column(db.Date)
    
    tax_type = db.Column(db.String(20))
    tax_amount = db.Column(db.Numeric(12, 2))
    total_amount = db.Column(db.Numeric(12, 2))
    status = db.Column(db.String(30), default='Raised')

    # Relationships
    customer = db.relationship('Customer', backref='invoices')