from flask import Blueprint, flash, render_template, request, redirect, url_for, session
from sqlalchemy import text
from datetime import date, datetime
from app import db

bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    return redirect(url_for('main.login'))

@bp.route('/login', methods=['GET', 'POST'])
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
            return redirect(url_for('main.my_bookings'))
        else:
            return redirect(url_for('main.employee_dashboard'))

    return render_template('login.html')


@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.login'))

@bp.route('/customer/search')
def search_rooms():
    if 'user_type' not in session or session['user_type'] != 'customer':
        return redirect(url_for('main.login'))

    checkin = request.args.get("checkin")
    checkout = request.args.get("checkout")
    if not checkin or not checkout:
        return render_template("customer/search.html", rooms=[], checkin=None, checkout=None)

    try:
        checkin = datetime.strptime(checkin, "%Y-%m-%d").date()
        checkout = datetime.strptime(checkout, "%Y-%m-%d").date()
        if checkin >= checkout:
            return render_template("customer/search.html", rooms=[], checkin=checkin, checkout=checkout, error="Check-out must be after check-in")
    except Exception:
        return render_template("customer/search.html", rooms=[], checkin=None, checkout=None, error="Invalid dates")

    filters = ["r.Status = 'Available'"]
    params = {"checkin": checkin, "checkout": checkout}

    if request.args.get("capacity"):
        filters.append("r.Capacity = :capacity")
        params["capacity"] = request.args["capacity"]

    if request.args.get("area"):
        filters.append("h.Address ILIKE :area")
        params["area"] = f"%{request.args['area']}%"

    if request.args.get("chain"):
        filters.append("hc.ChainName ILIKE :chain")
        params["chain"] = f"%{request.args['chain']}%"

    if request.args.get("category"):
        filters.append("h.Category = :category")
        params["category"] = request.args["category"]

    if request.args.get("price"):
        filters.append("r.Price <= :price")
        params["price"] = request.args["price"]

    if request.args.get("minrooms"):
        filters.append("h.Num_Rooms >= :minrooms")
        params["minrooms"] = request.args["minrooms"]

    query = f"""
        SELECT r.*, h.HotelName, h.Address, hc.ChainName, h.Rating
        FROM Room r
        JOIN Hotel h ON r.HotelID = h.HotelID
        JOIN HotelChain hc ON h.HotelChainID = hc.HotelChainID
        WHERE
            {' AND '.join(filters)} AND
            NOT EXISTS (
                SELECT 1 FROM Booking b
                WHERE b.RoomID = r.RoomID AND b.HotelID = r.HotelID
                AND (b.CheckInDate, b.CheckOutDate) OVERLAPS (:checkin, :checkout)
            ) AND
            NOT EXISTS (
                SELECT 1 FROM Rental rt
                WHERE rt.RoomID = r.RoomID AND rt.HotelID = r.HotelID
                AND (rt.CheckInDate, rt.CheckOutDate) OVERLAPS (:checkin, :checkout)
            )
        ORDER BY r.Price
    """

    results = db.session.execute(text(query), params).fetchall()
    return render_template("customer/search.html", rooms=results, checkin=checkin, checkout=checkout)

@bp.route('/customer/bookings')
def my_bookings():
    if 'user_type' not in session or session['user_type'] != 'customer':
        return redirect(url_for('main.login'))

    customer_id = session['user_id']
    bookings = db.session.execute(text("""
        SELECT b.*, h.HotelName, h.Address
        FROM Booking b
        JOIN Hotel h ON b.HotelID = h.HotelID
        WHERE b.CustomerID = :cid
        ORDER BY b.CheckInDate DESC
    """), {'cid': customer_id}).fetchall()

    return render_template("customer/my_bookings.html", bookings=bookings, current_date=date.today())

@bp.route('/customer/book', methods=['POST'])
def book_room():
    if 'user_type' not in session or session['user_type'] != 'customer':
        flash("You must be logged in to book a room.")
        return redirect(url_for('main.login'))

    room_id = request.form.get("room_id")
    hotel_id = request.form.get("hotel_id")
    checkin = request.form.get("checkin")
    checkout = request.form.get("checkout")
    customer_id = session['user_id']
    today = date.today()

    try:
        
        db.session.execute(text("""
            INSERT INTO Booking (CustomerID, HotelID, RoomID, BookingDate, CheckInDate, CheckOutDate, Status)
            VALUES (:cid, :hid, :rid, :bdate, :checkin, :checkout, 'Confirmed')
        """), {
            'cid': customer_id,
            'hid': hotel_id,
            'rid': room_id,
            'bdate': today,
            'checkin': checkin,
            'checkout': checkout
        })
        db.session.commit()

        hotel = db.session.execute(
            text("SELECT HotelName FROM Hotel WHERE HotelID = :hid"),
            {'hid': hotel_id}
        ).fetchone()
        hotel_name = hotel[0] if hotel else "Unknown Hotel"


        return render_template(
            "customer/book_success.html",
            room_id=room_id,
            hotel_name=hotel_name,
            checkin=checkin,
            checkout=checkout
        )

    except Exception as e:
        db.session.rollback()
        flash(f"❌ Booking failed: {e}")
        return redirect(url_for('main.search_rooms'))

