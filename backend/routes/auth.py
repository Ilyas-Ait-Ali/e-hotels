from flask import Blueprint, flash, render_template, request, redirect, url_for, session
from sqlalchemy import text
from datetime import date, datetime
from app import db

bp_auth = Blueprint('auth', __name__)

@bp_auth.route('/')
def home():
    return redirect(url_for('auth.login'))

@bp_auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        full_name_input = request.form['full_name'].strip().lower()
        user_type = request.form['user_type']
        selected_position = request.form.get('position')
        password = request.form.get('password', '').strip()
        input_id = request.form.get('user_id', '').strip()

        if not full_name_input or not password or not input_id or user_type not in ['customer', 'employee']:
            return render_template('login.html', error="All fields are required.")

        try:
            user_id = int(input_id)
        except ValueError:
            return render_template('login.html', error="Invalid ID format.")

        if user_type == 'customer':
            if password != 'customer':
                return render_template('login.html', error="Incorrect password for customer.")

            query = text("SELECT CustomerID, FullName FROM Customer WHERE CustomerID = :id AND LOWER(FullName) = :name")
            result = db.session.execute(query, {'id': user_id, 'name': full_name_input}).fetchone()

            if not result:
                return render_template('login.html', error="Customer not found with that name and ID.")

            session['user_id'] = result[0]
            session['user_type'] = 'customer'
            session['user_name'] = result[1]
            return redirect(url_for('customer.my_bookings'))

        else:  # employee login
            if not selected_position:
                return render_template('login.html', error="Please select a position.")

            expected_pw = {
                'Admin': 'admin',
                'Manager': 'employee',
                'Receptionist': 'employee'
            }.get(selected_position)

            if password != expected_pw:
                return render_template('login.html', error=f"Incorrect password for {selected_position}.")

            query = text("""
                SELECT EmployeeID, Position, HotelID, FullName
                FROM Employee
                WHERE EmployeeID = :id AND LOWER(FullName) = :name
            """)
            result = db.session.execute(query, {'id': user_id, 'name': full_name_input}).fetchone()

            if not result:
                return render_template('login.html', error="Employee not found with that name and ID.")

            db_position = result[1]
            if selected_position != db_position:
                return render_template('login.html', error="Position does not match our records.")

            session['user_id'] = result[0]
            session['position'] = db_position
            session['user_type'] = 'employee'
            session['user_name'] = result[3]

            if db_position == 'Manager':
                session['hotel_id'] = result[2]

            return redirect(url_for('employee.employee_dashboard'))

    return render_template('login.html')



@bp_auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name'].strip()
        address = request.form['address'].strip()
        id_type = request.form['id_type']
        id_number = request.form['id_number'].strip()
        registration_date = date.today()

        if not full_name or not address or not id_type or not id_number:
            return render_template('register.html', error="Please fill in all fields.")


        existing = db.session.execute(text("""
            SELECT 1 FROM Customer WHERE LOWER(FullName) = :name AND IDNumber = :idnum
        """), {'name': full_name.lower(), 'idnum': id_number}).fetchone()

        if existing:
            return render_template('register.html', error="An account with that name and ID already exists.")

        try:
            db.session.execute(text("""
                INSERT INTO Customer (FullName, Address, IDType, IDNumber, RegistrationDate)
                VALUES (:name, :address, :idtype, :idnum, :regdate)
            """), {
                'name': full_name,
                'address': address,
                'idtype': id_type,
                'idnum': id_number,
                'regdate': registration_date
            })
            db.session.commit()
            flash("✅ Account created successfully. Please log in.")
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            return render_template('register.html', error=f"❌ Registration failed: {e}")

    return render_template('register.html')


@bp_auth.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
