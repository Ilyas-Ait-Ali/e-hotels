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
        full_name_input = request.form['full_name'].strip()
        full_name = full_name_input.lower()
        user_type = request.form['user_type']
        selected_position = request.form.get('position')

        if not full_name or user_type not in ['customer', 'employee']:
            return render_template('login.html', error="Invalid input")

        if user_type == 'customer':
            query = text("SELECT CustomerID, FullName FROM Customer WHERE LOWER(FullName) = :name")
            result = db.session.execute(query, {'name': full_name}).fetchone()
            if not result:
                return render_template('login.html', error="Customer not found")

            session['user_id'] = result[0]
            session['user_type'] = 'customer'
            session['user_name'] = result[1]
            return redirect(url_for('customer.my_bookings'))

        else:  # employee login
            query = text("SELECT EmployeeID, Position, HotelID, FullName FROM Employee WHERE LOWER(FullName) = :name")
            result = db.session.execute(query, {'name': full_name}).fetchone()

            if not result:
                return render_template('login.html', error="Employee not found")

            db_position = result[1]
            if not selected_position or selected_position != db_position:
                return render_template('login.html', error="Position does not match our records.")

            session['user_id'] = result[0]
            session['position'] = db_position
            session['user_type'] = user_type
            session['user_name'] = result[3]

            if db_position == 'Manager':
                session['hotel_id'] = result[2]

            return redirect(url_for('employee.employee_dashboard'))

    return render_template('login.html')


@bp_auth.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