@bp.route('/view/available-rooms')
def available_rooms_per_area():
    results = db.session.execute(text("SELECT * FROM view_available_rooms_per_city")).fetchall()
    return render_template("view_available_rooms.html", rows=results)


@bp.route('/view/room-capacity')
def total_room_capacity():
    results = db.session.execute(text("SELECT * FROM view_total_capacity_per_hotel")).fetchall()
    return render_template("view_room_capacity.html", rows=results)

@bp.route('/customer/cancel-booking', methods=['POST'])
def cancel_booking():
    if 'user_type' not in session or session['user_type'] != 'customer':
        flash("You must be logged in to cancel a booking.")
        return redirect(url_for('main.login'))

    booking_id = request.form.get('booking_id')

    try:
        db.session.execute(text("""
            UPDATE Booking
            SET Status = 'Cancelled'
            WHERE BookingID = :bid
        """), {'bid': booking_id})
        db.session.commit()
        flash("✅ Booking successfully cancelled.")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Failed to cancel booking: {e}")

    return redirect(url_for('main.my_bookings'))

@bp.route('/employee/dashboard')
def employee_dashboard():
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('user_position') == 'Housekeeper':
        return redirect(url_for('main.login'))

    results = db.session.execute(text("""
        SELECT b.BookingID, b.CheckInDate, b.CheckOutDate, b.Status,
               b.RoomID, h.HotelName, c.FullName AS CustomerName
        FROM Booking b
        JOIN Hotel h ON b.HotelID = h.HotelID
        JOIN Customer c ON b.CustomerID = c.CustomerID
        WHERE b.Status = 'Confirmed' AND b.CheckInDate >= CURRENT_DATE
        ORDER BY b.CheckInDate
    """)).fetchall()

    return render_template("employee/dashboard.html", bookings=results)





