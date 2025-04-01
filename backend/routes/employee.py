from flask import Blueprint, flash, render_template, request, redirect, url_for, session
from sqlalchemy import text
from datetime import date, datetime
from app import db

bp_employee = Blueprint('employee', __name__)

@bp_employee.route('/employee/dashboard')
def employee_dashboard():
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    position = session.get('position')
    hotel_id = session.get('hotel_id')

    base_query = """
        SELECT b.BookingID, b.CheckInDate, b.CheckOutDate, b.Status,
               b.RoomID, h.HotelName, c.FullName AS CustomerName, b.HotelID
        FROM Booking b
        JOIN Hotel h ON b.HotelID = h.HotelID
        JOIN Customer c ON b.CustomerID = c.CustomerID
        WHERE b.Status IN ('Pending', 'Checked-in')
          AND b.CheckInDate >= CURRENT_DATE
          AND NOT EXISTS (
              SELECT 1 FROM Rental r WHERE r.BookingID = b.BookingID
          )
    """

    params = {}
    if position != 'Admin':
        base_query += " AND b.HotelID = :hid"
        params['hid'] = hotel_id

    base_query += " ORDER BY b.CheckInDate"

    results = db.session.execute(text(base_query), params).fetchall()

    return render_template("employee/dashboard.html", bookings=results)

@bp_employee.route('/employee/convert-booking', methods=['POST'])
def convert_booking():
    if 'user_type' not in session or session['user_type'] != 'employee':
        flash("You must be logged in as an employee.")
        return redirect(url_for('auth.login'))

    position = session.get('position')
    hotel_id = session.get('hotel_id')  
    employee_id = session.get('user_id')
    booking_id = request.form.get('booking_id')

    try:
        booking = db.session.execute(text("""
            SELECT * FROM Booking WHERE BookingID = :bid
        """), {'bid': booking_id}).fetchone()

        if not booking:
            flash("❌ Booking not found.")
            return redirect(url_for('employee.employee_dashboard'))

        
        if position != 'Admin' and booking.hotelid != hotel_id:
            flash("❌ You are not authorized to convert bookings from other hotels.")
            return redirect(url_for('employee.employee_dashboard'))

        db.session.execute(text("""
            UPDATE Booking SET Status = 'Checked-in' WHERE BookingID = :bid
        """), {'bid': booking_id})

        db.session.execute(text("""
            INSERT INTO Rental (
                CustomerID, HotelID, RoomID, EmployeeID, BookingID,
                CheckInDate, CheckOutDate, Status, PaymentAmount,
                PaymentDate, PaymentMethod
            ) VALUES (
                :cid, :hid, :rid, :eid, :bid,
                :checkin, :checkout, 'Ongoing', 0, CURRENT_DATE, 'Pending'
            )
        """), {
            'cid': booking.customerid,
            'hid': booking.hotelid,
            'rid': booking.roomid,
            'eid': employee_id,
            'bid': booking.bookingid,
            'checkin': booking.checkindate,
            'checkout': booking.checkoutdate
        })

        db.session.commit()
        flash("✅ Booking converted to rental.")

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Failed to convert booking: {e}")

    return redirect(url_for('employee.employee_dashboard'))

@bp_employee.route('/employee/rent-room', methods=['GET', 'POST'])
def rent_room():
    if 'user_type' not in session or session['user_type'] != 'employee':
        flash("You must be logged in as an employee.")
        return redirect(url_for('auth.login'))

    position = session.get("position")
    hotel_id = session.get("hotel_id") if position != 'Admin' else None

    if request.method == 'POST':
        customer_name = request.form.get("customer_name").strip()
        customer_id = request.form.get("customer_id")
        room_id = request.form.get("room_id")
        checkin = request.form.get("checkin")
        checkout = request.form.get("checkout")
        payment_amount = request.form.get("payment_amount")
        payment_method = request.form.get("payment_method")
        employee_id = session["user_id"]

        if position == "Admin":
            hotel_id = request.form.get("hotel_id")

        if not hotel_id:
            flash("❌ Hotel ID is required for Admin.")
            return redirect(url_for('employee.rent_room'))

        # Validate CustomerID + Name
        customer = db.session.execute(
            text("SELECT * FROM Customer WHERE CustomerID = :cid AND LOWER(FullName) = :name"),
            {"cid": customer_id, "name": customer_name.lower()}
        ).fetchone()

        if not customer:
            flash("❌ Customer ID and Name do not match any existing customer.")
            return redirect(url_for('employee.rent_room'))

        try:
            db.session.execute(text("""
                INSERT INTO Rental (
                    CustomerID, HotelID, RoomID, EmployeeID,
                    CheckInDate, CheckOutDate, Status,
                    PaymentAmount, PaymentDate, PaymentMethod
                )
                VALUES (
                    :customer_id, :hotel_id, :room_id, :employee_id,
                    :checkin, :checkout, 'Completed',
                    :payment_amount, CURRENT_DATE, :payment_method
                )
            """), {
                "customer_id": customer_id,
                "hotel_id": hotel_id,
                "room_id": room_id,
                "employee_id": employee_id,
                "checkin": checkin,
                "checkout": checkout,
                "payment_amount": payment_amount,
                "payment_method": payment_method
            })
            db.session.commit()

            hotel = db.session.execute(text("""
                SELECT HotelName FROM Hotel WHERE HotelID = :hid
            """), {"hid": hotel_id}).fetchone()

            return render_template(
                "employee/rent_success.html",
                customer_name=customer_name,
                hotel_name=hotel.hotelname if hotel else f"Hotel #{hotel_id}",
                room_id=room_id,
                checkin=checkin,
                checkout=checkout,
                payment_amount=float(payment_amount),
                payment_method=payment_method,
                current_date=date.today()
            )

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Rental failed: {e}")
            return redirect(url_for('employee.rent_room'))

    return render_template("employee/rent_form.html", is_admin=(position == "Admin"))

