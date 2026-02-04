from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models import db, Customer, Project, Invoice, PaymentSlab
from sqlalchemy.exc import IntegrityError
import datetime
from sqlalchemy import desc, extract
import datetime
import datetime
from sqlalchemy import extract

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Megha%402004@localhost/invoice_generator'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "valency_secret"
db.init_app(app)

@app.route('/')
def dashboard():
    # Automatically redirects the user to the invoice list view on launch
    return redirect(url_for('edit_list'))

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
        new_sequence_str = str(new_num).zfill(3)
        
        return f"{prefix}{new_sequence_str}"
    except (ValueError, IndexError):
        return f"{prefix}001"

@app.route('/invoice/new', methods=['GET', 'POST'])
def create_invoice():
    customers = Customer.query.all()
    projects = Project.query.all()
    # Assuming you might need services for the dropdown
    # services = Service.query.all() 
    suggested_no = get_next_invoice_number()

    if request.method == 'POST':
        # 1. Handle Multiple Projects/Amounts from the table
        # We take the first project selected as the primary project for the list view
        project_ids = request.form.getlist('project_ids[]')
        amounts = request.form.getlist('amounts[]')
        
        primary_project_id = project_ids[0] if project_ids and project_ids[0].strip() else None
        
        # Calculate Subtotal from all rows (before tax)
        # This ensures 'total_amount' is accurate even with multiple rows
        try:
            calculated_subtotal = sum(float(a) if a.strip() else 0 for a in amounts)
        except ValueError:
            calculated_subtotal = 0

        # 2. Handle Milestone logic
        # If milestone is chosen, the "slab" is usually the first milestone being billed
        slab_names = request.form.getlist('slab_names[]')
        # For the registry, we just link it to the first project for now
        
        try:
            new_inv = Invoice(
                invoice_number=request.form.get('invoice_number'),
                customer_id=request.form.get('customer_id'),
                project_id=primary_project_id, 
                # We store the total calculated by your JavaScript 'syncPreview'
                total_amount=float(request.form.get('total_amount', 0)),
                tax_amount=float(request.form.get('tax_amount', 0)),
                invoice_date=request.form.get('invoice_date'),
                tax_type=request.form.get('tax_type'),
                status='Raised',
                amount_received=0.0,
                # Optional: store the billing type if you added it to models
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

    # Important: If your HTML uses 'services', you must pass it here
    # services = Service.query.all()
    return render_template('invoice_create.html', 
                           customers=customers, 
                           projects=projects, 
                           # services=services, # Uncomment if you have a Service model
                           suggested_no=suggested_no)

@app.route('/get_slabs/<int:project_id>')
def get_slabs(project_id):
    slabs = PaymentSlab.query.filter_by(project_id=project_id).all()
    return jsonify([{'id': s.id, 'name': s.slab_name, 'amount': float(s.amount)} for s in slabs])

# --- UPDATED SECTION: EDIT LIST WITH ALL, NEW, AND CURRENT MONTH TABS ---
# --- UPDATED SECTION: CORRECTED VARIABLE NAMES ---
@app.route('/invoice/edit')
def edit_list():
    page = request.args.get('page', 1, type=int)
    now = datetime.datetime.now()
    
    # 1. Calculate target month for current page
    current_total_months = now.year * 12 + (now.month - 1)
    target_total_months = current_total_months - (page - 1)
    t_year = target_total_months // 12
    t_month = (target_total_months % 12) + 1
    
    display_label = datetime.date(t_year, t_month, 1).strftime('%B %Y')

    # 2. Calculate Total Pages (Months) based on oldest invoice
    oldest_invoice = Invoice.query.order_by(Invoice.invoice_date.asc()).first()
    if oldest_invoice:
        oldest_date = oldest_invoice.invoice_date
        oldest_total_months = oldest_date.year * 12 + (oldest_date.month - 1)
        total_pages = (current_total_months - oldest_total_months) + 1
    else:
        total_pages = 1

    # 3. Handle Filters
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

    # New & Edit Tabs (Current Month)
    current_month_query = Invoice.query.filter(
        extract('month', Invoice.invoice_date) == now.month,
        extract('year', Invoice.invoice_date) == now.year
    ).order_by(Invoice.invoice_date.desc())

    return render_template('invoice_list.html', 
                           all_invoices=all_invoices, 
                           new_invoices=current_month_query.limit(10).all(), 
                           edit_invoices=current_month_query.all(),
                           now=now,
                           page=page,
                           total_pages=total_pages,
                           display_label=display_label,
                           current_filters={'day': f_day, 'month': f_month, 'year': f_year})


@app.route('/invoice/edit/<int:id>', methods=['GET', 'POST'])
def edit_form(id):
    invoice = Invoice.query.get_or_404(id)
    customers = Customer.query.all()
    projects = Project.query.all()
    
    current_project_slabs = []
    if invoice.project_id:
        current_project_slabs = PaymentSlab.query.filter_by(project_id=invoice.project_id).all()

    if request.method == 'POST':
        try:
            raw_slab = request.form.get('slab_id')
            invoice.slab_id = int(raw_slab) if raw_slab and raw_slab.strip() else None
            
            invoice.invoice_number = request.form.get('invoice_number')
            invoice.customer_id = request.form.get('customer_id')
            invoice.project_id = request.form.get('project_id')
            invoice.invoice_date = request.form.get('invoice_date')
            invoice.due_date = request.form.get('due_date') or None
            invoice.status = request.form.get('status')
            invoice.tax_type = request.form.get('tax_type')
            invoice.tax_amount = float(request.form.get('tax_amount', 0))
            invoice.total_amount = float(request.form.get('total_amount', 0))
            invoice.billing_type = request.form.get('billing_type')
            invoice.amount_received = float(request.form.get('amount_received') or 0)
        
            date_val = request.form.get('received_date')
            invoice.received_date = datetime.datetime.strptime(date_val, '%Y-%m-%d').date() if date_val else None

            db.session.commit()
            flash("Invoice updated successfully!", "success")
            return redirect(url_for('edit_list'))
        except Exception as e:
            db.session.rollback()
            flash(f"Update Error: {str(e)}", "danger")
    
    return render_template('invoice_edit.html', 
                           invoice=invoice, 
                           customers=customers, 
                           projects=projects, 
                           slabs=current_project_slabs)

if __name__ == '__main__':
    app.run(debug=True)