@bp.route('/employee/convert-booking', methods=['POST'])
def convert_booking():
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('user_position') == 'Housekeeper':
        flash("You must be logged in as an employee.")
        return redirect(url_for('main.login'))

    booking_id = request.form.get('booking_id')

    try:
        
        booking = db.session.execute(text("""
            SELECT * FROM Booking WHERE BookingID = :bid
        """), {'bid': booking_id}).fetchone()

        if not booking:
            flash("❌ Booking not found.")
            return redirect(url_for('main.employee_dashboard'))

        
        db.session.execute(text("""
            UPDATE Booking SET Status = 'Cancelled' WHERE BookingID = :bid
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

    return redirect(url_for('main.employee_dashboard'))




@bp.route('/employee/rent-room', methods=['GET', 'POST'])
def rent_room():
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('user_position') == 'Housekeeper':
        flash("You must be logged in as an employee.")
        return redirect(url_for('main.login'))

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
            return redirect(url_for('main.rent_room'))

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
            return redirect(url_for('main.rent_room'))

    return render_template("employee/rent_form.html")

@bp.route('/employee/customers')
def manage_customers():
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('main.login'))
    if session.get('position') != 'Manager':
        flash("Access denied: Only Managers can manage customers.")
        return redirect(url_for('main.employee_dashboard'))

    customers = db.session.execute(text("SELECT * FROM Customer ORDER BY FullName")).fetchall()
    return render_template("employee/customers.html", customers=customers)



@bp.route('/employee/customers/add', methods=['GET', 'POST'])
def add_customer():
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('main.login'))

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
            return redirect(url_for('main.manage_customers'))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Failed to add customer: {e}")

    return render_template("employee/customer_form.html", customer=None)

@bp.route('/employee/customers/edit/<int:customer_id>', methods=['GET', 'POST'])
def edit_customer(customer_id):
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('main.login'))

    customer = db.session.execute(text("""
        SELECT * FROM Customer WHERE CustomerID = :cid
    """), {'cid': customer_id}).fetchone()

    if not customer:
        flash("❌ Customer not found.")
        return redirect(url_for('main.manage_customers'))

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
            return redirect(url_for('main.manage_customers'))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Failed to update customer: {e}")

    return render_template("employee/customer_form.html", customer=customer)

@bp.route('/employee/customers/delete/<int:customer_id>', methods=['POST'])
def delete_customer(customer_id):
    if 'user_type' not in session or session['user_type'] != 'employee':
        return redirect(url_for('main.login'))

    try:
        db.session.execute(text("DELETE FROM Customer WHERE CustomerID = :cid"), {'cid': customer_id})
        db.session.commit()
        flash("🗑️ Customer deleted successfully.")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Failed to delete customer: {e}")

    return redirect(url_for('main.manage_customers'))



@bp.route('/employee/employees')
def manage_employees():
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('position') != 'Manager':
        return redirect(url_for('main.login'))

    employees = db.session.execute(text("""
        SELECT EmployeeID, FullName, Address, Position, SSN, HotelID
        FROM Employee
        ORDER BY FullName
    """)).fetchall()

    return render_template("employee/employees.html", employees=employees)

@bp.route('/employee/employees/add', methods=['GET', 'POST'])
def add_employee():
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('position') != 'Manager':
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        try:
            name = request.form.get("name")
            addr = request.form.get("addr")
            pos = request.form.get("pos")
            ssn = request.form.get("ssn")
            hid = request.form.get("hid")

            db.session.execute(text("""
                INSERT INTO Employee (FullName, Address, Position, SSN, HotelID)
                VALUES (:name, :addr, :pos, :ssn, :hid)
            """), {
                "name": name,
                "addr": addr,
                "pos": pos,
                "ssn": ssn,
                "hid": hid
            })

            db.session.commit()
            flash("✅ Employee added successfully.")
            return redirect(url_for('main.manage_employees'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Failed to add employee: {e}")
            return redirect(url_for('main.add_employee'))

    return render_template("employee/employee_form.html", mode="add", employee=None)

@bp.route('/employee/employees/edit/<int:employee_id>', methods=['GET', 'POST'])
def edit_employee(employee_id):
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('position') != 'Manager':
        flash("Only managers can edit employees.")
        return redirect(url_for('main.login'))

    employee = db.session.execute(
        text("SELECT * FROM Employee WHERE EmployeeID = :eid"),
        {'eid': employee_id}
    ).fetchone()

    if not employee:
        flash("❌ Employee not found.")
        return redirect(url_for('main.manage_employees'))

    if request.method == 'POST':
        fullname = request.form.get('fullname', '')
        address = request.form.get('address', '')
        position = request.form.get('position', '')
        ssn = request.form.get('ssn', '')
        hotel_id = request.form.get('hotel_id', '')


        if not all([fullname, address, position, ssn, hotel_id]):
            flash("❌ All fields are required.")
            return redirect(url_for('main.edit_employee', employee_id=employee_id))


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
                'pos': position,
                'ssn': ssn,
                'hid': hotel_id,
                'eid': employee_id
            })
            db.session.commit()
            flash("✅ Employee updated successfully.")
            return redirect(url_for('main.manage_employees'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Failed to update employee: {e}")

    return render_template("employee/employee_form.html", mode='edit', employee=employee)

@bp.route('/employee/employees/delete/<int:employee_id>', methods=['POST'])
def delete_employee(employee_id):
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('position') != 'Manager':
        flash("Only managers can delete employees.")
        return redirect(url_for('main.login'))

    try:
        db.session.execute(text("DELETE FROM Employee WHERE EmployeeID = :eid"), {'eid': employee_id})
        db.session.commit()
        flash("✅ Employee deleted successfully.")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Failed to delete employee: {e}")

    return redirect(url_for('main.manage_employees'))



@bp.route('/employee/hotels')
def manage_hotels():
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('position') != 'Manager':
        flash("Only managers can access hotel management.")
        return redirect(url_for('main.login'))

    hotels = db.session.execute(text("SELECT * FROM Hotel ORDER BY HotelName")).fetchall()
    return render_template("employee/hotels.html", hotels=hotels)

@bp.route('/employee/hotels/add', methods=['GET', 'POST'])
def add_hotel():
    
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
            return redirect(url_for('main.manage_hotels'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Failed to add hotel: {e}")

    return render_template("employee/hotel_form.html", mode="add", hotel_chains=hotel_chains)

@bp.route('/employee/hotels/edit/<int:hotel_id>', methods=['GET', 'POST'])
def edit_hotel(hotel_id):
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('position') != 'Manager':
        flash("Only managers can edit hotels.")
        return redirect(url_for('main.login'))

    hotel = db.session.execute(text("SELECT * FROM Hotel WHERE HotelID = :hid"), {'hid': hotel_id}).fetchone()

    if not hotel:
        flash("❌ Hotel not found.")
        return redirect(url_for('main.manage_hotels'))

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
            return redirect(url_for('main.manage_hotels'))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Failed to update hotel: {e}")

    return render_template("employee/hotel_form.html", mode='edit', hotel=hotel)

@bp.route('/employee/hotels/delete/<int:hotel_id>', methods=['POST'])
def delete_hotel(hotel_id):
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('position') != 'Manager':
        flash("Only managers can delete hotels.")
        return redirect(url_for('main.login'))

    
    bookings = db.session.execute(text("""
        SELECT 1 FROM Booking WHERE HotelID = :hid LIMIT 1
    """), {'hid': hotel_id}).fetchone()

    if bookings:
        flash("❌ Cannot delete the hotel because it has existing bookings.")
        return redirect(url_for('main.manage_hotels'))

    try:
        db.session.execute(text("DELETE FROM Hotel WHERE HotelID = :hid"), {'hid': hotel_id})
        db.session.commit()
        flash("✅ Hotel deleted successfully.")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Failed to delete hotel: {e}")

    return redirect(url_for('main.manage_hotels'))






@bp.route('/employee/rooms')
def manage_rooms():
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('position') != 'Manager':
        flash("Only managers can view rooms.")
        return redirect(url_for('main.login'))

    rooms = db.session.execute(text("SELECT * FROM Room ORDER BY RoomID")).fetchall()
    return render_template("employee/rooms.html", rooms=rooms)

@bp.route('/employee/rooms/add', methods=['GET', 'POST'])
def add_room():
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('position') != 'Manager':
        flash("Only managers can add rooms.")
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        hotel_id = request.form.get('hotel_id')
        capacity = request.form.get('capacity')
        viewtype = request.form.get('viewtype')
        extendable = request.form.get('extendable')
        price = request.form.get('price')
        status = request.form.get('status')

        try:
            db.session.execute(text("""
                INSERT INTO Room (HotelID, Capacity, ViewType, Extendable, Price, Status)
                VALUES (:hotel_id, :capacity, :viewtype, :extendable, :price, :status)
            """), {
                'hotel_id': hotel_id,
                'capacity': capacity,
                'viewtype': viewtype,
                'extendable': extendable,
                'price': price,
                'status': status
            })
            db.session.commit()
            flash("✅ Room added successfully.")
            return redirect(url_for('main.manage_rooms'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Failed to add room: {e}")

    return render_template("employee/room_form.html", mode='add')


@bp.route('/employee/rooms/edit/<int:room_id>', methods=['GET', 'POST'])
def edit_room(room_id):
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('position') != 'Manager':
        flash("Only managers can edit rooms.")
        return redirect(url_for('main.login'))

    room = db.session.execute(text("SELECT * FROM Room WHERE RoomID = :rid"), {'rid': room_id}).fetchone()

    if not room:
        flash("❌ Room not found.")
        return redirect(url_for('main.manage_rooms'))

    if request.method == 'POST':
        hotel_id = request.form.get('hotel_id')
        capacity = request.form.get('capacity')
        viewtype = request.form.get('viewtype')
        extendable = request.form.get('extendable')
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
                'hotel_id': hotel_id,
                'capacity': capacity,
                'viewtype': viewtype,
                'extendable': extendable,
                'price': price,
                'status': status,
                'rid': room_id
            })
            db.session.commit()
            flash("✅ Room updated successfully.")
            return redirect(url_for('main.manage_rooms'))

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Failed to update room: {e}")

    return render_template("employee/room_form.html", mode='edit', room=room)


@bp.route('/employee/rooms/delete/<int:room_id>', methods=['POST'])
def delete_room(room_id):
    if 'user_type' not in session or session['user_type'] != 'employee' or session.get('position') != 'Manager':
        flash("Only managers can delete rooms.")
        return redirect(url_for('main.login'))

    try:
        db.session.execute(text("DELETE FROM Room WHERE RoomID = :rid"), {'rid': room_id})
        db.session.commit()
        flash("✅ Room deleted successfully.")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Failed to delete room: {e}")

    return redirect(url_for('main.manage_rooms'))
