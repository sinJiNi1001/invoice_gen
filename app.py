from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from typing import List, Dict, Any
import os
from datetime import date
from dotenv import load_dotenv

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

if __name__ == '__main__':
    app.run(debug=True, port=8000)