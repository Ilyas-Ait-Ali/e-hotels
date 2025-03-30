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
        full_name = request.form['full_name'].strip()
        user_type = request.form['user_type']

        if not full_name or user_type not in ['customer', 'employee']:
            return render_template('login.html', error="Invalid input")

        if user_type == 'customer':
            query = text("SELECT CustomerID FROM Customer WHERE FullName = :name")
            result = db.session.execute(query, {'name': full_name}).fetchone()
            if not result:
                return render_template('login.html', error="Customer not found")
            session['user_id'] = result[0]

        else: 
            query = text("SELECT EmployeeID, Position FROM Employee WHERE FullName = :name")
            result = db.session.execute(query, {'name': full_name}).fetchone()
            if not result:
                return render_template('login.html', error="Employee not found")
            session['user_id'] = result[0]
            session['position'] = result[1] 

        session['user_type'] = user_type
        session['user_name'] = full_name

        if user_type == 'customer':
            return redirect(url_for('customer.my_bookings'))
        else:
            return redirect(url_for('employee.employee_dashboard'))

    return render_template('login.html')


@bp_auth.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

