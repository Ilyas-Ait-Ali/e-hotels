from flask import Blueprint, flash, render_template, request, redirect, url_for, session
from sqlalchemy import text
from datetime import date, datetime
from app import db

bp_employee = Blueprint('employee', __name__)

@bp_employee.route('/employee/dashboard')
def employee_dashboard():
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    results = db.session.execute(text("""
        SELECT b.BookingID, b.CheckInDate, b.CheckOutDate, b.Status,
            b.RoomID, h.HotelName, c.FullName AS CustomerName
        FROM Booking b
        JOIN Hotel h ON b.HotelID = h.HotelID
        JOIN Customer c ON b.CustomerID = c.CustomerID
        WHERE b.Status IN ('Pending', 'Confirmed')
        AND b.CheckInDate >= CURRENT_DATE
        AND NOT EXISTS (
            SELECT 1 FROM Rental r WHERE r.BookingID = b.BookingID
        )
        ORDER BY b.CheckInDate
    """)).fetchall()


    return render_template("employee/dashboard.html", bookings=results)





@bp_employee.route('/employee/convert-booking', methods=['POST'])
def convert_booking():
    if 'user_type' not in session or session['user_type'] != 'employee':
        flash("You must be logged in as an employee.")
        return redirect(url_for('auth.login'))

    booking_id = request.form.get('booking_id')

    try:
        
        booking = db.session.execute(text("""
            SELECT * FROM Booking WHERE BookingID = :bid
        """), {'bid': booking_id}).fetchone()

        if not booking:
            flash("❌ Booking not found.")
            return redirect(url_for('employee.employee_dashboard'))

        
        db.session.execute(text("""
            UPDATE Booking SET Status = 'Confirmed' WHERE BookingID = :bid
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
            'eid': session['user_id'],
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

    if request.method == 'POST':
        customer_name = request.form.get("customer_name").strip()
        hotel_id = request.form.get("hotel_id")
        room_id = request.form.get("room_id")
        checkin = request.form.get("checkin")
        checkout = request.form.get("checkout")
        payment_amount = request.form.get("payment_amount")
        payment_method = request.form.get("payment_method")
        employee_id = session["user_id"]

        
        customer = db.session.execute(
            text("SELECT CustomerID FROM Customer WHERE FullName = :name"),
            {"name": customer_name}
        ).fetchone()

        if not customer:
            flash("❌ Customer not found.")
            return redirect(url_for('employee.rent_room'))

        customer_id = customer[0]

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

            return render_template(
                "employee/rent_success.html",
                customer_name=customer_name,
                hotel_id=hotel_id,
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

    return render_template("employee/rent_form.html")

@bp_employee.route('/employee/customers')
def manage_customers():
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    position = session.get('position')
    hotel_id = session.get('hotel_id')

    if position == 'Admin':
        customers = db.session.execute(text("""
            SELECT * FROM Customer ORDER BY FullName
        """)).fetchall()
    elif position == 'Manager':
        customers = db.session.execute(text("""
            SELECT DISTINCT c.*
            FROM Customer c
            LEFT JOIN Booking b ON c.CustomerID = b.CustomerID
            LEFT JOIN Rental r ON c.CustomerID = r.CustomerID
            WHERE b.HotelID = :hotel_id OR r.HotelID = :hotel_id
            ORDER BY c.FullName
        """), {'hotel_id': hotel_id}).fetchall()
    else:
        flash("❌ Access denied.")
        return redirect(url_for('employee.employee_dashboard'))

    return render_template("employee/customers.html", customers=customers)




@bp_employee.route('/employee/customers/add', methods=['GET', 'POST'])
def add_customer():
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    if session.get('position') not in ['Admin', 'Manager']:
        flash("❌ Access denied.")
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
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    customer = db.session.execute(text("""
        SELECT * FROM Customer WHERE CustomerID = :cid
    """), {'cid': customer_id}).fetchone()

    if not customer:
        flash("❌ Customer not found.")
        return redirect(url_for('employee.manage_customers'))

    # Manager permission check
    if session.get('position') == 'Manager':
        access = db.session.execute(text("""
            SELECT 1
            FROM Booking WHERE CustomerID = :cid AND HotelID = :hid
            UNION
            SELECT 1
            FROM Rental WHERE CustomerID = :cid AND HotelID = :hid
            LIMIT 1
        """), {'cid': customer_id, 'hid': session['hotel_id']}).fetchone()

        if not access:
            flash("❌ You do not have permission to edit this customer.")
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
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('auth.login'))

    # Manager permission check
    if session.get('position') == 'Manager':
        access = db.session.execute(text("""
            SELECT 1
            FROM Booking WHERE CustomerID = :cid AND HotelID = :hid
            UNION
            SELECT 1
            FROM Rental WHERE CustomerID = :cid AND HotelID = :hid
            LIMIT 1
        """), {'cid': customer_id, 'hid': session['hotel_id']}).fetchone()

        if not access:
            flash("❌ You do not have permission to delete this customer.")
            return redirect(url_for('employee.manage_customers'))

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

    if position == 'Admin':
        employees = db.session.execute(text("""
            SELECT EmployeeID, FullName, Address, Position, SSN, HotelID
            FROM Employee
            ORDER BY FullName
        """)).fetchall()

    elif position == 'Manager':
        employees = db.session.execute(text("""
            SELECT EmployeeID, FullName, Address, Position, SSN, HotelID
            FROM Employee
            WHERE HotelID = :hid
            ORDER BY FullName
        """), {'hid': hotel_id}).fetchall()

    else:
        flash("❌ Access denied.")
        return redirect(url_for('employee.employee_dashboard'))

    return render_template("employee/employees.html", employees=employees)



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

    employee = db.session.execute(
        text("SELECT * FROM Employee WHERE EmployeeID = :eid"),
        {'eid': employee_id}
    ).fetchone()

    if not employee:
        flash("❌ Employee not found.")
        return redirect(url_for('employee.manage_employees'))
    
    if position == 'Admin' and employee.employeeid == session['user_id']:
        flash("⚠️ You cannot edit your own account.")
        return redirect(url_for('employee.manage_employees'))
    elif position == 'Manager' and employee.employeeid == session['user_id']:
        flash("⚠️ You cannot edit your own account.")
        return redirect(url_for('employee.manage_employees'))



    if position == 'Manager':
        if employee.hotelid != hotel_id or employee.position in ['Admin', 'Manager']:
            flash("❌ You do not have permission to edit this employee.")
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

    hotels = db.session.execute(text("SELECT * FROM Hotel ORDER BY HotelName")).fetchall()
    return render_template("employee/hotels.html", hotels=hotels)


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

    if position == 'Admin':
        rooms = db.session.execute(text("SELECT * FROM Room ORDER BY HotelID, RoomID")).fetchall()
    elif position == 'Manager':
        rooms = db.session.execute(text("SELECT * FROM Room WHERE HotelID = :hid ORDER BY RoomID"), {'hid': hotel_id}).fetchall()
    else:
        flash("❌ Access denied.")
        return redirect(url_for('employee.employee_dashboard'))

    return render_template("employee/rooms.html", rooms=rooms)


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
        hotel_id_input = int(request.form.get('hotel_id'))
        if position == 'Manager' and hotel_id_input != hotel_id:
            flash("❌ You can only add rooms to your own hotel.")
            return redirect(url_for('employee.add_room'))

        capacity = request.form.get('capacity')
        viewtype = request.form.get('viewtype')
        extendable = request.form.get('extendable') == 'true'
        price = request.form.get('price')
        status = request.form.get('status')

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
        hotel_id_input = int(request.form.get('hotel_id'))
        if position == 'Manager' and hotel_id_input != hotel_id:
            flash("❌ You cannot reassign a room to another hotel.")
            return redirect(url_for('employee.edit_room', room_id=room_id))

        capacity = request.form.get('capacity')
        viewtype = request.form.get('viewtype')
        extendable = request.form.get('extendable') == 'true'
        price = request.form.get('price')
        status = request.form.get('status')

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
