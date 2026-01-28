from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models import db, Customer, Project, Invoice, PaymentSlab
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Megha%402004@localhost/invoice_generator'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "valency_secret"
db.init_app(app)

@app.route('/')
def dashboard():
    return render_template('base.html')

import re
import datetime
from sqlalchemy import desc

def get_next_invoice_number():
    current_year = datetime.datetime.now().year
    prefix = f"VAL/{current_year}/"
    
    last_invoice = Invoice.query.filter(Invoice.invoice_number.like(f"{prefix}%"))\
                                .order_by(desc(Invoice.id)).first()

    if not last_invoice:
        return f"{prefix}001"

    match = re.search(r'(\d+)$', last_invoice.invoice_number)
    
    if match:
        last_num_str = match.group(1)
        new_num = int(last_num_str) + 1
        new_num_str = str(new_num).zfill(len(last_num_str))
        
        return re.sub(r'\d+$', new_num_str, last_invoice.invoice_number)

    return f"{prefix}001"

@app.route('/invoice/new', methods=['GET', 'POST'])
def create_invoice():
    # Always fetch these for the dropdowns
    customers = Customer.query.all()
    projects = Project.query.all()
    slabs = PaymentSlab.query.all()
    suggested_no = get_next_invoice_number()
    if request.method == 'POST':

        # 1. Handle Slab ID (Crucial: convert empty string to None)
        raw_slab = request.form.get('slab_id')
        clean_slab_id = None
        if raw_slab and raw_slab.strip():
            clean_slab_id = int(raw_slab)

        # 2. Handle Due Date (Crucial: convert empty string to None)
        raw_due_date = request.form.get('due_date')
        clean_due_date = None
        if raw_due_date and raw_due_date.strip():
            clean_due_date = raw_due_date

        try:
            new_inv = Invoice(
                invoice_number=request.form.get('invoice_number'),
                customer_id=request.form.get('customer_id'),
                project_id=request.form.get('project_id'),
                slab_id=clean_slab_id,      # Uses None if empty
                invoice_date=request.form.get('invoice_date'),
                due_date=clean_due_date,    # Uses None if empty
                tax_type=request.form.get('tax_type'),
                tax_amount=request.form.get('tax_amount'),
                total_amount=request.form.get('total_amount'),
                status='Raised'
            )
            db.session.add(new_inv)
            db.session.commit()
            return redirect(url_for('edit_list'))

        except IntegrityError:
            db.session.rollback()
            flash("Error: This Invoice Number is already in the system.", "danger")
        except Exception as e:
            db.session.rollback()
            # This will show you exactly what went wrong if another error occurs
            flash(f"Database Error: {str(e)}", "danger")

    # If it's a GET request or an error happened, reload the page
    return render_template('create.html', 
                           customers=customers, 
                           projects=projects, 
                           slabs=slabs,
                           suggested_no=suggested_no
                           )

@app.route('/get_slabs/<int:project_id>')
def get_slabs(project_id):
    slabs = PaymentSlab.query.filter_by(project_id=project_id).all()
    return jsonify([{'id': s.id, 'name': s.slab_name, 'amount': float(s.amount)} for s in slabs])


@app.route('/invoice/edit')
def edit_list():
    invoices = Invoice.query.all()
    return render_template('edit_list.html', invoices=invoices)

@app.route('/invoice/edit/<int:id>', methods=['GET', 'POST'])
def edit_form(id):
    invoice = Invoice.query.get_or_404(id)
    customers = Customer.query.all()
    projects = Project.query.all()
    slabs = PaymentSlab.query.all()

    if request.method == 'POST':
        # Handle Slab ID (None if empty)
        raw_slab = request.form.get('slab_id')
        invoice.slab_id = int(raw_slab) if raw_slab and raw_slab.strip() else None
        
        # Update other fields
        invoice.invoice_number = request.form.get('invoice_number')
        invoice.customer_id = request.form.get('customer_id')
        invoice.project_id = request.form.get('project_id')
        invoice.invoice_date = request.form.get('invoice_date')
        invoice.due_date = request.form.get('due_date') or None
        invoice.status = request.form.get('status')
        invoice.tax_type = request.form.get('tax_type')
        invoice.tax_amount = request.form.get('tax_amount')
        invoice.total_amount = request.form.get('total_amount')
        
        db.session.commit()
        return redirect(url_for('edit_list'))
    
    return render_template('edit_form.html', invoice=invoice, customers=customers, projects=projects, slabs=slabs)

if __name__ == '__main__':
    app.run(debug=True)