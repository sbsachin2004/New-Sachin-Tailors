from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from pymongo import MongoClient
from datetime import datetime
import uuid
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
import logging

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB Atlas connection
client = MongoClient('mongodb+srv://tailor_admin:Nihcas2004@tailoringcluster.scrl7r9.mongodb.net/?retryWrites=true&w=majority&appName=TailoringCluster')
db = client['sachin_tailors']
users_collection = db['users']
customers_collection = db['customers']
orders_collection = db['orders']

# Helper functions
def generate_bill_no():
    return str(uuid.uuid4())[:8].upper()

def get_user(username):
    try:
        user = users_collection.find_one({'username': str(username).strip()})
        logger.debug(f"User found for '{username}': {user}")
        return user
    except Exception as e:
        logger.error(f"Error fetching user '{username}': {str(e)}")
        return None

def get_customer(mobile):
    try:
        customer = customers_collection.find_one({'mobile': str(mobile).strip()})
        logger.debug(f"Customer found for mobile '{mobile}': {customer}")
        return customer
    except Exception as e:
        logger.error(f"Error fetching customer '{mobile}': {str(e)}")
        return None

def generate_pdf_invoice(order):
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        elements = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            name='TitleStyle',
            fontName='Helvetica-Bold',
            fontSize=20,
            textColor=colors.HexColor('#1A2A44'),  # Navy blue
            spaceAfter=12
        )
        subtitle_style = ParagraphStyle(
            name='SubtitleStyle',
            fontName='Helvetica',
            fontSize=12,
            textColor=colors.HexColor('#333333'),
            spaceAfter=8
        )
        normal_style = ParagraphStyle(
            name='NormalStyle',
            fontName='Times-Roman',
            fontSize=11,
            textColor=colors.HexColor('#333333'),
            spaceAfter=6
        )

        # Header
        elements.append(Paragraph("Sachin Tailors", title_style))
        elements.append(Paragraph("Premium Tailoring Services", subtitle_style))
        elements.append(Spacer(1, 0.2*inch))

        # Invoice Details
        details_data = [
            ["Invoice Details", ""],
            ["Bill No:", order['bill_no']],
            ["Customer Mobile:", order['mobile']],
            ["Invoice Date:", datetime.now().strftime('%Y-%m-%d')],
            ["Created Date:", order['created_date']],
        ]
        details_table = Table(details_data, colWidths=[2*inch, 4*inch])
        details_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1A2A44')),  # Navy blue header
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 12),
            ('FONT', (0, 1), (-1, -1), 'Times-Roman', 11),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#D4A017')),  # Gold border
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.gray),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(details_table)
        elements.append(Spacer(1, 0.3*inch))

        # Order Details
        order_data = [
            ["Description", "Measurements", "Total Amount", "Advance", "Due Amount", "Delivery Date"],
            [order['description'], order['measurements'], f"${order['total_amount']:.2f}", 
             f"${order['advance']:.2f}", f"${order['due_amount']:.2f}", order['delivery_date']],
        ]
        order_table = Table(order_data, colWidths=[1.5*inch, 1.5*inch, 1*inch, 1*inch, 1*inch, 1*inch])
        order_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1A2A44')),  # Navy blue header
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 12),
            ('FONT', (0, 1), (-1, -1), 'Times-Roman', 11),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#F4F6F8')),  # Light gray row
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#D4A017')),  # Gold border
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.gray),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),  # Right-align amounts
        ]))
        elements.append(Paragraph("Order Details", subtitle_style))
        elements.append(order_table)
        elements.append(Spacer(1, 0.3*inch))

        # Footer
        elements.append(Paragraph("Thank you for choosing Sachin Tailors!", normal_style))
        elements.append(Paragraph("Contact: +91 8122288855 | Email: info@sachintailors.com", normal_style))

        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        logger.debug(f"PDF generated successfully for bill_no: {order['bill_no']}")
        return buffer
    except Exception as e:
        logger.error(f"Error generating PDF for bill_no {order['bill_no']}: {str(e)}")
        raise