@bp_employee.route('/employee/customers')
def manage_customers():
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('position') != 'Admin':
        flash("❌ Only admins can manage customers.")
        return redirect(url_for('employee.employee_dashboard'))

    sort = request.args.get("sort", "id") 

    sort_map = {
        "fullname": "FullName",
        "id": "CustomerID",
        "registered": "RegistrationDate DESC",
        "idtype": "IDType",
    }
    order_clause = sort_map.get(sort, "CustomerID")

    customers = db.session.execute(text(f"""
        SELECT * FROM Customer ORDER BY {order_clause}
    """)).fetchall()

    return render_template("employee/customers.html", customers=customers, sort=sort)


@bp_employee.route('/employee/customers/add', methods=['GET', 'POST'])
def add_customer():
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('position') != 'Admin':
        flash("❌ Only admins can add customers.")
        return redirect(url_for('employee.employee_dashboard'))

    if request.method == 'POST':
        full_name = request.form['full_name']
        address = request.form['address']
        id_type = request.form['id_type']
        id_number = request.form['id_number']
        registration_date = request.form['registration_date']

        try:
            db.session.execute(text("""
                INSERT INTO Customer (FullName, Address, IDType, IDNumber, RegistrationDate)
                VALUES (:full_name, :address, :id_type, :id_number, :reg_date)
            """), {
                'full_name': full_name,
                'address': address,
                'id_type': id_type,
                'id_number': id_number,
                'reg_date': registration_date
            })
            db.session.commit()
            flash("✅ Customer added successfully.")
            return redirect(url_for('employee.manage_customers'))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Failed to add customer: {e}")

    return render_template("employee/customer_form.html", customer=None)

@bp_employee.route('/employee/customers/edit/<int:customer_id>', methods=['GET', 'POST'])
def edit_customer(customer_id):
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('position') != 'Admin':
        flash("❌ Only admins can edit customers.")
        return redirect(url_for('employee.employee_dashboard'))

    customer = db.session.execute(text("""
        SELECT * FROM Customer WHERE CustomerID = :cid
    """), {'cid': customer_id}).fetchone()

    if not customer:
        flash("❌ Customer not found.")
        return redirect(url_for('employee.manage_customers'))

    if request.method == 'POST':
        full_name = request.form['full_name']
        address = request.form['address']
        id_type = request.form['id_type']
        id_number = request.form['id_number']
        registration_date = request.form['registration_date']

        try:
            db.session.execute(text("""
                UPDATE Customer
                SET FullName = :full_name, Address = :address, IDType = :id_type,
                    IDNumber = :id_number, RegistrationDate = :reg_date
                WHERE CustomerID = :cid
            """), {
                'full_name': full_name,
                'address': address,
                'id_type': id_type,
                'id_number': id_number,
                'reg_date': registration_date,
                'cid': customer_id
            })
            db.session.commit()
            flash("✅ Customer updated successfully.")
            return redirect(url_for('employee.manage_customers'))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Failed to update customer: {e}")

    return render_template("employee/customer_form.html", customer=customer)

@bp_employee.route('/employee/customers/delete/<int:customer_id>', methods=['POST'])
def delete_customer(customer_id):
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('position') != 'Admin':
        flash("❌ Only admins can delete customers.")
        return redirect(url_for('employee.employee_dashboard'))

    try:
        db.session.execute(text("DELETE FROM Customer WHERE CustomerID = :cid"), {'cid': customer_id})
        db.session.commit()
        flash("🗑️ Customer deleted successfully.")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Failed to delete customer: {e}")

    return redirect(url_for('employee.manage_customers'))

@bp_employee.route('/employee/employees')
def manage_employees():
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    position = session.get('position')
    hotel_id = session.get('hotel_id')
    sort = request.args.get("sort", "id")  

    sort_map = {
        "name": "FullName",
        "address": "Address",
        "position": "Position",
        "ssn": "SSN",
        "hotel": "HotelID",
        "id": "EmployeeID"
    }

    order_clause = sort_map.get(sort, "EmployeeID")

    if position == 'Admin':
        query = text(f"""
            SELECT EmployeeID, FullName, Address, Position, SSN, HotelID
            FROM Employee
            ORDER BY {order_clause}
        """)
        params = {}

    elif position == 'Manager':
        query = text(f"""
            SELECT EmployeeID, FullName, Address, Position, SSN, HotelID
            FROM Employee
            WHERE HotelID = :hid
            ORDER BY {order_clause}
        """)
        params = {'hid': hotel_id}

    else:
        flash("❌ Access denied.")
        return redirect(url_for('employee.employee_dashboard'))

    employees = db.session.execute(query, params).fetchall()
    return render_template("employee/employees.html", employees=employees, sort=sort)


