from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from typing import List, Dict, Any
import os
from datetime import date
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from database import db, Customer, Invoice # Removed Project


load_dotenv()

app = Flask(__name__)

app.secret_key = "valency_secret" 

# SQLALCHEMY CONFIG (For the Invoice Tool)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Sinu%40123@localhost/invoice_generator'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


# --- DATABASE CONFIG ---
db_config = {
    'user': 'root',
    'password': 'Sinu@123', 
    'host': 'localhost',
    'database': 'invoice_generator'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

def fetch_as_dict(cursor: Any) -> List[Dict[str, Any]]:
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

# --- ROOT ---
@app.route('/')
def dashboard():
    return redirect(url_for('list_customers'))

# ==========================================
# CUSTOMER ROUTES
# ==========================================

@app.route('/customers')
def list_customers():
    # Get Filter Parameters
    search = request.args.get('search', '')
    country = request.args.get('country', '')
    sort_by = request.args.get('sort_by', 'newest')
    filter_month = request.args.get('month', '')
    filter_year = request.args.get('year', '')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Base Query
    query = "SELECT * FROM customers WHERE 1=1"
    params = []
    
    # Apply Filters
    if search:
        query += " AND company_name LIKE %s"
        params.append(f"%{search}%")
    if country:
        query += " AND country = %s"
        params.append(country)
    
    if filter_month:
        query += " AND MONTH(joined_date) = %s"
        params.append(filter_month)
    if filter_year:
        query += " AND YEAR(joined_date) = %s"
        params.append(filter_year)
    
    # Apply Sorting
    if sort_by == 'name_asc': query += " ORDER BY company_name ASC"
    elif sort_by == 'oldest': query += " ORDER BY joined_date ASC"
    else: query += " ORDER BY joined_date DESC"
    
    cursor.execute(query, tuple(params))
    customers = fetch_as_dict(cursor)
    
    conn.close()
    
    return render_template('customer_list.html', 
                           customers=customers, 
                           search_term=search, 
                           country_filter=country, 
                           sort_by=sort_by,
                           filter_month=filter_month,
                           filter_year=filter_year)

@app.route('/customers/new', methods=('GET', 'POST'))
def create_customer():
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        
        j_date = request.form.get('joined_date')
        if not j_date or j_date.strip() == '':
            j_date = date.today()

        # Logic: If status is NOT Registered, force gst_type to NULL
        status = request.form.get('gst_status', 'Registered')
        tax_type = request.form.get('gst_type') if status == 'Registered' else None

        # REMOVED: po_ref
        cursor.execute("""
            INSERT INTO customers (
                company_name, first_name, last_name, 
                email, phone, address, city, state, country, 
                deal_owner, gst_status, gst_type, gst_number, currency, 
                joined_date, notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            request.form['company_name'], 
            request.form.get('first_name'),
            request.form.get('last_name'),
            request.form.get('email'), 
            request.form.get('phone'), 
            request.form.get('address'),
            request.form.get('city'),
            request.form.get('state'),
            request.form['country'], 
            request.form.get('deal_owner'), 
            status,
            tax_type,
            request.form.get('gst_number'),
            request.form['currency'], 
            j_date,
            request.form.get('notes')
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

        # Logic: If status is NOT Registered, force gst_type to NULL
        status = request.form.get('gst_status', 'Registered')
        tax_type = request.form.get('gst_type') if status == 'Registered' else None

        # REMOVED: po_ref
        cursor.execute("""
            UPDATE customers 
            SET company_name=%s, first_name=%s, last_name=%s, 
                email=%s, phone=%s, address=%s, city=%s, state=%s, country=%s,
                deal_owner=%s, gst_status=%s, gst_type=%s, gst_number=%s, currency=%s, 
                joined_date=%s, notes=%s
            WHERE id=%s
        """, (
            request.form['company_name'], 
            request.form.get('first_name'),
            request.form.get('last_name'),
            request.form.get('email'), 
            request.form.get('phone'), 
            request.form.get('address'),
            request.form.get('city'),
            request.form.get('state'),
            request.form['country'], 
            request.form.get('deal_owner'), 
            status,
            tax_type,
            request.form.get('gst_number'),
            request.form['currency'], 
            j_date,
            request.form.get('notes'),
            id
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
# PLACEHOLDER ROUTES (For Sidebar Links)
# ==========================================
@app.route('/invoices')
def list_invoices(): return "<h1>Invoices Page</h1><p>Coming next...</p>"
@app.route('/invoices/new')
def create_invoice(): return "<h1>Create Invoice</h1><p>Coming next...</p>"
@app.route('/invoices/edit')
def edit_list(): return "<h1>Edit Invoice</h1><p>Coming next...</p>"

# ==========================================
# CONTRACT ROUTES
# ==========================================

@app.route('/contracts')
def list_contracts():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Fetch Contracts
    cursor.execute("""
        SELECT contracts.*, customers.company_name, customers.currency 
        FROM contracts 
        JOIN customers ON contracts.customer_id = customers.id
        ORDER BY contracts.created_at DESC
    """)
    contracts = fetch_as_dict(cursor)
    
    # 2. Fetch Services linked to contracts (Group_Concat is a quick SQL trick here)
    cursor.execute("""
        SELECT contract_id, GROUP_CONCAT(services.service_name SEPARATOR '||') as service_list
        FROM contract_services
        JOIN services ON contract_services.service_id = services.id
        GROUP BY contract_id
    """)
    service_map = {row['contract_id']: row['service_list'].split('||') for row in fetch_as_dict(cursor)}

    # 3. Fetch Slabs
    cursor.execute("SELECT * FROM contract_slabs ORDER BY due_date ASC")
    all_slabs = fetch_as_dict(cursor)
    conn.close()

    # 4. Attach Data to Contracts
    contracts_map = {c['id']: c for c in contracts}
    for c in contracts:
        c['slabs'] = []
        c['services'] = service_map.get(c['id'], []) # Attach services list
        
    for slab in all_slabs:
        if slab['contract_id'] in contracts_map:
            contracts_map[slab['contract_id']]['slabs'].append(slab)

    return render_template('contract_list.html', contracts=contracts)

@app.route('/contracts/new', methods=('GET', 'POST'))
def create_contract():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # 1. Insert Main Contract
        cursor.execute("""
            INSERT INTO contracts (
                customer_id, contract_name, po_reference, total_value, start_date, end_date, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            request.form['customer_id'],
            request.form['contract_name'],
            request.form['po_reference'],
            request.form['total_value'],
            request.form['start_date'],
            request.form['end_date'],
            'Active'
        ))
        contract_id = cursor.lastrowid
        
        # 2. Insert Selected Services (NEW)
        selected_services = request.form.getlist('service_ids')
        for service_id in selected_services:
            cursor.execute("INSERT INTO contract_services (contract_id, service_id) VALUES (%s, %s)", (contract_id, service_id))

        # 3. Insert Slabs
        slab_names = request.form.getlist('slab_name[]')
        slab_amounts = request.form.getlist('slab_amount[]')
        slab_dates = request.form.getlist('slab_date[]')
        
        for i in range(len(slab_names)):
            if slab_names[i].strip():
                cursor.execute("""
                    INSERT INTO contract_slabs (
                        contract_id, slab_name, amount, due_date, status
                    ) VALUES (%s, %s, %s, %s, 'Pending')
                """, (contract_id, slab_names[i], slab_amounts[i], slab_dates[i]))

        conn.commit()
        conn.close()
        return redirect(url_for('list_contracts'))

    # GET Request
    cursor.execute("SELECT * FROM customers ORDER BY company_name ASC")
    customers = fetch_as_dict(cursor)
    
    # Fetch Services for the Checklist
    cursor.execute("SELECT * FROM services ORDER BY service_name ASC")
    services = fetch_as_dict(cursor)
    
    conn.close()
    return render_template('contract_form.html', customers=customers, services=services, contract=None, slabs=None)

@app.route('/contracts/edit/<int:id>', methods=('GET', 'POST'))
def edit_contract(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # 1. Update Main Contract
        cursor.execute("""
            UPDATE contracts 
            SET customer_id = %s, contract_name = %s, po_reference = %s, total_value = %s, start_date = %s, end_date = %s, status = %s
            WHERE id = %s
        """, (
            request.form['customer_id'],
            request.form['contract_name'],
            request.form['po_reference'],
            request.form['total_value'],
            request.form['start_date'],
            request.form['end_date'],
            request.form['status'],
            id
        ))

        # 2. Update Services (Delete Old -> Insert New)
        cursor.execute("DELETE FROM contract_services WHERE contract_id = %s", (id,))
        selected_services = request.form.getlist('service_ids')
        for service_id in selected_services:
            cursor.execute("INSERT INTO contract_services (contract_id, service_id) VALUES (%s, %s)", (id, service_id))

        # 3. Update Slabs
        cursor.execute("DELETE FROM contract_slabs WHERE contract_id = %s", (id,))
        slab_names = request.form.getlist('slab_name[]')
        slab_amounts = request.form.getlist('slab_amount[]')
        slab_dates = request.form.getlist('slab_date[]')
        slab_statuses = request.form.getlist('slab_status[]')
        
        for i in range(len(slab_names)):
            if slab_names[i].strip():
                current_status = slab_statuses[i] if i < len(slab_statuses) else 'Pending'
                cursor.execute("""
                    INSERT INTO contract_slabs (
                        contract_id, slab_name, amount, due_date, status
                    ) VALUES (%s, %s, %s, %s, %s)
                """, (id, slab_names[i], slab_amounts[i], slab_dates[i], current_status))

        conn.commit()
        conn.close()
        return redirect(url_for('list_contracts'))

    # GET Request
    cursor.execute("SELECT * FROM contracts WHERE id = %s", (id,))
    contract = cursor.fetchone()
    
    cursor.execute("SELECT * FROM contract_slabs WHERE contract_id = %s ORDER BY due_date ASC", (id,))
    slabs = fetch_as_dict(cursor)
    
    cursor.execute("SELECT * FROM customers ORDER BY company_name ASC")
    customers = fetch_as_dict(cursor)
    
    # Fetch All Services
    cursor.execute("SELECT * FROM services ORDER BY service_name ASC")
    all_services = fetch_as_dict(cursor)

    # Fetch Selected Services for this Contract
    cursor.execute("SELECT service_id FROM contract_services WHERE contract_id = %s", (id,))
    selected_rows = cursor.fetchall()
    # Convert list of dicts [{'service_id': 1}, {'service_id': 5}] -> simple list [1, 5]
    current_service_ids = [row['service_id'] for row in selected_rows]

    conn.close()
    return render_template('contract_form.html', contract=contract, slabs=slabs, customers=customers, services=all_services, current_service_ids=current_service_ids)

# --- NEW: Route to change payment status via Dashboard ---
@app.route('/contracts/slab/<int:slab_id>/status/<string:new_status>')
def update_slab_status(slab_id, new_status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE contract_slabs SET status = %s WHERE id = %s", (new_status, slab_id))
    conn.commit()
    conn.close()
    return redirect(url_for('list_contracts'))

if __name__ == '__main__':
    app.run(debug=True, port=8000)