@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        logger.debug(f"Login attempt - Username: '{username}', Password: '{password}'")
        user = get_user(username)
        if user is not None and user['password'] == password:
            session['username'] = username
            session['role'] = user['role']
            logger.debug(f"Login successful for {username}, role: {user['role']}")
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('customer_dashboard'))
        else:
            logger.debug("Invalid credentials")
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        role = request.form['role'].strip()
        logger.debug(f"Signup attempt - Username: '{username}', Password: '{password}', Role: '{role}'")
        if users_collection.find_one({'username': username}):
            flash('Username already exists')
            logger.debug("Username already exists")
        else:
            users_collection.insert_one({'username': username, 'password': password, 'role': role})
            logger.debug(f"User {username} saved to MongoDB")
            flash('Signup successful! Please login.')
            return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'username' not in session or session['role'] != 'admin':
        logger.debug("Unauthorized access to admin dashboard, redirecting to login")
        return redirect(url_for('login'))
    
    # Initialize orders and customers lists
    orders = list(orders_collection.find())
    customers = list(customers_collection.find())
    
    # Handle order search by bill number
    if request.method == 'POST' and 'bill_no' in request.form:
        bill_no = request.form['bill_no'].strip()
        logger.debug(f"Searching for order with bill_no: {bill_no}")
        if bill_no:
            try:
                # Use regex for case-insensitive partial match
                orders = list(orders_collection.find({'bill_no': {'$regex': bill_no, '$options': 'i'}}))
                if not orders:
                    flash(f"No orders found with bill number containing: {bill_no}")
                else:
                    flash(f"Found {len(orders)} order(s) matching: {bill_no}")
            except Exception as e:
                logger.error(f"Error searching orders with bill_no {bill_no}: {str(e)}")
                flash(f"Error searching orders: {str(e)}")
        else:
            flash("Please enter a bill number to search")
    
    return render_template('admin_dashboard.html', customers=customers, orders=orders)

@app.route('/add_customer', methods=['POST'])
def add_customer():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    mobile = request.form['mobile'].strip()
    customer_code = request.form['customer_code'].strip()
    measurements = request.form['measurements'].strip()
    if customers_collection.find_one({'mobile': mobile}):
        flash('Customer with this mobile number already exists')
    else:
        customers_collection.insert_one({'mobile': mobile, 'customer_code': customer_code, 'measurements': measurements})
        flash('Customer added successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/edit_customer/<mobile>', methods=['GET', 'POST'])
def edit_customer(mobile):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    customer = customers_collection.find_one({'mobile': mobile})
    if not customer:
        flash('Customer not found')
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        customer_code = request.form['customer_code'].strip()
        measurements = request.form['measurements'].strip()
        customers_collection.update_one(
            {'mobile': mobile},
            {'$set': {'customer_code': customer_code, 'measurements': measurements}}
        )
        flash('Customer updated successfully')
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_customer.html', customer=customer)

@app.route('/delete_customer/<mobile>', methods=['POST'])
def delete_customer(mobile):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    customers_collection.delete_one({'mobile': mobile})
    orders_collection.delete_many({'mobile': mobile})
    flash('Customer and their orders deleted successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/create_order', methods=['POST'])
def create_order():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    mobile = request.form['mobile'].strip()
    description = request.form['description'].strip()
    total_amount = float(request.form['total_amount'])
    advance = float(request.form['advance'])
    due_amount = total_amount - advance
    delivery_date = request.form['delivery_date'].strip()
    status = request.form['status'].strip()
    created_date = datetime.now().strftime('%Y-%m-%d')
    bill_no = generate_bill_no()

    customer = get_customer(mobile)
    if customer is None:
        flash('Customer not found. Please add the customer first.')
        return redirect(url_for('admin_dashboard'))
    measurements = customer['measurements']

    orders_collection.insert_one({
        'bill_no': bill_no,
        'mobile': mobile,
        'measurements': measurements,
        'description': description,
        'total_amount': total_amount,
        'advance': advance,
        'due_amount': due_amount,
        'delivery_date': delivery_date,
        'created_date': created_date,
        'status': status
    })
    flash('Order created successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/edit_order/<bill_no>', methods=['GET', 'POST'])