@bp_employee.route('/employee/employees/add', methods=['GET', 'POST'])
def add_employee():
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    position = session.get('position')
    hotel_id = session.get('hotel_id')

    if position not in ['Admin', 'Manager']:
        flash("❌ Access denied.")
        return redirect(url_for('employee.employee_dashboard'))

    if request.method == 'POST':
        fullname = request.form.get("fullname")
        address = request.form.get("address")
        emp_position = request.form.get("position")
        ssn = request.form.get("ssn")
        emp_hotel_id = int(request.form.get("hotel_id"))

        
        if position == 'Manager':
            if emp_position in ['Admin', 'Manager']:
                flash("❌ You cannot assign Admin or Manager positions.")
                return redirect(url_for('employee.add_employee'))
            if emp_hotel_id != hotel_id:
                flash("❌ You can only assign employees to your own hotel.")
                return redirect(url_for('employee.add_employee'))

        try:
            db.session.execute(text("""
                INSERT INTO Employee (FullName, Address, Position, SSN, HotelID)
                VALUES (:name, :addr, :pos, :ssn, :hid)
            """), {
                "name": fullname,
                "addr": address,
                "pos": emp_position,
                "ssn": ssn,
                "hid": emp_hotel_id
            })

            db.session.commit()
            flash("✅ Employee added successfully.")
            return redirect(url_for('employee.manage_employees'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Failed to add employee: {e}")

    return render_template("employee/employee_form.html", mode="add", employee=None)

@bp_employee.route('/employee/employees/edit/<int:employee_id>', methods=['GET', 'POST'])
def edit_employee(employee_id):
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    position = session.get('position')
    hotel_id = session.get('hotel_id')
    current_user_id = session['user_id']

    employee = db.session.execute(
        text("SELECT * FROM Employee WHERE EmployeeID = :eid"),
        {'eid': employee_id}
    ).fetchone()

    if not employee:
        flash("❌ Employee not found.")
        return redirect(url_for('employee.manage_employees'))

    # Permissions
    if position == 'Manager':
        # Managers can edit themselves
        if employee.employeeid != current_user_id:
            # But cannot edit Admins or Managers from other hotels
            if employee.position in ['Admin', 'Manager'] or employee.hotelid != hotel_id:
                flash("❌ Managers can only edit employees from their own hotel who are not Admin or Manager.")
                return redirect(url_for('employee.manage_employees'))

    if request.method == 'POST':
        fullname = request.form.get('fullname')
        address = request.form.get('address')
        emp_position = request.form.get('position')
        ssn = request.form.get('ssn')
        emp_hotel_id = int(request.form.get('hotel_id'))

        if not all([fullname, address, emp_position, ssn, emp_hotel_id]):
            flash("❌ All fields are required.")
            return redirect(url_for('employee.edit_employee', employee_id=employee_id))

        # Restrict what a Manager can change
        if position == 'Manager':
            if emp_position in ['Admin', 'Manager']:
                flash("❌ You cannot assign Admin or Manager roles.")
                return redirect(url_for('employee.edit_employee', employee_id=employee_id))
            if emp_hotel_id != hotel_id:
                flash("❌ You can only assign employees to your own hotel.")
                return redirect(url_for('employee.edit_employee', employee_id=employee_id))

        try:
            db.session.execute(text("""
                UPDATE Employee
                SET FullName = :name,
                    Address = :addr,
                    Position = :pos,
                    SSN = :ssn,
                    HotelID = :hid
                WHERE EmployeeID = :eid
            """), {
                'name': fullname,
                'addr': address,
                'pos': emp_position,
                'ssn': ssn,
                'hid': emp_hotel_id,
                'eid': employee_id
            })
            db.session.commit()
            flash("✅ Employee updated successfully.")
            return redirect(url_for('employee.manage_employees'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Failed to update employee: {e}")

    return render_template("employee/employee_form.html", mode='edit', employee=employee)

@bp_employee.route('/employee/employees/delete/<int:employee_id>', methods=['POST'])
def delete_employee(employee_id):
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    position = session.get('position')
    hotel_id = session.get('hotel_id')

    employee = db.session.execute(
        text("SELECT * FROM Employee WHERE EmployeeID = :eid"),
        {'eid': employee_id}
    ).fetchone()

    if not employee:
        flash("❌ Employee not found.")
        return redirect(url_for('employee.manage_employees'))

    if position == 'Admin' and employee.employeeid == session['user_id']:
        flash("⚠️ You cannot delete your own account.")
        return redirect(url_for('employee.manage_employees'))

    elif position == 'Manager' and employee.employeeid == session['user_id']:
        flash("⚠️ You cannot delete your own account.")
        return redirect(url_for('employee.manage_employees'))

    # Manager restrictions
    if position == 'Manager':
        if employee.hotelid != hotel_id or employee.position in ['Admin', 'Manager']:
            flash("❌ You do not have permission to delete this employee.")
            return redirect(url_for('employee.manage_employees'))

    try:
        db.session.execute(text("DELETE FROM Employee WHERE EmployeeID = :eid"), {'eid': employee_id})
        db.session.commit()
        flash("✅ Employee deleted successfully.")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Failed to delete employee: {e}")

    return redirect(url_for('employee.manage_employees'))

@bp_employee.route('/employee/hotels')
def manage_hotels():
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('position') != 'Admin':
        flash("❌ Only admins can access hotel management.")
        return redirect(url_for('auth.login'))

    sort = request.args.get("sort", "id") 

    sort_map = {
        "name": "HotelName",
        "address": "Address",
        "category": "Category",
        "num_rooms": "Num_Rooms DESC",
        "rating": "Rating DESC",
        "id": "HotelID"
    }

    order_clause = sort_map.get(sort, "HotelID")

    hotels = db.session.execute(text(f"""
        SELECT * FROM Hotel ORDER BY {order_clause}
    """)).fetchall()

    return render_template("employee/hotels.html", hotels=hotels, sort=sort)



@bp_employee.route('/employee/hotels/add', methods=['GET', 'POST'])
def add_hotel():
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('position') != 'Admin':
        flash("❌ Only admins can add hotels.")
        return redirect(url_for('auth.login'))

    hotel_chains = db.session.execute(text("SELECT HotelChainID, ChainName FROM HotelChain")).fetchall()

    if request.method == 'POST':
        hotel_name = request.form.get('hotel_name')
        address = request.form.get('address')
        hotel_chain_id = request.form.get('hotel_chain_id')
        category = request.form.get('category')
        num_rooms = request.form.get('num_rooms')
        rating = request.form.get('rating')

        valid_categories = ['Luxury', 'Resort', 'Boutique']

        try:
            hotel_chain_id = int(hotel_chain_id)
            num_rooms = int(num_rooms)
            rating = int(rating)

            if num_rooms < 0:
                flash("❌ Number of rooms must be non-negative.")
                return redirect(url_for('employee.add_hotel'))
            if rating < 1 or rating > 5:
                flash("❌ Rating must be between 1 and 5.")
                return redirect(url_for('employee.add_hotel'))
            if category not in valid_categories:
                flash("❌ Invalid category.")
                return redirect(url_for('employee.add_hotel'))

        except (ValueError, TypeError):
            flash("❌ Invalid input: ensure all numeric fields are filled correctly.")
            return redirect(url_for('employee.add_hotel'))

        try:
            db.session.execute(text("""
                INSERT INTO Hotel (HotelName, Address, HotelChainID, Category, Num_Rooms, Rating)
                VALUES (:hotel_name, :address, :hotel_chain_id, :category, :num_rooms, :rating)
            """), {
                'hotel_name': hotel_name,
                'address': address,
                'hotel_chain_id': hotel_chain_id,
                'category': category,
                'num_rooms': num_rooms,
                'rating': rating
            })
            db.session.commit()
            flash("✅ Hotel added successfully.")
            return redirect(url_for('employee.manage_hotels'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Failed to add hotel: {e}")

    return render_template("employee/hotel_form.html", mode="add", hotel_chains=hotel_chains)

@bp_employee.route('/employee/hotels/edit/<int:hotel_id>', methods=['GET', 'POST'])
def edit_hotel(hotel_id):
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('position') != 'Admin':
        flash("❌ Only admins can edit hotels.")
        return redirect(url_for('auth.login'))

    hotel = db.session.execute(text("SELECT * FROM Hotel WHERE HotelID = :hid"), {'hid': hotel_id}).fetchone()
    if not hotel:
        flash("❌ Hotel not found.")
        return redirect(url_for('employee.manage_hotels'))

    hotel_chains = db.session.execute(text("SELECT HotelChainID, ChainName FROM HotelChain")).fetchall()

    if request.method == 'POST':
        hotel_name = request.form.get('hotel_name')
        address = request.form.get('address')
        hotel_chain_id = request.form.get('hotel_chain_id')
        category = request.form.get('category')
        num_rooms = request.form.get('num_rooms')
        rating = request.form.get('rating')

        valid_categories = ['Luxury', 'Resort', 'Boutique']

        try:
            hotel_chain_id = int(hotel_chain_id)
            num_rooms = int(num_rooms)
            rating = int(rating)

            if num_rooms < 0:
                flash("❌ Number of rooms must be non-negative.")
                return redirect(url_for('employee.edit_hotel', hotel_id=hotel_id))
            if rating < 1 or rating > 5:
                flash("❌ Rating must be between 1 and 5.")
                return redirect(url_for('employee.edit_hotel', hotel_id=hotel_id))
            if category not in valid_categories:
                flash("❌ Invalid category.")
                return redirect(url_for('employee.edit_hotel', hotel_id=hotel_id))

        except (ValueError, TypeError):
            flash("❌ Invalid input: ensure all numeric fields are filled correctly.")
            return redirect(url_for('employee.edit_hotel', hotel_id=hotel_id))

        try:
            db.session.execute(text("""
                UPDATE Hotel
                SET HotelName = :hotel_name,
                    Address = :address,
                    HotelChainID = :hotel_chain_id,
                    Category = :category,
                    Num_Rooms = :num_rooms,
                    Rating = :rating
                WHERE HotelID = :hid
            """), {
                'hotel_name': hotel_name,
                'address': address,
                'hotel_chain_id': hotel_chain_id,
                'category': category,
                'num_rooms': num_rooms,
                'rating': rating,
                'hid': hotel_id
            })
            db.session.commit()
            flash("✅ Hotel updated successfully.")
            return redirect(url_for('employee.manage_hotels'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Failed to update hotel: {e}")

    return render_template("employee/hotel_form.html", mode='edit', hotel=hotel, hotel_chains=hotel_chains)

@bp_employee.route('/employee/hotels/delete/<int:hotel_id>', methods=['POST'])
def delete_hotel(hotel_id):
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('position') != 'Admin':
        flash("❌ Only admins can delete hotels.")
        return redirect(url_for('auth.login'))

    bookings = db.session.execute(text("""
        SELECT 1 FROM Booking WHERE HotelID = :hid LIMIT 1
    """), {'hid': hotel_id}).fetchone()

    if bookings:
        flash("❌ Cannot delete the hotel because it has existing bookings.")
        return redirect(url_for('employee.manage_hotels'))

    try:
        db.session.execute(text("DELETE FROM Hotel WHERE HotelID = :hid"), {'hid': hotel_id})
        db.session.commit()
        flash("✅ Hotel deleted successfully.")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Failed to delete hotel: {e}")

    return redirect(url_for('employee.manage_hotels'))


@bp_employee.route('/employee/rooms')
def manage_rooms():
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    position = session.get('position')
    hotel_id = session.get('hotel_id')
    sort = request.args.get('sort', 'roomid_asc')

    sort_map = {
        'roomid_asc': 'RoomID ASC',
        'roomid_desc': 'RoomID DESC',
        'price_asc': 'Price ASC',
        'price_desc': 'Price DESC',
        'capacity': "CASE Capacity WHEN 'single' THEN 1 WHEN 'double' THEN 2 WHEN 'triple' THEN 3 WHEN 'family' THEN 4 WHEN 'suite' THEN 5 ELSE 6 END",
        'status': 'Status',
        'viewtype': 'ViewType'
    }

    order_clause = sort_map.get(sort, 'RoomID ASC')

    if position == 'Admin':
        query = text(f"SELECT * FROM Room ORDER BY {order_clause}")
        params = {}
    elif position == 'Manager':
        query = text(f"SELECT * FROM Room WHERE HotelID = :hid ORDER BY {order_clause}")
        params = {'hid': hotel_id}
    else:
        flash("❌ Access denied.")
        return redirect(url_for('employee.employee_dashboard'))

    rooms = db.session.execute(query, params).fetchall()
    return render_template("employee/rooms.html", rooms=rooms, sort=sort)



@bp_employee.route('/employee/rooms/add', methods=['GET', 'POST'])
def add_room():
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    position = session.get('position')
    hotel_id = session.get('hotel_id')

    if position not in ['Admin', 'Manager']:
        flash("❌ Access denied.")
        return redirect(url_for('employee.employee_dashboard'))

    if request.method == 'POST':
        try:
            hotel_id_input = int(request.form.get('hotel_id'))
            price = float(request.form.get('price'))
        except (TypeError, ValueError):
            flash("❌ Invalid input for hotel ID or price.")
            return redirect(url_for('employee.add_room'))

        if price < 0:
            flash("❌ Price cannot be negative.")
            return redirect(url_for('employee.add_room'))

        if position == 'Manager' and hotel_id_input != hotel_id:
            flash("❌ You can only add rooms to your own hotel.")
            return redirect(url_for('employee.add_room'))

        capacity = request.form.get('capacity')
        viewtype = request.form.get('viewtype')
        extendable = request.form.get('extendable') == 'true'
        status = request.form.get('status')

        valid_capacities = ['single', 'double', 'triple', 'family', 'suite']
        valid_views = ['none', 'mountain_view', 'sea_view', 'both']
        valid_statuses = ['Available', 'Occupied', 'Out-Of-Order']

        if capacity not in valid_capacities or viewtype not in valid_views or status not in valid_statuses:
            flash("❌ Invalid input selection.")
            return redirect(url_for('employee.add_room'))

        try:
            db.session.execute(text("""
                INSERT INTO Room (HotelID, Capacity, ViewType, Extendable, Price, Status)
                VALUES (:hotel_id, :capacity, :viewtype, :extendable, :price, :status)
            """), {
                'hotel_id': hotel_id_input,
                'capacity': capacity,
                'viewtype': viewtype,
                'extendable': extendable,
                'price': price,
                'status': status
            })
            db.session.commit()
            flash("✅ Room added successfully.")
            return redirect(url_for('employee.manage_rooms'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Failed to add room: {e}")

    return render_template("employee/room_form.html", mode='add')



@bp_employee.route('/employee/rooms/edit/<int:room_id>', methods=['GET', 'POST'])
def edit_room(room_id):
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    position = session.get('position')
    hotel_id = session.get('hotel_id')

    room = db.session.execute(text("SELECT * FROM Room WHERE RoomID = :rid"), {'rid': room_id}).fetchone()
    if not room:
        flash("❌ Room not found.")
        return redirect(url_for('employee.manage_rooms'))

    if position == 'Manager' and room.hotelid != hotel_id:
        flash("❌ You can only edit rooms from your own hotel.")
        return redirect(url_for('employee.manage_rooms'))

    if request.method == 'POST':
        try:
            hotel_id_input = int(request.form.get('hotel_id'))
            price = float(request.form.get('price'))
        except (TypeError, ValueError):
            flash("❌ Invalid input for hotel ID or price.")
            return redirect(url_for('employee.edit_room', room_id=room_id))

        if price < 0:
            flash("❌ Price cannot be negative.")
            return redirect(url_for('employee.edit_room', room_id=room_id))

        if position == 'Manager' and hotel_id_input != hotel_id:
            flash("❌ You cannot reassign a room to another hotel.")
            return redirect(url_for('employee.edit_room', room_id=room_id))

        capacity = request.form.get('capacity')
        viewtype = request.form.get('viewtype')
        extendable = request.form.get('extendable') == 'true'
        status = request.form.get('status')

        valid_capacities = ['single', 'double', 'triple', 'family', 'suite']
        valid_views = ['none', 'mountain_view', 'sea_view', 'both']
        valid_statuses = ['Available', 'Occupied', 'Out-Of-Order']

        if capacity not in valid_capacities or viewtype not in valid_views or status not in valid_statuses:
            flash("❌ Invalid input selection.")
            return redirect(url_for('employee.edit_room', room_id=room_id))

        try:
            db.session.execute(text("""
                UPDATE Room
                SET HotelID = :hotel_id,
                    Capacity = :capacity,
                    ViewType = :viewtype,
                    Extendable = :extendable,
                    Price = :price,
                    Status = :status
                WHERE RoomID = :rid
            """), {
                'hotel_id': hotel_id_input,
                'capacity': capacity,
                'viewtype': viewtype,
                'extendable': extendable,
                'price': price,
                'status': status,
                'rid': room_id
            })
            db.session.commit()
            flash("✅ Room updated successfully.")
            return redirect(url_for('employee.manage_rooms'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Failed to update room: {e}")

    return render_template("employee/room_form.html", mode='edit', room=room)




@bp_employee.route('/employee/rooms/delete/<int:room_id>', methods=['POST'])
def delete_room(room_id):
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('position') != 'Manager':
        flash("Only managers can delete rooms.")
        return redirect(url_for('auth.login'))

    try:
        db.session.execute(text("DELETE FROM Room WHERE RoomID = :rid"), {'rid': room_id})
        db.session.commit()
        flash("✅ Room deleted successfully.")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Failed to delete room: {e}")

    return redirect(url_for('employee.manage_rooms'))


@bp_employee.route('/employee/problems')
def manage_room_problems():
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    position = session.get('position')
    user_id = session.get('user_id')
    hotel_id = session.get('hotel_id')
    sort = request.args.get('sort', 'report_desc')

    sort_map = {
        'report_desc': 'rp.ReportDate DESC',
        'report_asc': 'rp.ReportDate ASC',
        'roomid': 'rp.RoomID',
        'hotelname': 'h.HotelName',
        'status': 'rp.Resolved',
    }
    order_clause = sort_map.get(sort, 'rp.ReportDate DESC')

    if position == 'Admin':
        query = text(f"""
            SELECT rp.*, h.HotelName
            FROM RoomProblems rp
            JOIN Hotel h ON rp.HotelID = h.HotelID
            ORDER BY {order_clause}
        """)
        problems = db.session.execute(query).fetchall()

    elif position == 'Manager':
        if not hotel_id:
            flash("⚠️ Hotel information missing for manager.")
            return redirect(url_for('employee.employee_dashboard'))

        query = text(f"""
            SELECT rp.*, h.HotelName
            FROM RoomProblems rp
            JOIN Hotel h ON rp.HotelID = h.HotelID
            WHERE rp.HotelID = :hid
            ORDER BY {order_clause}
        """)
        problems = db.session.execute(query, {'hid': hotel_id}).fetchall()
    else:
        flash("Access denied.")
        return redirect(url_for('employee.employee_dashboard'))

    return render_template('employee/room_problems.html', problems=problems, sort=sort)



@bp_employee.route('/employee/problems/add', methods=['GET', 'POST'])
def add_room_problem():
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    position = session.get('position')
    hotel_id = session.get('hotel_id') if position == 'Manager' else None

    if request.method == 'POST':
        try:
            hotel_id_form = int(request.form.get('hotel_id'))
            room_id = int(request.form.get('room_id'))
            problem = request.form.get('problem', '').strip()
            report_date = request.form.get('report_date')

            if hotel_id_form < 1 or room_id < 1:
                raise ValueError("Hotel ID and Room ID must be positive.")

            if not problem:
                raise ValueError("Problem description cannot be empty.")

            if date.fromisoformat(report_date) > date.today():
                raise ValueError("Report date cannot be in the future.")

            if position == 'Manager' and hotel_id != hotel_id_form:
                flash("⚠️ Managers can only report problems for their own hotel.")
                return redirect(url_for('employee.manage_room_problems'))

            db.session.execute(text("""
                INSERT INTO RoomProblems (HotelID, RoomID, Problem, ReportDate, Resolved)
                VALUES (:hid, :rid, :prob, :rdate, FALSE)
            """), {
                'hid': hotel_id_form,
                'rid': room_id,
                'prob': problem,
                'rdate': report_date
            })
            db.session.commit()
            flash("✅ Room problem reported successfully.")
            return redirect(url_for('employee.manage_room_problems'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Failed to add room problem: {e}")

    return render_template("employee/room_problem_form.html", mode='add', hotel_id=hotel_id, current_date=date.today().isoformat())


@bp_employee.route('/employee/problems/edit/<int:room_id>/<path:problem>', methods=['GET', 'POST'])
def edit_room_problem(room_id, problem):
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    position = session.get('position')
    hotel_id = session.get('hotel_id') if position == 'Manager' else None

    room_problem = db.session.execute(text("""
        SELECT * FROM RoomProblems WHERE RoomID = :rid AND Problem = :prob
    """), {'rid': room_id, 'prob': problem}).fetchone()

    if not room_problem:
        flash("❌ Problem not found.")
        return redirect(url_for('employee.manage_room_problems'))

    if position == 'Manager' and room_problem.hotelid != hotel_id:
        flash("⚠️ Managers can only edit problems in their own hotel.")
        return redirect(url_for('employee.manage_room_problems'))

    if request.method == 'POST':
        try:
            new_problem = request.form.get('problem', '').strip()
            report_date = request.form.get('report_date')
            resolved = request.form.get('resolved') == 'true'

            if not new_problem:
                raise ValueError("Problem description cannot be empty.")

            if date.fromisoformat(report_date) > date.today():
                raise ValueError("Report date cannot be in the future.")

            db.session.execute(text("""
                UPDATE RoomProblems
                SET Problem = :new_prob, ReportDate = :rdate, Resolved = :resolved
                WHERE HotelID = :hid AND RoomID = :rid AND Problem = :old_prob
            """), {
                'new_prob': new_problem,
                'rdate': report_date,
                'resolved': resolved,
                'hid': room_problem.hotelid,
                'rid': room_id,
                'old_prob': problem
            })
            db.session.commit()
            flash("✅ Room problem updated.")
            return redirect(url_for('employee.manage_room_problems'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Update failed: {e}")

    return render_template("employee/room_problem_form.html", mode='edit', problem_data=room_problem, current_date=date.today().isoformat())



@bp_employee.route('/employee/problems/delete/<int:room_id>/<path:problem>', methods=['POST'])
def delete_room_problem(room_id, problem):
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    position = session.get('position')
    hotel_id = session.get('hotel_id') if position == 'Manager' else None

    # Fetch the record to validate hotel access
    problem_row = db.session.execute(text("""
        SELECT * FROM RoomProblems WHERE RoomID = :rid AND Problem = :prob
    """), {'rid': room_id, 'prob': problem}).fetchone()

    if not problem_row:
        flash("❌ Room problem not found.")
        return redirect(url_for('employee.manage_room_problems'))

    if position == 'Manager' and problem_row.hotelid != hotel_id:
        flash("⚠️ Managers can only delete problems in their own hotel.")
        return redirect(url_for('employee.manage_room_problems'))

    try:
        db.session.execute(text("""
            DELETE FROM RoomProblems
            WHERE HotelID = :hid AND RoomID = :rid AND Problem = :prob
        """), {
            'hid': problem_row.hotelid,
            'rid': room_id,
            'prob': problem
        })
        db.session.commit()
        flash("✅ Room problem deleted.")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Deletion failed: {e}")

    return redirect(url_for('employee.manage_room_problems'))


@bp_employee.route('/employee/bookings')
def view_bookings():
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    hotel_id = session.get('hotel_id')
    position = session.get('position')
    sort = request.args.get('sort', 'checkin_desc')

    order_map = {
        'checkin_desc': 'b.CheckInDate DESC',
        'checkin_asc': 'b.CheckInDate ASC',
        'bookingdate': 'b.BookingDate DESC',
        'customer': 'c.FullName',
        'hotel': 'h.HotelName',
        'status': 'b.Status'
    }
    order_clause = order_map.get(sort, 'b.CheckInDate DESC')

    if position == 'Admin':
        query = text(f"""
            SELECT b.BookingID, c.FullName AS CustomerName, h.HotelName, b.RoomID,
                   b.BookingDate, b.CheckInDate, b.CheckOutDate, b.Status
            FROM Booking b
            JOIN Customer c ON b.CustomerID = c.CustomerID
            JOIN Hotel h ON b.HotelID = h.HotelID
            ORDER BY {order_clause}
        """)
        params = {}
    else:
        query = text(f"""
            SELECT b.BookingID, c.FullName AS CustomerName, h.HotelName, b.RoomID,
                   b.BookingDate, b.CheckInDate, b.CheckOutDate, b.Status
            FROM Booking b
            JOIN Customer c ON b.CustomerID = c.CustomerID
            JOIN Hotel h ON b.HotelID = h.HotelID
            WHERE b.HotelID = :hid
            ORDER BY {order_clause}
        """)
        params = {'hid': hotel_id}

    bookings = db.session.execute(query, params).fetchall()
    return render_template("employee/view_bookings.html", bookings=bookings, sort=sort)


@bp_employee.route('/employee/bookings/delete/<int:booking_id>', methods=['POST'])
def delete_booking(booking_id):
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    try:
        db.session.execute(text("DELETE FROM Booking WHERE BookingID = :bid"), {'bid': booking_id})
        db.session.commit()
        flash("✅ Booking archived and deleted.")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Failed to delete booking: {e}")

    return redirect(url_for('employee.view_bookings'))

@bp_employee.route('/employee/rentals')
def view_rentals():
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    hotel_id = session.get('hotel_id')
    position = session.get('position')
    sort = request.args.get('sort', 'checkin_desc')

    
    sort_options = {
        'checkin_desc': 'r.CheckInDate DESC',
        'checkin_asc': 'r.CheckInDate ASC',
        'customer': 'c.FullName',
        'hotel': 'h.HotelName',
        'status': 'r.Status',
        'payment': 'r.PaymentAmount DESC',
        'payment_asc': 'r.PaymentAmount ASC'
    }
    order_clause = sort_options.get(sort, 'r.CheckInDate DESC')

    
    db.session.execute(text("""
        UPDATE Rental
        SET Status = 'Completed'
        WHERE Status != 'Completed'
          AND CURRENT_DATE > CheckOutDate;
    """))
    db.session.execute(text("""
        UPDATE Rental
        SET Status = 'Ongoing'
        WHERE Status NOT IN ('Completed')
          AND CURRENT_DATE BETWEEN CheckInDate AND CheckOutDate;
    """))
    db.session.commit()

    if position == 'Admin':
        query = text(f"""
            SELECT r.RentalID, c.FullName AS CustomerName, h.HotelName, r.RoomID,
                   r.CheckInDate, r.CheckOutDate, r.Status, r.PaymentAmount, r.PaymentMethod
            FROM Rental r
            JOIN Customer c ON r.CustomerID = c.CustomerID
            JOIN Hotel h ON r.HotelID = h.HotelID
            ORDER BY {order_clause}
        """)
        params = {}
    else:
        query = text(f"""
            SELECT r.RentalID, c.FullName AS CustomerName, h.HotelName, r.RoomID,
                   r.CheckInDate, r.CheckOutDate, r.Status, r.PaymentAmount, r.PaymentMethod
            FROM Rental r
            JOIN Customer c ON r.CustomerID = c.CustomerID
            JOIN Hotel h ON r.HotelID = h.HotelID
            WHERE r.HotelID = :hid
            ORDER BY {order_clause}
        """)
        params = {'hid': hotel_id}

    rentals = db.session.execute(query, params).fetchall()
    return render_template("employee/view_rentals.html", rentals=rentals, sort=sort)

@bp_employee.route('/employee/rentals/delete/<int:rental_id>', methods=['POST'])
def delete_rental(rental_id):
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    try:

        db.session.execute(text("""
            DELETE FROM Rental WHERE RentalID = :rid
        """), {'rid': rental_id})

        db.session.commit()
        flash("✅ Rental archived and deleted.")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Failed to delete rental: {e}")

    return redirect(url_for('employee.view_rentals'))



@bp_employee.route('/employee/rentals/payment', methods=['POST'])
def add_payment():
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    rental_id = request.form.get('rental_id')
    payment_amount = request.form.get('payment_amount')
    payment_method = request.form.get('payment_method')

    try:
        db.session.execute(text("""
            UPDATE Rental
            SET PaymentAmount = :amount,
                PaymentMethod = :method,
                PaymentDate = CURRENT_DATE
            WHERE RentalID = :rid
        """), {
            'amount': payment_amount,
            'method': payment_method,
            'rid': rental_id
        })
        db.session.commit()
        flash("✅ Payment added successfully.")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Failed to add payment: {e}")

    return redirect(url_for('employee.view_rentals'))


@bp_employee.route('/employee/bookings/archive')
def view_booking_archive():
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    position = session.get('position')
    hotel_id = session.get('hotel_id')
    sort = request.args.get('sort', 'archivedate_desc')


    order_map = {
        'archivedate_desc': 'ArchiveDate DESC',
        'archivedate_asc': 'ArchiveDate ASC',
        'bookingdate': 'BookingDate',
        'checkin': 'CheckInDate',
        'customer': 'CustomerName',
        'hotel': 'HotelName'
    }
    order_clause = order_map.get(sort, 'ArchiveDate DESC')

    if position == 'Admin':
        query = text(f"SELECT * FROM BookingArchive ORDER BY {order_clause}")
        params = {}
    else:
        query = text(f"""
            SELECT * FROM BookingArchive 
            WHERE HotelName IN (
                SELECT HotelName FROM Hotel WHERE HotelID = :hid
            )
            ORDER BY {order_clause}
        """)
        params = {'hid': hotel_id}

    archived_bookings = db.session.execute(query, params).fetchall()
    return render_template("employee/booking_archive.html", bookings=archived_bookings, sort=sort)



@bp_employee.route('/employee/rentals/archive')
def view_rental_archive():
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    position = session.get('position')
    hotel_id = session.get('hotel_id')
    sort = request.args.get("sort", "archivedate_desc")

    order_clause = "ArchiveDate DESC"
    if sort == "archivedate_asc":
        order_clause = "ArchiveDate ASC"
    elif sort == "checkin":
        order_clause = "CheckInDate"
    elif sort == "customer":
        order_clause = "CustomerName"
    elif sort == "hotel":
        order_clause = "HotelName"
    elif sort == "employee":
        order_clause = "EmployeeName"

    if position == 'Admin':
        query = text(f"SELECT * FROM RentalArchive ORDER BY {order_clause}")
        params = {}
    else:
        query = text(f"""
            SELECT * FROM RentalArchive 
            WHERE HotelName IN (
                SELECT HotelName FROM Hotel WHERE HotelID = :hid
            )
            ORDER BY {order_clause}
        """)
        params = {'hid': hotel_id}

    archived_rentals = db.session.execute(query, params).fetchall()
    return render_template("employee/rental_archive.html", rentals=archived_rentals)