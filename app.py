from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import mysql.connector
from datetime import date
import datetime
import os
from dotenv import load_dotenv
from typing import List, Dict, Any

# ✅ CORRECT IMPORTS:
from database import db  # Import the single DB instance
from models import Customer, Project, Invoice, PaymentSlab, Service, Contract, ContractSlab, ContractService
from sqlalchemy import desc, extract
from sqlalchemy.exc import IntegrityError

load_dotenv()

app = Flask(__name__)
app.secret_key = "valency_secret"

# A. SQLAlchemy Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Sinu%40123@localhost/invoice_generator'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ✅ INITIALIZE THE SHARED DB
db.init_app(app)

# ... (Rest of your app.py routes remain the same) ...


# Import Models
from models import Customer, Project, Invoice, PaymentSlab, Service, Contract, ContractSlab

db_config = {
    'user': 'root',
    'password': 'Sinu@123', 
    'host': 'localhost',
    'database': 'invoice_generator'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

def fetch_as_dict(cursor) -> List[Dict[str, Any]]:
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

# --- ROOT ---
@app.route('/')
def dashboard():
    return redirect(url_for('edit_list'))

# ==========================================
# INVOICE ROUTES
# ==========================================
def get_next_invoice_number():
    current_year = datetime.datetime.now().year
    prefix = str(current_year)
    last_invoice = Invoice.query.filter(Invoice.invoice_number.like(f"{prefix}%"))\
                                .order_by(desc(Invoice.id)).first()
    if not last_invoice:
        return f"{prefix}001"
    try:
        current_number_str = last_invoice.invoice_number
        sequence_part = current_number_str[len(prefix):]
        new_num = int(sequence_part) + 1
        return f"{prefix}{str(new_num).zfill(3)}"
    except (ValueError, IndexError):
        return f"{prefix}001"

@app.route('/invoice/new', methods=['GET', 'POST'])
def create_invoice():
    customers = Customer.query.all()
    projects = Project.query.all()
    services = Service.query.all()
    suggested_no = get_next_invoice_number()

    if request.method == 'POST':
        project_ids = request.form.getlist('project_ids[]')
        primary_project_id = project_ids[0] if project_ids and project_ids[0].strip() else None
        
        try:
            invoice_date_str = request.form['invoice_date']
            
            new_inv = Invoice(
                invoice_number=request.form.get('invoice_number'),
                customer_id=request.form.get('customer_id'),
                project_id=primary_project_id, 
                total_amount=float(request.form.get('total_amount', 0)),
                tax_amount=float(request.form.get('tax_amount', 0)),
                invoice_date=datetime.datetime.fromisoformat(invoice_date_str),
                tax_type=request.form.get('tax_type'),
                status='Raised',
                amount_received=0.0,
                billing_type=request.form.get('payment_structure') 
            )
            db.session.add(new_inv)
            db.session.commit()
            flash("Invoice created successfully!", "success")
            return redirect(url_for('edit_list'))
        except IntegrityError:
            db.session.rollback()
            flash("Error: This Invoice Number is already in the system.", "danger")
        except Exception as e:
            db.session.rollback()
            flash(f"Database Error: {str(e)}", "danger")

    return render_template('invoice_create.html', customers=customers, projects=projects, services=services, suggested_no=suggested_no)

@app.route('/invoice/edit')
def edit_list():
    page = request.args.get('page', 1, type=int)
    now = datetime.datetime.now()
    
    current_total_months = now.year * 12 + (now.month - 1)
    target_total_months = current_total_months - (page - 1)
    t_year = target_total_months // 12
    t_month = (target_total_months % 12) + 1
    display_label = date(t_year, t_month, 1).strftime('%B %Y')

    oldest_invoice = Invoice.query.order_by(Invoice.invoice_date.asc()).first()
    if oldest_invoice:
        oldest_date = oldest_invoice.invoice_date
        oldest_total_months = oldest_date.year * 12 + (oldest_date.month - 1)
        total_pages = (current_total_months - oldest_total_months) + 1
    else:
        total_pages = 1

    f_day = request.args.get('day', type=int)
    f_month = request.args.get('month', type=int)
    f_year = request.args.get('year', type=int)

    query_all = Invoice.query
    if f_year or f_month or f_day:
        if f_year: query_all = query_all.filter(extract('year', Invoice.invoice_date) == f_year)
        if f_month: query_all = query_all.filter(extract('month', Invoice.invoice_date) == f_month)
        if f_day: query_all = query_all.filter(extract('day', Invoice.invoice_date) == f_day)
        display_label = "Filtered Results"
    else:
        query_all = query_all.filter(
            extract('month', Invoice.invoice_date) == t_month,
            extract('year', Invoice.invoice_date) == t_year
        )

    all_invoices = query_all.order_by(Invoice.invoice_date.desc()).all()
    current_month_query = Invoice.query.filter(
        extract('month', Invoice.invoice_date) == now.month,
        extract('year', Invoice.invoice_date) == now.year
    ).order_by(Invoice.invoice_date.desc())

    return render_template('invoice_list.html', 
                           all_invoices=all_invoices, 
                           new_invoices=current_month_query.limit(10).all(), 
                           edit_invoices=current_month_query.all(),
                           now=now, page=page, total_pages=total_pages, display_label=display_label,
                           current_filters={'day': f_day, 'month': f_month, 'year': f_year})

@app.route('/invoice/edit/<int:id>', methods=['GET', 'POST'])
def edit_form(id):
    invoice = Invoice.query.get_or_404(id)
    customers = Customer.query.all()
    projects = Project.query.all()
    services = Service.query.all()
    
    current_project_slabs = []
    if invoice.project_id:
        current_project_slabs = PaymentSlab.query.filter_by(project_id=invoice.project_id).all()

    if request.method == 'POST':
        try:
            invoice.invoice_number = request.form.get('invoice_number')
            invoice.customer_id = request.form.get('customer_id')
            invoice.project_id = request.form.get('project_id')
            invoice.total_amount = float(request.form.get('total_amount', 0))
            invoice.tax_amount = float(request.form.get('tax_amount', 0))
            invoice.invoice_date = datetime.datetime.fromisoformat(request.form['invoice_date'])
            invoice.tax_type = request.form.get('tax_type')
            invoice.billing_type = request.form.get('payment_structure')

            db.session.commit()
            flash("Invoice updated successfully!", "success")
            return redirect(url_for('edit_list'))
        except Exception as e:
            db.session.rollback()
            flash(f"Update Error: {str(e)}", "danger")
    
    return render_template('invoice_edit.html', invoice=invoice, customers=customers, projects=projects, services=services, slabs=current_project_slabs)

@app.route('/get_slabs/<int:project_id>')
def get_slabs(project_id):
    slabs = PaymentSlab.query.filter_by(project_id=project_id).all()
    return jsonify([{'id': s.id, 'name': s.slab_name, 'amount': float(s.amount)} for s in slabs])


# ==========================================
# CUSTOMER ROUTES
# ==========================================
@app.route('/customers')
def list_customers():
    search = request.args.get('search', '')
    country = request.args.get('country', '')
    sort_by = request.args.get('sort_by', 'newest')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = "SELECT * FROM customers WHERE 1=1"
    params = []
    if search:
        query += " AND company_name LIKE %s"
        params.append(f"%{search}%")
    if country:
        query += " AND country = %s"
        params.append(country)
    
    if sort_by == 'name_asc': query += " ORDER BY company_name ASC"
    elif sort_by == 'oldest': query += " ORDER BY joined_date ASC"
    else: query += " ORDER BY joined_date DESC"
    
    cursor.execute(query, tuple(params))
    customers = fetch_as_dict(cursor)
    conn.close()
    return render_template('customer_list.html', customers=customers, search_term=search, country_filter=country, sort_by=sort_by)

@app.route('/customers/new', methods=('GET', 'POST'))
def create_customer():
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        
        j_date = request.form.get('joined_date')
        if not j_date or j_date.strip() == '': j_date = date.today()

        status = request.form.get('gst_status', 'Registered')
        tax_type = request.form.get('gst_type') if status == 'Registered' else None

        cursor.execute("""
            INSERT INTO customers (
                company_name, first_name, last_name, email, phone, address, 
                city, state, country, deal_owner, gst_status, gst_type, gst_number, 
                currency, joined_date, notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            request.form['company_name'], request.form.get('first_name'), request.form.get('last_name'),
            request.form.get('email'), request.form.get('phone'), request.form.get('address'),
            request.form.get('city'), request.form.get('state'), request.form['country'], 
            request.form.get('deal_owner'), status, tax_type, request.form.get('gst_number'),
            request.form['currency'], j_date, request.form.get('notes')
        ))
        conn.commit()
        conn.close()
        return redirect(url_for('list_customers'))
    
    return render_template('customer_form.html', customer=None)

@app.route('/customers/<int:id>/edit', methods=('GET', 'POST'))
def edit_customer(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        j_date = request.form.get('joined_date')
        if not j_date or j_date.strip() == '': j_date = None
        status = request.form.get('gst_status', 'Registered')
        tax_type = request.form.get('gst_type') if status == 'Registered' else None

        cursor.execute("""
            UPDATE customers SET company_name=%s, first_name=%s, last_name=%s, email=%s, phone=%s, 
                address=%s, city=%s, state=%s, country=%s, deal_owner=%s, gst_status=%s, 
                gst_type=%s, gst_number=%s, currency=%s, joined_date=%s, notes=%s
            WHERE id=%s
        """, (
            request.form['company_name'], request.form.get('first_name'), request.form.get('last_name'),
            request.form.get('email'), request.form.get('phone'), request.form.get('address'),
            request.form.get('city'), request.form.get('state'), request.form['country'], 
            request.form.get('deal_owner'), status, tax_type, request.form.get('gst_number'),
            request.form['currency'], j_date, request.form.get('notes'), id
        ))
        conn.commit()
        conn.close()
        return redirect(url_for('list_customers'))

    cursor.execute("SELECT * FROM customers WHERE id = %s", (id,))
    rows = fetch_as_dict(cursor)
    customer = rows[0] if rows else None
    if customer and customer.get('joined_date'):
        customer['joined_date'] = str(customer['joined_date'])
    conn.close()
    return render_template('customer_form.html', customer=customer)

# ==========================================
# CONTRACT ROUTES
# ==========================================
@app.route('/contracts')
def list_contracts():
    # Get sort parameter from URL, default to 'newest'
    sort_by = request.args.get('sort_by', 'newest')
    
    query = Contract.query
    
    # Sorting Logic
    if sort_by == 'oldest':
        query = query.order_by(Contract.start_date.asc())
    elif sort_by == 'status':
        # Sort by status, then by newest date within that status
        query = query.order_by(Contract.status.asc(), Contract.start_date.desc())
    elif sort_by == 'value_high':
        query = query.order_by(Contract.total_value.desc())
    else: # Default: newest
        query = query.order_by(Contract.start_date.desc())
        
    contracts = query.all()
    
    # Pass 'current_sort' to template so the dropdown stays selected
    return render_template('contract_list.html', contracts=contracts, current_sort=sort_by)

# RENAMED: 'new_contract' -> 'create_contract' to match HTML
@app.route('/contracts/new', methods=['GET', 'POST'])
def create_contract():
    if request.method == 'POST':
        try:
            new_c = Contract(
                customer_id=request.form['customer_id'],
                contract_name=request.form['contract_name'],
                po_reference=request.form.get('po_reference'),
                total_value=float(request.form.get('total_value', 0)),
                start_date=datetime.datetime.fromisoformat(request.form['start_date']),
                end_date=datetime.datetime.fromisoformat(request.form['end_date']),
                status=request.form.get('status', 'Draft')
            )
            
            service_ids = request.form.getlist('service_ids')
            if service_ids:
                selected_services = Service.query.filter(Service.id.in_(service_ids)).all()
                new_c.services.extend(selected_services)

            db.session.add(new_c)
            db.session.commit()
            flash('Contract created successfully!', 'success')
            return redirect(url_for('list_contracts'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating contract: {str(e)}', 'danger')

    clients = Customer.query.all()
    services = Service.query.all()
    return render_template('contract_form.html', customers=clients, services=services)

@app.route('/contracts/edit/<int:contract_id>', methods=['GET', 'POST'])
def edit_contract(contract_id):
    contract = Contract.query.get_or_404(contract_id)
    
    if request.method == 'POST':
        try:
            # 1. Update Basic Info
            contract.contract_name = request.form['contract_name']
            contract.customer_id = request.form['customer_id']
            contract.po_reference = request.form['po_reference']
            contract.total_value = float(request.form.get('total_value', 0))
            contract.start_date = request.form['start_date'] or None
            contract.end_date = request.form['end_date'] or None
            contract.status = request.form.get('status', 'Draft')
            
            # 2. Update Services (Delete old, add new)
            contract.services.clear()
            service_ids = request.form.getlist('service_ids')
            if service_ids:
                selected_services = Service.query.filter(Service.id.in_(service_ids)).all()
                contract.services.extend(selected_services)
            
            # 3. Update Slabs (Delete old, recreate from form data)
            # This ensures added/removed slabs are reflected correctly
            ContractSlab.query.filter_by(contract_id=contract.id).delete()
            
            slab_names = request.form.getlist('slab_names[]')
            slab_amounts = request.form.getlist('slab_amounts[]')
            slab_dates = request.form.getlist('slab_dates[]')
            slab_statuses = request.form.getlist('slab_statuses[]')
            
            for i in range(len(slab_names)):
                if slab_names[i]:
                    # Use existing status if available, else default to Pending
                    current_status = slab_statuses[i] if i < len(slab_statuses) else 'Pending'
                    
                    db.session.add(ContractSlab(
                        contract_id=contract.id,
                        slab_name=slab_names[i],
                        amount=slab_amounts[i],
                        due_date=slab_dates[i] or None,
                        status=current_status
                    ))
            
            db.session.commit()
            flash('Contract updated successfully!', 'success')
            return redirect(url_for('list_contracts'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating: {str(e)}', 'danger')

    customers = Customer.query.all()
    services = Service.query.filter_by(is_active=True).all()
    current_service_ids = [s.id for s in contract.services]
    
    return render_template('contract_form.html', contract=contract, customers=customers, services=services, current_service_ids=current_service_ids)

@app.route('/contracts/update_slab_status/<int:slab_id>/<string:new_status>')
def update_slab_status(slab_id, new_status):
    slab = ContractSlab.query.get_or_404(slab_id)
    slab.status = new_status
    db.session.commit()
    flash(f"Milestone '{slab.slab_name}' marked as {new_status}", "success")
    return redirect(url_for('list_contracts'))

# ==========================================
# SERVICE ROUTES
# ==========================================
@app.route('/services', methods=['GET', 'POST'])
def manage_services():
    if request.method == 'POST':
        try:
            s_name = request.form.get('service_name')
            s_id = request.form.get('service_id')
            s_desc = request.form.get('description')
            
            new_service = Service(
                service_id=s_id, 
                service_name=s_name, 
                description=s_desc, 
                is_active=True
            )
            db.session.add(new_service)
            db.session.commit()
            flash(f"Service '{s_name}' added!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('manage_services'))

    all_services = Service.query.order_by(Service.service_name).all()
    return render_template('services.html', services=all_services)

# ==========================================
# UPDATED API: Now includes Currency
# ==========================================
@app.route('/get_customer_details/<int:id>')
def get_customer_details(id):
    c = Customer.query.get_or_404(id)
    
    return jsonify({
        'gst_number': c.gst_number or 'N/A',
        'gst_status': c.gst_status or 'N/A',
        'gst_type': c.gst_type or 'N/A',
        'city': c.city or '',
        'state': c.state or '',
        'country': c.country or '',
        'currency': c.currency or ''  # <--- Added this!
    })
if __name__ == '__main__':
    app.run(debug=True, port=8000)