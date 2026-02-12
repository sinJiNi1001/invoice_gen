from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import mysql.connector
from datetime import date
import datetime
import os
import json


from typing import List, Dict, Any  # <--- Add this line
from werkzeug.utils import secure_filename

# DATABASE & MODELS
from models import db, Customer, Project, Invoice, PaymentSlab, Service, Contract, ContractSlab, ContractService, InvoiceItem, CustomerDocument
from sqlalchemy import desc, extract
from sqlalchemy.exc import IntegrityError


app = Flask(__name__)
app.secret_key = "valency_secret"

# Configure Upload Folder
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# A. SQLAlchemy Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Sinu%40123@localhost/invoice_generator'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# INITIALIZE DB
db.init_app(app)

# Use the SAME credentials for Raw MySQL
db_config = {
    'user': 'root',
    'password': 'Sinu@123', 
    'host': 'localhost',
    'database': 'invoice_generator',
    'auth_plugin': 'mysql_native_password' # <--- Adding this fixes cryptography/auth errors
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

def fetch_as_dict(cursor) -> List[Dict[str, Any]]:
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


@app.route('/')
def dashboard():
    # Get parameters from URL
    tab = request.args.get('tab', 'invoices')  # Default to Invoices
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'newest')
    # NEW: Capture the invoice type filter
    invoice_type = request.args.get('invoice_type', 'all')
    per_page = 10

    data = None
    pagination = None
    
    # 1. INVOICES TAB
    if tab == 'invoices':
        query = Invoice.query
        
        # NEW: Apply Type Filter (Project vs Contract)
        if invoice_type == 'project':
            query = query.filter(Invoice.contract_id.is_(None))
        elif invoice_type == 'contract':
            query = query.filter(Invoice.contract_id.isnot(None))
            
        if sort == 'oldest': query = query.order_by(Invoice.invoice_date.asc())
        elif sort == 'amount_high': query = query.order_by(Invoice.total_amount.desc())
        elif sort == 'amount_low': query = query.order_by(Invoice.total_amount.asc())
        else: query = query.order_by(Invoice.invoice_date.desc()) # Newest default
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
    # 2. CONTRACTS TAB
    elif tab == 'contracts':
        query = Contract.query
        if sort == 'oldest': query = query.order_by(Contract.start_date.asc())
        elif sort == 'value_high': query = query.order_by(Contract.total_value.desc())
        elif sort == 'status': query = query.order_by(Contract.status.asc())
        else: query = query.order_by(Contract.start_date.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # 3. CUSTOMERS TAB
    elif tab == 'customers':
        query = Customer.query
        if sort == 'name_asc': query = query.order_by(Customer.company_name.asc())
        elif sort == 'name_desc': query = query.order_by(Customer.company_name.desc())
        elif sort == 'oldest': query = query.order_by(Customer.joined_date.asc())
        else: query = query.order_by(Customer.joined_date.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # 4. PROJECTS TAB
    elif tab == 'projects':
        query = Project.query
        if sort == 'name_asc': query = query.order_by(Project.project_name.asc())
        else: query = query.order_by(Project.id.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # 5. SERVICES TAB
    elif tab == 'services':
        query = Service.query
        if sort == 'name_desc': query = query.order_by(Service.service_name.desc())
        else: query = query.order_by(Service.service_name.asc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('dashboard.html', 
                           tab=tab, 
                           pagination=pagination, 
                           sort=sort,
                           invoice_type=invoice_type) # Added parameter
# ==========================================
# 2. INVOICE ROUTES (Restored Logic)
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


import json
@app.route('/invoice/new', methods=['GET', 'POST'])
def create_invoice():
    customers = Customer.query.all()
    projects = Project.query.all()
    services = Service.query.all()
    suggested_no = get_next_invoice_number()

    # Get the slab name from the hidden input field
    selected_slab = request.form.get('linked_slab_name')
    
    import json
    for p in projects:
    # 1. Handle Slabs (Existing logic)
        slabs = PaymentSlab.query.filter_by(project_id=p.id).all()
        slabs_data = [{'slab_name': s.slab_name, 'percent': float(s.percentage) if s.percentage else 0} for s in slabs]
        p.slabs_list_json = json.dumps(slabs_data)
    
    # 2. Handle Service Breakdown (The Fix)
        if p.service_breakdown:
            try:
                # Ensure it's a valid serializable string for the data-attribute
                if isinstance(p.service_breakdown, str):
                    p.breakdown_json = p.service_breakdown
                else:
                    p.breakdown_json = json.dumps(p.service_breakdown)
            except:
                p.breakdown_json = "{}"
        else:
            p.breakdown_json = "{}"

    if request.method == 'POST':
        # FIXED: Ensure pid pulls from the correct form field
        pid = request.form.get('project_id') 
        
        try:
            # FIXED: total_amount must match the 'name' attribute in your HTML
            invoice_date_str = request.form.get('invoice_date')
            invoice_date = datetime.datetime.strptime(invoice_date_str, '%Y-%m-%d') if invoice_date_str else datetime.datetime.now()
            
            new_inv = Invoice(
                invoice_number=request.form.get('invoice_number'),
                customer_id=request.form.get('customer_id'),
                project_id=pid, 
                total_amount=float(request.form.get('total_amount', 0)), # Match HTML name
                tax_amount=float(request.form.get('tax_amount', 0)),     # Match HTML name
                invoice_date=invoice_date,
                tax_type=request.form.get('tax_type'),
                status='Raised',
                amount_received=float(request.form.get('amount_received', 0)), # Match HTML name
                slab_name=selected_slab,
                billing_type=request.form.get('payment_type') 
            )
            db.session.add(new_inv)
            db.session.flush() # Get the ID for line items

            # NEW: Save the multiple line items so they show in "Service Details"
           # ... (inside POST after db.session.flush())
            proj_list = request.form.getlist('project_ids[]')
            serv_list = request.form.getlist('service_ids[]')
            amt_list = request.form.getlist('amounts[]')

            for i in range(len(serv_list)):
                if serv_list[i]: 
                    # CHANGE THIS: Use InvoiceItem, NOT Invoice
                    item = InvoiceItem()
                    item.invoice_id = new_inv.id
                    item.service_id = int(serv_list[i]) if serv_list[i] else None
                    item.amount = float(amt_list[i] if amt_list[i] else 0)
                    db.session.add(item)

            db.session.commit()
            flash("Invoice created successfully!", "success")
            return redirect(url_for('edit_list'))
        except Exception as e:
            db.session.rollback()
            flash(f"Database Error: {str(e)}", "danger")

    return render_template('invoice_create.html', 
                           customers=customers, 
                           projects=projects, 
                           services=services, 
                           suggested_no=suggested_no)

@app.route('/get_slabs/<int:project_id>')
def get_slabs(project_id):
    slabs = PaymentSlab.query.filter_by(project_id=project_id).all()
    return jsonify([{'id': s.id, 'name': s.slab_name, 'amount': float(s.amount)} for s in slabs])


@app.route('/invoice/edit/<int:id>', methods=['GET', 'POST'])
def edit_invoice(id):
    invoice = Invoice.query.get_or_404(id)
    customers = Customer.query.all()
    projects = Project.query.all()
    services = Service.query.all()

    
    import json
    for p in projects:
    # 1. Handle Slabs (Existing logic)
        slabs = PaymentSlab.query.filter_by(project_id=p.id).all()
        slabs_data = [{'slab_name': s.slab_name, 'percent': float(s.percentage) if s.percentage else 0} for s in slabs]
        p.slabs_list_json = json.dumps(slabs_data)
    
    # 2. Handle Service Breakdown (The Fix)
        if p.service_breakdown:
            try:
                # Ensure it's a valid serializable string for the data-attribute
                if isinstance(p.service_breakdown, str):
                    p.breakdown_json = p.service_breakdown
                else:
                    p.breakdown_json = json.dumps(p.service_breakdown)
            except:
                p.breakdown_json = "{}"
        else:
            p.breakdown_json = "{}"
   
    if request.method == 'POST':
        try:
            # 1. Update main Invoice details
            invoice.invoice_number = request.form.get('invoice_number')
            invoice.customer_id = request.form.get('customer_id')
            invoice.project_id = request.form.get('project_id')
            invoice.total_amount = float(request.form.get('total_amount', 0))
            invoice.tax_amount = float(request.form.get('tax_amount', 0))
            invoice_date_str = request.form.get('invoice_date')
            invoice.invoice_date = datetime.datetime.strptime(invoice_date_str, '%Y-%m-%d') if invoice_date_str else datetime.datetime.now()
            invoice.tax_type = request.form.get('tax_type')
            invoice.slab_name = request.form.get('linked_slab_name')
            invoice.billing_type = request.form.get('payment_type')
            invoice.status = request.form.get('status')
            
            # Optional: update amount_received if you have it in your form
            amount_received = request.form.get('amount_received', '0').strip()
            invoice.amount_received = float(amount_received) if amount_received else 0.0

            # 2. Clear existing InvoiceItems and replace with new ones
            # (Standard practice for "Edit" to ensure consistency)
            InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()

            proj_list = request.form.getlist('project_ids[]')
            serv_list = request.form.getlist('service_ids[]')
            amt_list = request.form.getlist('amounts[]')

            for i in range(len(serv_list)):
                if serv_list[i]:
                    item = InvoiceItem(
                        invoice_id=invoice.id,
                        service_id=int(serv_list[i]) if serv_list[i] and serv_list[i].strip() else None,
                        amount=float(amt_list[i] if amt_list[i] else 0)
                    )
                    db.session.add(item)

            db.session.commit()
            flash("Invoice updated successfully!", "success")
            return redirect(url_for('edit_list'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error updating invoice: {str(e)}", "danger")

    return render_template('invoice_create.html', 
                           invoice=invoice, 
                           customers=customers, 
                           projects=projects, 
                           services=services)


from sqlalchemy import extract

@app.route('/invoice/edit')
def edit_list():
    # 1. Fetch data for Create/Edit Modals (Keep as is)
    customers = Customer.query.all()
    projects = Project.query.all()
    services = Service.query.all()
    suggested_no = get_next_invoice_number()

    for p in projects:
        slabs = PaymentSlab.query.filter_by(project_id=p.id).all()
        slabs_data = [
            {'slab_name': s.slab_name, 'percent': float(s.percentage) if s.percentage else 0} 
            for s in slabs
        ]
        p.slabs_list_json = json.dumps(slabs_data)
        
        if p.service_breakdown:
            if isinstance(p.service_breakdown, dict):
                clean_breakdown = {k: float(v) if hasattr(v, '__float__') else v 
                                  for k, v in p.service_breakdown.items()}
                p.breakdown_json = json.dumps(clean_breakdown)
            else:
                p.breakdown_json = p.service_breakdown
        else:
            p.breakdown_json = "{}"

    # 2. Pagination & Date Logic (Keep as is)
    page = request.args.get('page', 1, type=int)
    now = datetime.datetime.now()
    
    current_total_months = now.year * 12 + (now.month - 1)
    target_total_months = current_total_months - (page - 1)
    t_year = target_total_months // 12
    t_month = (target_total_months % 12) + 1
    
    display_label = datetime.date(t_year, t_month, 1).strftime('%B %Y')

    oldest_invoice = Invoice.query.order_by(Invoice.invoice_date.asc()).first()
    if oldest_invoice:
        o_date = oldest_invoice.invoice_date
        if isinstance(o_date, str):
            o_date = datetime.datetime.strptime(o_date, '%Y-%m-%d')
        oldest_total_months = o_date.year * 12 + (o_date.month - 1)
        total_pages = max((current_total_months - oldest_total_months) + 1, 1)
    else:
        total_pages = 1

    # 3. Filtering Logic (FIXED FOR INVOICE TYPE)
    f_day = request.args.get('day', type=int)
    f_month = request.args.get('month', type=int)
    f_year = request.args.get('year', type=int)
    f_type = request.args.get('invoice_type', 'all') # Default to 'all'

    query_all = Invoice.query.options(db.joinedload(Invoice.customer), db.joinedload(Invoice.project))
    
    # Apply Type Filter Logic
    if f_type == 'contract':
        # Assumes contract invoices have a contract_id and NO project_id
        query_all = query_all.filter(Invoice.contract_id.isnot(None))
    elif f_type == 'project':
        # Assumes project invoices have a project_id and NO contract_id
        query_all = query_all.filter(Invoice.project_id.isnot(None))

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
    )

    # --- APPLY TYPE FILTER TO TABS ---
    if f_type == 'contract':
        current_month_query = current_month_query.filter(Invoice.contract_id.isnot(None))
    elif f_type == 'project':
        # Assuming project invoices have no contract_id
        current_month_query = current_month_query.filter(Invoice.contract_id.is_(None))

    # New Created: Just the 10 most recent from this month (now type-filtered)
    new_invoices = current_month_query.order_by(Invoice.id.desc()).limit(10).all()

    # Edit: Invoices from this month that are not yet "Paid" (now type-filtered)
    edit_invoices = current_month_query.filter(Invoice.status != 'Paid').order_by(Invoice.invoice_date.desc()).all()
    return render_template('invoice_list.html', 
                           all_invoices=all_invoices, 
                           new_invoices=new_invoices, 
                           edit_invoices=edit_invoices,
                           customers=customers,
                           projects=projects,
                           services=services,
                           suggested_no=suggested_no,
                           now=now, 
                           page=page, 
                           total_pages=total_pages, 
                           display_label=display_label,
                           current_filters={
                               'day': f_day, 
                               'month': f_month, 
                               'year': f_year, 
                               'invoice_type': f_type
                           })


# ==========================================
# 3.Contract Invoice ROUTES     
# ==========================================
@app.route('/invoice/contract/new', methods=['GET', 'POST'])
@app.route('/invoice/contract/edit/<int:id>', methods=['GET', 'POST'])
def contract_invoice(id=None):
    # Fetch core data
    now = datetime.datetime.now()
    customers = Customer.query.all()
    contracts = Contract.query.all()
    services = Service.query.all()
    suggested_no = get_next_invoice_number()
    
    # If editing, fetch existing invoice
    invoice = Invoice.query.get(id) if id else None

    # --- CORRECTED LOOP START ---
    import json
    for c in contracts:
        # 1. Fetch Slabs (Indented inside the loop)
        slabs = ContractSlab.query.filter_by(contract_id=c.id).all()
        c.slabs_list_json = json.dumps([
            {'id': s.id, 'name': s.slab_name, 'amount': float(s.amount or 0)} 
            for s in slabs
        ])

        # 2. Fetch Primary Service (Now inside the loop where 'c' is defined)
        primary_serv = ContractService.query.filter_by(contract_id=c.id).first()
        c.primary_service_id = primary_serv.service_id if primary_serv else ""
    # --- END OF LOOP ---

    if request.method == 'POST':
        try:
            # 1. Create or Update Invoice Header
            if not invoice:
                invoice = Invoice()
                db.session.add(invoice)

            invoice.invoice_number = request.form.get('invoice_number')
            invoice.customer_id = request.form.get('customer_id')
            invoice.contract_id = request.form.get('contract_id') 
            invoice.total_amount = float(request.form.get('total_amount', 0))
            invoice.tax_amount = float(request.form.get('tax_amount', 0))
            invoice_date_str = request.form.get('invoice_date')
            invoice.invoice_date = datetime.datetime.strptime(invoice_date_str, '%Y-%m-%d') if invoice_date_str else datetime.datetime.now()
            invoice.tax_type = request.form.get('tax_type')
            invoice.status = request.form.get('status', 'Raised')
            invoice.slab_name = request.form.get('linked_slab_name') 
            
            db.session.flush()

            # 2. Update Invoice Items
            InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()

            serv_list = request.form.getlist('service_ids[]')
            amt_list = request.form.getlist('amounts[]')

            for i in range(len(serv_list)):
                if amt_list[i] and float(amt_list[i]) > 0:
                    item = InvoiceItem()
                    item.invoice_id = invoice.id
                    item.contract_id = invoice.contract_id
                    item.service_id = int(serv_list[i]) if serv_list[i] else None
                    item.amount = float(amt_list[i])
                    db.session.add(item)

            db.session.commit()
            flash(f"Contract Invoice {'updated' if id else 'created'} successfully!", "success")
            return redirect(url_for('edit_list'))

        except Exception as e:
            db.session.rollback()
            flash(f"Error: {str(e)}", "danger")

    return render_template('invoice_contract_form.html', 
                           invoice=invoice,
                           customers=customers, 
                           contracts=contracts, 
                           services=services, 
                           suggested_no=suggested_no,
                           now=now)
# ==========================================
# 3. CUSTOMER ROUTES (Raw SQL)
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
        tax_type = request.form.get('gst_type')

        # 1. Insert Customer
        cursor.execute("""
            INSERT INTO customers (
                company_name, first_name, last_name, email, phone, address, 
                city, state, country, deal_owner, gst_status, gst_type, gst_number, 
                currency, joined_date, notes, tax_disclaimer
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            request.form['company_name'], request.form.get('first_name'), request.form.get('last_name'),
            request.form.get('email'), request.form.get('phone'), request.form.get('address'),
            request.form.get('city'), request.form.get('state'), request.form['country'], 
            request.form.get('deal_owner'), status, tax_type, request.form.get('gst_number'),
            request.form['currency'], j_date, request.form.get('notes'),
            request.form.get('tax_disclaimer')
        ))
        
        # Get the new ID
        conn.commit()
        new_customer_id = cursor.lastrowid

        # 2. Handle Multiple Files
        files = request.files.getlist('documents')
        for file in files:
            if file and file.filename != '':
                filename = secure_filename(file.filename or '')
                # Make filename unique
                unique_filename = f"{new_customer_id}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))

                cursor.execute(
                    "INSERT INTO customer_documents (customer_id, filename) VALUES (%s, %s)",
                    (new_customer_id, unique_filename)
                )

        conn.commit()
        conn.close()
        return redirect(url_for('list_customers'))
    
    return render_template('customer_form.html', customer=None, documents=[])

@app.route('/customers/<int:id>/edit', methods=('GET', 'POST'))
def edit_customer(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        j_date = request.form.get('joined_date')
        if not j_date or j_date.strip() == '': j_date = None
        status = request.form.get('gst_status', 'Registered')
        tax_type = request.form.get('gst_type')

        # 1. Update Customer Data
        cursor.execute("""
            UPDATE customers SET company_name=%s, first_name=%s, last_name=%s, email=%s, phone=%s, 
                address=%s, city=%s, state=%s, country=%s, deal_owner=%s, gst_status=%s, 
                gst_type=%s, gst_number=%s, currency=%s, joined_date=%s, notes=%s, 
                tax_disclaimer=%s
            WHERE id=%s
        """, (
            request.form['company_name'], request.form.get('first_name'), request.form.get('last_name'),
            request.form.get('email'), request.form.get('phone'), request.form.get('address'),
            request.form.get('city'), request.form.get('state'), request.form['country'], 
            request.form.get('deal_owner'), status, tax_type, request.form.get('gst_number'),
            request.form['currency'], j_date, request.form.get('notes'), 
            request.form.get('tax_disclaimer'), id
        ))

        # 2. Handle New File Uploads (Append to list)
        files = request.files.getlist('documents')
        for file in files:
            if file and file.filename != '':
                filename = secure_filename(file.filename or '')
                unique_filename = f"{id}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))

                cursor.execute(
                    "INSERT INTO customer_documents (customer_id, filename) VALUES (%s, %s)",
                    (id, unique_filename)
                )

        conn.commit()
        conn.close()
        return redirect(url_for('list_customers'))

    # GET Request: Fetch Customer
    cursor.execute("SELECT * FROM customers WHERE id = %s", (id,))
    rows = fetch_as_dict(cursor)
    customer = rows[0] if rows else None
    
    if customer and customer.get('joined_date'):
        customer['joined_date'] = str(customer['joined_date'])

    # Fetch Documents
    cursor.execute("SELECT * FROM customer_documents WHERE customer_id = %s", (id,))
    documents = fetch_as_dict(cursor)

    conn.close()
    return render_template('customer_form.html', customer=customer, documents=documents)


@app.route('/document/delete/<int:doc_id>')
def delete_document(doc_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get info to delete file from disk
    cursor.execute("SELECT * FROM customer_documents WHERE id = %s", (doc_id,))
    doc = cursor.fetchone()
    
    if doc:
        # 1. Delete from Disk
        try:
            filename = doc.get('filename') if isinstance(doc, dict) else doc[1]
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], str(filename)))
        except OSError:
            pass # File might already be gone

        # 2. Delete from DB
        cursor.execute("DELETE FROM customer_documents WHERE id = %s", (doc_id,))
        conn.commit()
        flash("Document deleted.", "success")
        
        customer_id = doc.get('customer_id') if isinstance(doc, dict) else doc[2]
        conn.close()
        return redirect(url_for('edit_customer', id=customer_id))
    
    conn.close()
    return redirect(url_for('list_customers'))


# ==========================================
# 4. CONTRACT ROUTES (Raw SQL)
# ==========================================

# ==========================================
# CONTRACT ROUTES
# ==========================================

@app.route('/contracts/new', methods=['GET', 'POST'])
def create_contract():
    if request.method == 'POST':
        try:
            # SAFETY FIX: Handle empty Total Value
            t_val = request.form.get('total_value', '').strip()
            total_val = float(t_val) if t_val else 0.0

            new_c = Contract(
                customer_id=request.form['customer_id'],
                contract_name=request.form['contract_name'],
                po_reference=request.form.get('po_reference'),
                total_value=total_val,
                start_date=datetime.datetime.fromisoformat(request.form['start_date']),
                end_date=datetime.datetime.fromisoformat(request.form['end_date']),
                status=request.form.get('status', 'Draft')
            )
            
            # Add Services
            service_ids = request.form.getlist('service_ids')
            if service_ids:
                selected_services = Service.query.filter(Service.id.in_(service_ids)).all()
                new_c.services.extend(selected_services)

            db.session.add(new_c)
            db.session.commit()
            
            # Add Slabs (Milestones)
            slab_names = request.form.getlist('slab_names[]')
            slab_amounts = request.form.getlist('slab_amounts[]')
            slab_dates = request.form.getlist('slab_dates[]')

            for i in range(len(slab_names)):
                if slab_names[i]:
                    # SAFETY FIX: Handle empty Slab Amount
                    s_amt_str = slab_amounts[i].strip()
                    s_amt = float(s_amt_str) if s_amt_str else 0.0
                    
                    # SAFETY FIX: Handle empty Date
                    s_date = slab_dates[i] if slab_dates[i] else None

                    db.session.add(ContractSlab(
                        contract_id=new_c.id,
                        slab_name=slab_names[i],
                        amount=s_amt,
                        due_date=s_date,
                        status='Pending'
                    ))
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
            contract.contract_name = request.form['contract_name']
            contract.customer_id = request.form['customer_id']
            contract.po_reference = request.form['po_reference']
            
            # SAFETY FIX: Total Value
            t_val = request.form.get('total_value', '').strip()
            contract.total_value = float(t_val) if t_val else 0.0

            contract.start_date = request.form['start_date'] or None
            contract.end_date = request.form['end_date'] or None
            contract.status = request.form.get('status', 'Draft')
            
            # Update Services
            contract.services.clear()
            service_ids = request.form.getlist('service_ids')
            if service_ids:
                selected_services = Service.query.filter(Service.id.in_(service_ids)).all()
                contract.services.extend(selected_services)
            
            # Update Slabs (Delete all & Re-add)
            ContractSlab.query.filter_by(contract_id=contract.id).delete()
            
            slab_names = request.form.getlist('slab_names[]')
            slab_amounts = request.form.getlist('slab_amounts[]')
            slab_dates = request.form.getlist('slab_dates[]')
            slab_statuses = request.form.getlist('slab_statuses[]')
            
            for i in range(len(slab_names)):
                if slab_names[i]:
                    # SAFETY FIX: Slab Amount
                    s_amt_str = slab_amounts[i].strip()
                    s_amt = float(s_amt_str) if s_amt_str else 0.0
                    
                    s_date = slab_dates[i] if slab_dates[i] else None
                    current_status = slab_statuses[i] if i < len(slab_statuses) else 'Pending'
                    
                    db.session.add(ContractSlab(
                        contract_id=contract.id,
                        slab_name=slab_names[i],
                        amount=s_amt,
                        due_date=s_date,
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
@app.route('/contracts')
def list_contracts():
    sort_by = request.args.get('sort_by', 'newest')
    
    query = Contract.query
    
    if sort_by == 'oldest':
        query = query.order_by(Contract.start_date.asc())
    elif sort_by == 'status':
        query = query.order_by(Contract.status.asc(), Contract.start_date.desc())
    elif sort_by == 'value_high':
        query = query.order_by(Contract.total_value.desc())
    else: 
        query = query.order_by(Contract.start_date.desc())
        
    contracts = query.all()
    return render_template('contract_list.html', contracts=contracts, current_sort=sort_by)

@app.route('/contracts/update_slab_status/<int:slab_id>/<string:new_status>')
def update_slab_status(slab_id, new_status):
    slab = ContractSlab.query.get_or_404(slab_id)
    slab.status = new_status
    db.session.commit()
    flash(f"Milestone '{slab.slab_name}' marked as {new_status}", "success")
    return redirect(url_for('list_contracts'))



# ==========================================
# 5. SERVICE MANAGEMENT ROUTES
# ==========================================
# ==========================================
# SERVICES ROUTE
# ==========================================

@app.route('/services', methods=['GET', 'POST'])
def manage_services():
    if request.method == 'POST':
        try:
            s_name = request.form.get('service_name')
            if s_name:
                new_service = Service(
                    service_name=s_name,
                    is_active=True
                )
                db.session.add(new_service)
                db.session.commit()
                flash(f"Service '{s_name}' added successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {str(e)}", "danger")
        return redirect(url_for('manage_services'))

    # Crucial part: Sort by ID ASCENDING to append new items at the end
    all_services = Service.query.order_by(Service.id.desc()).all()
    return render_template('services.html', services=all_services)
  

@app.route('/services/edit/<int:id>', methods=['POST'])
def edit_service(id):
    try:
        service = Service.query.get_or_404(id)
        new_name = request.form.get('service_name')
        if new_name:
            service.service_name = new_name
            db.session.commit()
            flash("Service updated successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating service: {str(e)}", "danger")
    return redirect(url_for('manage_services'))

@app.route('/delete_service/<int:id>', methods=['POST'])
def delete_service(id):
    service = Service.query.get_or_404(id)
    try:
        db.session.delete(service)
        db.session.commit()
        # This line is what sends the user back to the main list
        return redirect(url_for('manage_services')) 
    except Exception as e:
        db.session.rollback()
        # Handle error
        return redirect(url_for('manage_services'))


# ==========================================
# 6. PROJECT MANAGEMENT ROUTES
# ==========================================
# ==========================================
# PROJECT ROUTE
# ==========================================
@app.route('/projects/create', methods=['GET', 'POST'])
def create_project():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # 1. Capture Form Data
        customer_id = request.form.get('customer_id')
        project_name = request.form.get('project_name')
        po_number = request.form.get('po_number')
        service_type = request.form.get('service_type')
        description = request.form.get('description')
        total_value = float(request.form.get('total_value', 0))
        currency = request.form.get('currency', 'INR')
        payment_type = request.form.get('payment_type')
        status = request.form.get('status', 'Active')
        start_date = request.form.get('start_date') or None

        # 2. Build Service Breakdown JSON
        selected_names = request.form.getlist('service_names[]')
        selected_costs = request.form.getlist('service_costs[]')
        
        breakdown_data = {name: float(cost) for name, cost in zip(selected_names, selected_costs) if cost and float(cost) > 0}
        service_breakdown_json = json.dumps(breakdown_data)

        # 3. Insert Project and Get New ID
        cursor.execute("""
            INSERT INTO projects 
            (customer_id, project_name, po_number, service_type, description, 
             start_date, total_value, currency, payment_type, status, service_breakdown) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (customer_id, project_name, po_number, service_type, description, 
              start_date, total_value, currency, payment_type, status, service_breakdown_json))
        
        new_project_id = cursor.lastrowid

        # 4. Handle Payment Slabs
        if payment_type == 'Milestone-based':
            names = request.form.getlist('slab_names[]')
            percents = request.form.getlist('slab_percentages[]')
            conditions = request.form.getlist('due_conditions[]') or request.form.getlist('due_condition[]')
            
            for i in range(len(names)):
                if names[i].strip():
                    p_val = float(percents[i]) if (i < len(percents) and percents[i]) else 0
                    slab_amt = (p_val / 100) * total_value
                    current_cond = conditions[i] if i < len(conditions) else ""
                    
                    cursor.execute("""
                        INSERT INTO payment_slabs (project_id, slab_name, percentage, amount, due_condition) 
                        VALUES (%s, %s, %s, %s, %s)
                    """, (new_project_id, names[i], p_val, slab_amt, current_cond))
        else:
            # Single "Full Payment" entry for standard projects
            cursor.execute("""
                INSERT INTO payment_slabs (project_id, slab_name, percentage, amount, due_condition) 
                VALUES (%s, %s, %s, %s, %s)
            """, (new_project_id, 'Full Payment', 100, total_value, 'Immediate'))

        conn.commit()
        conn.close()
        return redirect(url_for('list_projects'))

    # GET Logic (Fetching dropdown data)
    cursor.execute("SELECT id, company_name FROM customers ORDER BY company_name")
    customers = cursor.fetchall()
    cursor.execute("SELECT service_name FROM services ORDER BY service_name")
    services = cursor.fetchall()
    conn.close()

    return render_template('project_form.html', customers=customers, services=services)

@app.route('/projects/view/<int:id>')
def view_project(id):
    project = Project.query.get_or_404(id)
    return render_template('project_view.html', project=project)


@app.route('/projects/<int:id>/edit', methods=['GET', 'POST'])
def edit_project(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # 1. Capture standard fields
        customer_id = request.form.get('customer_id')
        project_name = request.form.get('project_name')
        po_number = request.form.get('po_number')
        service_type = request.form.get('service_type')
        description = request.form.get('description')
        total_value = float(request.form.get('total_value', 0))
        currency = request.form.get('currency', 'INR')
        payment_type = request.form.get('payment_type')
        status = request.form.get('status', 'Active')
        
        # --- NEW: Build Service Breakdown JSON ---
        selected_names = request.form.getlist('service_names[]')
        selected_costs = request.form.getlist('service_costs[]')
        
        breakdown_data = {}
        for name, cost in zip(selected_names, selected_costs):
            if cost and float(cost) > 0:
                breakdown_data[name] = float(cost)
        
        service_breakdown_json = json.dumps(breakdown_data)
        # ------------------------------------------

        start_date = request.form.get('start_date')
        if not start_date or start_date.strip() == '': 
            start_date = None

        # 2. UPDATED QUERY: Added service_breakdown=%s
        cursor.execute("""
            UPDATE projects 
            SET customer_id=%s, project_name=%s, po_number=%s, service_type=%s, 
                description=%s, start_date=%s, total_value=%s, currency=%s, 
                payment_type=%s, status=%s, service_breakdown=%s 
            WHERE id=%s
        """, (customer_id, project_name, po_number, service_type, description, 
              start_date, total_value, currency, payment_type, status, 
              service_breakdown_json, id))

        # 3. Handle Payment Slabs
        cursor.execute("DELETE FROM payment_slabs WHERE project_id = %s", (id,))
        
        # 3. Handle Payment Slabs
        cursor.execute("DELETE FROM payment_slabs WHERE project_id = %s", (id,))
        
        if payment_type == 'Milestone-based':
            names = request.form.getlist('slab_names[]')
            percents = request.form.getlist('slab_percentages[]')
            # Check both singular and plural names to be safe
            conditions = request.form.getlist('due_conditions[]') or request.form.getlist('due_condition[]')
            
            for i in range(len(names)):
                # Only save if the milestone has a name
                if names[i].strip():
                    # 1. Safe Percent & Amount
                    p_val = float(percents[i]) if (i < len(percents) and percents[i]) else 0
                    slab_amt = (p_val / 100) * total_value
                    
                    # 2. Safe Condition fetch
                    current_condition = conditions[i] if i < len(conditions) else ""
                    
                    cursor.execute("""
                        INSERT INTO payment_slabs (project_id, slab_name, percentage, amount, due_condition) 
                        VALUES (%s, %s, %s, %s, %s)
                    """, (id, names[i], p_val, slab_amt, current_condition))
        else:
            # If not Milestone-based, save one single full payment row
            cursor.execute("""
                INSERT INTO payment_slabs (project_id, slab_name, percentage, amount, due_condition) 
                VALUES (%s, %s, %s, %s, %s)
            """, (id, 'Full Payment', 100, total_value, 'Immediate'))

        conn.commit()
        conn.close()
        return redirect(url_for('list_projects'))

    # --- GET LOGIC ---
    cursor.execute("SELECT * FROM projects WHERE id = %s", (id,))
    project = cursor.fetchone() 
    
    # --- NEW: Parse Service Breakdown for Frontend ---
    breakdown_dict = {}
    if project:
        if project.get('start_date'):
            project['start_date'] = str(project['start_date'])
        
        # Parse the JSON string from the DB into a Python dictionary
        if project.get('service_breakdown'):
            try:
                breakdown_dict = json.loads(project['service_breakdown'])
            except:
                breakdown_dict = {}

        cursor.execute("SELECT * FROM payment_slabs WHERE project_id = %s", (id,))
        slabs = cursor.fetchall()
    else:
        slabs = []

    cursor.execute("SELECT id, company_name, currency FROM customers ORDER BY company_name")
    customers = cursor.fetchall()

    cursor.execute("SELECT service_name FROM services ORDER BY service_name")
    services = cursor.fetchall()
    
    conn.close()
    
    # Pass breakdown_dict to the template
    return render_template('project_form.html', 
                           project=project, 
                           slabs=slabs, 
                           customers=customers, 
                           services=services, 
                           breakdown_dict=breakdown_dict)


@app.route('/projects')
def list_projects():
    # Fetch filter arguments from URL
    search_term = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    service_filter = request.args.get('service_type', '')

    # Use SQLAlchemy (Project model) to fetch projects
    query = Project.query.join(Customer)

    # Apply Filters
    if search_term:
        query = query.filter(
            (Project.project_name.ilike(f'%{search_term}%')) | 
            (Customer.company_name.ilike(f'%{search_term}%')) |
            (Project.po_number.ilike(f'%{search_term}%'))
        )
    if status_filter:
        query = query.filter(Project.status == status_filter)
    if service_filter:
        query = query.filter(Project.service_type == service_filter)

    projects = query.order_by(Project.id.desc()).all()

    return render_template('project_list.html', 
                           projects=projects, 
                           search_term=search_term,
                           status_filter=status_filter,
                           service_filter=service_filter)



@app.route('/project/create', methods=['POST'])
@app.route('/project/edit/<int:id>', methods=['POST'])
def save_project(id=None):
    # 1. Get the list of names and all cost inputs
    # Note: We'll update the HTML to give costs a specific name
    selected_names = request.form.getlist('service_names[]')
    selected_costs = request.form.getlist('service_costs[]')

    # 2. Create a dictionary: {"Web VAPT": 1000, "Mobile VAPT": 800}
    breakdown_data = {}
    for name, cost in zip(selected_names, selected_costs):
        if cost and float(cost) > 0:
            breakdown_data[name] = float(cost)

    # 3. Save to Project
    if id:
        project = Project.query.get(id)
    else:
        project = Project()

    project.project_name = request.form.get('project_name')
    project.total_value = request.form.get('total_value')
    project.service_type = ", ".join(breakdown_data.keys())
    project.service_breakdown = json.dumps(breakdown_data) # SAVE AS JSON STRING

    # ... save slabs and commit ...
    db.session.add(project)
    db.session.commit()
    return redirect(url_for('list_projects'))




# ==========================================
# UPDATED API
# ==========================================
from flask import jsonify

@app.route('/get_customer_details/<int:id>')
def get_customer_details(id):
    # Fetch the customer from your database using the ID
    customer = Customer.query.get(id) 
    
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404

    # The keys here MUST match the JavaScript "data.key" names
    return jsonify({
        'currency': customer.currency,     # e.g., 'USD' or 'INR'
        'gst_number': customer.gst_number,     # Ensure field name matches your model
        'gst_type': customer.gst_type,     # e.g., 'Regular', 'Composition'
        'gst_status': customer.gst_status, # e.g., 'Registered', 'No_Forex'
        'city': customer.city,
        'state': customer.state,
        'country': customer.country
    })



if __name__ == '__main__':
    app.run(debug=True, port=8000)