def edit_order(bill_no):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    order = orders_collection.find_one({'bill_no': bill_no})
    if not order:
        flash('Order not found')
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        mobile = request.form['mobile'].strip()
        measurements = request.form['measurements'].strip()
        description = request.form['description'].strip()
        total_amount = float(request.form['total_amount'])
        advance = float(request.form['advance'])
        due_amount = total_amount - advance
        delivery_date = request.form['delivery_date'].strip()
        status = request.form['status'].strip()
        created_date = order['created_date']

        customer = get_customer(mobile)
        if customer is None:
            flash('Customer not found. Please add the customer first.')
            return redirect(url_for('edit_order', bill_no=bill_no))

        orders_collection.update_one(
            {'bill_no': bill_no},
            {'$set': {
                'mobile': mobile,
                'measurements': measurements,
                'description': description,
                'total_amount': total_amount,
                'advance': advance,
                'due_amount': due_amount,
                'delivery_date': delivery_date,
                'created_date': created_date,
                'status': status
            }}
        )
        flash('Order updated successfully')
        return redirect(url_for('admin_dashboard'))
    customer = get_customer(order['mobile'])
    if customer:
        order['measurements'] = customer['measurements'] if not order['measurements'] else order['measurements']
    return render_template('edit_order.html', order=order)

@app.route('/delete_order/<bill_no>', methods=['POST'])
def delete_order(bill_no):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    orders_collection.delete_one({'bill_no': bill_no})
    flash('Order deleted successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/download_invoice/<bill_no>')
def download_invoice(bill_no):
    if 'username' not in session:
        logger.debug("No user session found, redirecting to login")
        flash('Please log in to download the invoice')
        return redirect(url_for('login'))
    try:
        logger.debug(f"Fetching order for bill_no: {bill_no}")
        order = orders_collection.find_one({'bill_no': bill_no})
        logger.debug(f"Order found: {order}")
        if not order:
            logger.debug(f"Order not found for bill_no: {bill_no}")
            flash('Order not found')
            return redirect(url_for('customer_dashboard' if session['role'] == 'customer' else 'admin_dashboard'))
        if session['role'] != 'admin' and order['mobile'] != session['username']:
            logger.debug(f"Unauthorized access attempt by {session['username']} for bill_no: {bill_no}")
            flash('Unauthorized access to invoice')
            return redirect(url_for('customer_dashboard'))
        pdf = generate_pdf_invoice(order)
        logger.debug(f"PDF response prepared for bill_no: {bill_no}")
        return Response(
            pdf.getvalue(),
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment;filename=invoice_{bill_no}.pdf'}
        )
    except Exception as e:
        logger.error(f"Error in download_invoice for bill_no {bill_no}: {str(e)}")
        flash(f'Error generating invoice: {str(e)}')
        return redirect(url_for('customer_dashboard' if session['role'] == 'customer' else 'admin_dashboard'))

@app.route('/analytics', methods=['GET', 'POST'])
def analytics():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    if request.method == 'POST':
        password = request.form['password'].strip()
        user = get_user(session['username'])
        if user is not None and user['password'] == password:
            orders = list(orders_collection.find())
            total_revenue = sum(order['total_amount'] for order in orders)
            status_counts = {}
            for order in orders:
                status = order['status']
                status_counts[status] = status_counts.get(status, 0) + 1
            analytics = {
                'total_orders': len(orders),
                'total_revenue': total_revenue,
                'orders_by_status': status_counts,
                'avg_order_value': total_revenue / len(orders) if orders else 0,
                'total_customers': len(set(order['mobile'] for order in orders))
            }
            return render_template('analytics.html', analytics=analytics)
        else:
            flash('Incorrect analytics password')
    return render_template('analytics_password.html')

@app.route('/customer_dashboard')
def customer_dashboard():
    if 'username' not in session or session['role'] != 'customer':
        return redirect(url_for('login'))
    user = get_user(session['username'])
    customer = get_customer(session['username'])
    customer_code = customer['customer_code'] if customer else session['username']
    customer_orders = list(orders_collection.find({'mobile': user['username']}))
    return render_template('customer_dashboard.html', orders=customer_orders, customer_code=customer_code)

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)