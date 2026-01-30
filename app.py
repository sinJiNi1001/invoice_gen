from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from typing import List, Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

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
    elif sort_by == 'oldest': query += " ORDER BY id ASC"
    else: query += " ORDER BY id DESC"
    
    cursor.execute(query, tuple(params))
    customers = fetch_as_dict(cursor)

    # Attach Projects
    if customers:
        for c in customers: c['projects'] = []
        cust_ids = [str(c['id']) for c in customers]
        if cust_ids:
            placeholders = ','.join(['%s'] * len(cust_ids))
            sql = f"SELECT * FROM projects WHERE customer_id IN ({placeholders})"
            cursor.execute(sql, tuple(cust_ids))
            all_projects = fetch_as_dict(cursor)

            for cust in customers:
                cust['projects'] = [p for p in all_projects if str(p['customer_id']) == str(cust['id'])]
    
    conn.close()
    return render_template('customer_list.html', customers=customers, search_term=search, country_filter=country, sort_by=sort_by)

@app.route('/customers/new', methods=('GET', 'POST'))
def create_customer():
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # FIXED: Uses gst_number instead of tax_id
        # FIXED: Includes deal_owner and gst_type
        cursor.execute("""
            INSERT INTO customers (company_name, deal_owner, gst_type, gst_number, country, currency, email, phone, address)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            request.form['company_name'], 
            request.form.get('deal_owner'), 
            request.form.get('gst_type', 'Yes'), 
            request.form.get('gst_number'),
            request.form['country'], 
            request.form['currency'], 
            request.form.get('email'), 
            request.form.get('phone'), 
            request.form.get('address')
        ))
        
        new_cust_id = cursor.lastrowid

        # Insert Projects
        proj_names = request.form.getlist('new_project_names[]')
        proj_values = request.form.getlist('new_project_values[]')
        proj_statuses = request.form.getlist('new_project_statuses[]')

        for name, val, status in zip(proj_names, proj_values, proj_statuses):
            if name.strip():
                cursor.execute("""
                    INSERT INTO projects (customer_id, project_name, total_value, status)
                    VALUES (%s, %s, %s, %s)
                """, (new_cust_id, name, val, status))

        conn.commit()
        conn.close()
        return redirect(url_for('list_customers'))
    
    return render_template('customer_form.html', customer=None, projects=[])

@app.route('/customers/<int:id>/edit', methods=('GET', 'POST'))
def edit_customer(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        # FIXED: Updates gst_number, deal_owner, and gst_type
        cursor.execute("""
            UPDATE customers 
            SET company_name=%s, deal_owner=%s, gst_type=%s, gst_number=%s, country=%s, currency=%s, email=%s, phone=%s, address=%s
            WHERE id=%s
        """, (
            request.form['company_name'], 
            request.form.get('deal_owner'), 
            request.form.get('gst_type'), 
            request.form.get('gst_number'),
            request.form['country'], 
            request.form['currency'], 
            request.form.get('email'), 
            request.form.get('phone'), 
            request.form.get('address'), 
            id
        ))
        conn.commit()
        conn.close()
        return redirect(url_for('list_customers'))

    cursor.execute("SELECT * FROM customers WHERE id = %s", (id,))
    rows = fetch_as_dict(cursor)
    customer = rows[0] if rows else None
    
    projects = []
    if customer:
        cursor.execute("SELECT * FROM projects WHERE customer_id = %s ORDER BY id DESC", (id,))
        projects = fetch_as_dict(cursor)

    conn.close()
    return render_template('customer_form.html', customer=customer, projects=projects)

# ==========================================
# PROJECT ROUTES
# ==========================================

@app.route('/customers/<int:id>/project/add', methods=['POST'])
def add_project_to_customer(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO projects (customer_id, project_name, total_value, status)
        VALUES (%s, %s, %s, %s)
    """, (id, request.form['project_name'], request.form['total_value'], request.form['status']))
    conn.commit()
    conn.close()
    return redirect(url_for('edit_customer', id=id))

@app.route('/projects/<int:proj_id>/update', methods=['POST'])
def update_project(proj_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cust_id = request.form['customer_id']
    cursor.execute("""
        UPDATE projects SET project_name=%s, total_value=%s, status=%s
        WHERE id=%s
    """, (request.form['project_name'], request.form['total_value'], request.form['status'], proj_id))
    conn.commit()
    conn.close()
    return redirect(url_for('edit_customer', id=cust_id))

# ==========================================
# INVOICE ROUTES (Placeholders to prevent crashing)
# ==========================================

@app.route('/invoices')
def list_invoices():
    return "<h1>Invoices Page</h1><p>Coming next...</p>"

@app.route('/invoices/new')
def create_invoice():
    return "<h1>Create Invoice</h1><p>Coming next...</p>"

@app.route('/invoices/edit')
def edit_list():
    return "<h1>Edit Invoice</h1><p>Coming next...</p>"

# ==========================================
# RUN APP
# ==========================================

if __name__ == '__main__':
    app.run(debug=True, port=8000)