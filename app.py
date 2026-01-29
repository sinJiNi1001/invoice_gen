from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from typing import List, Dict, Any

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

# --- HELPER ---
def fetch_as_dict(cursor: Any) -> List[Dict[str, Any]]:
    rows = cursor.fetchall()
    return [dict(row) for row in rows]

# --- ROUTES ---

@app.route('/')
def dashboard():
    return redirect(url_for('list_customers'))

# 1. VIEW CUSTOMERS (FIXED ID MATCHING)
# 1. VIEW CUSTOMERS (WITH SORTING)
@app.route('/customers')
def list_customers():
    search = request.args.get('search', '')
    country = request.args.get('country', '')
    sort_by = request.args.get('sort_by', 'newest')  # Default to 'newest'
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Base Query
    query = "SELECT * FROM customers WHERE 1=1"
    params = []
    
    # Filters
    if search:
        query += " AND company_name LIKE %s"
        params.append(f"%{search}%")
    if country:
        query += " AND country = %s"
        params.append(country)
    
    # Sorting Logic
    if sort_by == 'name_asc':
        query += " ORDER BY company_name ASC"
    elif sort_by == 'name_desc':
        query += " ORDER BY company_name DESC"
    elif sort_by == 'oldest':
        query += " ORDER BY id ASC"
    else:
        # Default: Newest First
        query += " ORDER BY id DESC"
    
    cursor.execute(query, tuple(params))
    customers = fetch_as_dict(cursor)

    # Attach Projects (Same logic as before)
    if customers:
        for c in customers: c['projects'] = [] # Safety init
        
        cust_ids = [str(c['id']) for c in customers]
        if cust_ids:
            placeholders = ','.join(['%s'] * len(cust_ids))
            sql = f"SELECT * FROM projects WHERE customer_id IN ({placeholders})"
            cursor.execute(sql, tuple(cust_ids))
            all_projects = fetch_as_dict(cursor)

            for cust in customers:
                cust['projects'] = [p for p in all_projects if str(p['customer_id']) == str(cust['id'])]
    
    conn.close()
    
    return render_template('customer_list.html', 
                           customers=customers, 
                           search_term=search, 
                           country_filter=country,
                           sort_by=sort_by,   # Pass this to template
                           active_page='customers')

# 2. CREATE CUSTOMER
@app.route('/customers/new', methods=('GET', 'POST'))
def create_customer():
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert Customer
        cursor.execute("""
            INSERT INTO customers (company_name, country, currency, email, phone, address, tax_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (request.form['company_name'], request.form['country'], request.form['currency'], 
              request.form.get('email'), request.form.get('phone'), request.form.get('address'), request.form.get('tax_id')))
        
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
    
    return render_template('customer_form.html', customer=None, projects=[], active_page='customers')

# 3. EDIT CUSTOMER
@app.route('/customers/<int:id>/edit', methods=('GET', 'POST'))
def edit_customer(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        cursor.execute("""
            UPDATE customers SET company_name=%s, country=%s, currency=%s, email=%s, phone=%s, address=%s, tax_id=%s
            WHERE id=%s
        """, (request.form['company_name'], request.form['country'], request.form['currency'], 
              request.form.get('email'), request.form.get('phone'), request.form.get('address'), request.form.get('tax_id'), id))
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
    return render_template('customer_form.html', customer=customer, projects=projects, active_page='customers')

# 4. ADD SINGLE PROJECT (Edit Mode)
@app.route('/customers/<int:id>/project/add', methods=['POST'])
def add_project_to_customer(id):
    project_name = request.form['project_name']
    total_value = request.form['total_value']
    status = request.form['status']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO projects (customer_id, project_name, total_value, status)
        VALUES (%s, %s, %s, %s)
    """, (id, project_name, total_value, status))
    conn.commit()
    conn.close()
    return redirect(url_for('edit_customer', id=id))

# 5. UPDATE PROJECT
@app.route('/projects/<int:proj_id>/update', methods=['POST'])
def update_project(proj_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cust_id = request.form['customer_id'] # Needed for redirect
    
    cursor.execute("""
        UPDATE projects SET project_name=%s, total_value=%s, status=%s
        WHERE id=%s
    """, (request.form['project_name'], request.form['total_value'], request.form['status'], proj_id))
    
    conn.commit()
    conn.close()
    return redirect(url_for('edit_customer', id=cust_id))

# 6. DELETE PROJECT
@app.route('/customers/<int:cust_id>/project/<int:proj_id>/delete')
def delete_project(cust_id, proj_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM projects WHERE id = %s", (proj_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('edit_customer', id=cust_id))

# Placeholders
@app.route('/invoice/create')
def create_invoice(): return "Invoice Create Page"
@app.route('/invoice/edit')
def edit_list(): return "Invoice Edit Page"

if __name__ == '__main__':
    app.run(debug=True, port=8000)