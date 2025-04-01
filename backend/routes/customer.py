from flask import Blueprint, flash, render_template, request, redirect, url_for, session
from sqlalchemy import text
from datetime import date, datetime
from app import db


bp_customer = Blueprint('customer', __name__)

@bp_customer.route('/customer/search')
def search_rooms():
    if 'user_type' not in session or session['user_type'] != 'customer':
        return redirect(url_for('auth.login'))

    checkin = request.args.get("checkin")
    checkout = request.args.get("checkout")
    sort_by = request.args.get("sort")

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

    if request.args.get("minhotelrooms"):
        filters.append("h.Num_Rooms >= :minhotelrooms")
        params["minhotelrooms"] = request.args["minhotelrooms"]

    if request.args.get("viewtype"):
        filters.append("r.ViewType = :viewtype")
        params["viewtype"] = request.args["viewtype"]

    
    order_clause = "r.Price"
    if sort_by == "price_desc":
        order_clause = "r.Price DESC"
    elif sort_by == "rating":
        order_clause = "h.Rating DESC"
    elif sort_by == "rating_asc":
        order_clause = "h.Rating ASC"
    elif sort_by == "category":
        order_clause = "h.Category"
    elif sort_by == "capacity":
        order_clause = "CASE r.Capacity WHEN 'suite' THEN 5 WHEN 'family' THEN 4 WHEN 'triple' THEN 3 WHEN 'double' THEN 2 WHEN 'single' THEN 1 ELSE 6 END DESC"
    elif sort_by == "capacity_asc":
        order_clause = "CASE r.Capacity WHEN 'single' THEN 1 WHEN 'double' THEN 2 WHEN 'triple' THEN 3 WHEN 'family' THEN 4 WHEN 'suite' THEN 5 ELSE 6 END ASC"
    elif sort_by == "amenities":
        order_clause = """(
            SELECT COUNT(*) FROM RoomAmenities ra
            WHERE ra.HotelID = r.HotelID AND ra.RoomID = r.RoomID
        ) DESC"""
    elif sort_by == "amenities_least":
        order_clause = """(
            SELECT COUNT(*) FROM RoomAmenities ra
            WHERE ra.HotelID = r.HotelID AND ra.RoomID = r.RoomID
        ) ASC"""

    query = f"""
        SELECT r.*, h.HotelName, h.Address, hc.ChainName, h.Rating, h.Num_Rooms,
            (
                SELECT string_agg(ra.Amenity, ', ')
                FROM RoomAmenities ra
                WHERE ra.HotelID = r.HotelID AND ra.RoomID = r.RoomID
            ) AS amenities,
            (
                SELECT p.Problem
                FROM RoomProblems p
                WHERE p.HotelID = r.HotelID AND p.RoomID = r.RoomID AND p.Resolved = FALSE
                ORDER BY p.ReportDate DESC
                LIMIT 1
            ) AS problem_cause
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
        ORDER BY {order_clause}
    """
    results = db.session.execute(text(query), params).fetchall()
    return render_template("customer/search.html", rooms=results, checkin=checkin, checkout=checkout)






@bp_customer.route('/customer/bookings')
def my_bookings():
    if 'user_type' not in session or session['user_type'] != 'customer':
        return redirect(url_for('auth.login'))

    customer_id = session['user_id']
    bookings = db.session.execute(text("""
        SELECT b.*, h.HotelName, h.Address
        FROM Booking b
        JOIN Hotel h ON b.HotelID = h.HotelID
        WHERE b.CustomerID = :cid
        ORDER BY 
            CASE WHEN b.Status = 'Cancelled' THEN 1 ELSE 0 END,
            b.CheckInDate
    """), {'cid': customer_id}).fetchall()

    return render_template("customer/my_bookings.html", bookings=bookings, current_date=date.today())



@bp_customer.route('/customer/book', methods=['POST'])
def book_room():
    if 'user_type' not in session or session['user_type'] != 'customer':
        flash("You must be logged in to book a room.")
        return redirect(url_for('auth.login'))

    room_id = request.form.get("room_id")
    hotel_id = request.form.get("hotel_id")
    checkin = request.form.get("checkin")
    checkout = request.form.get("checkout")
    customer_id = session['user_id']
    today = date.today()

    try:
        
        db.session.execute(text("""
            INSERT INTO Booking (CustomerID, HotelID, RoomID, BookingDate, CheckInDate, CheckOutDate, Status)
            VALUES (:cid, :hid, :rid, :bdate, :checkin, :checkout, 'Pending')
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
        error_msg = str(e).lower()
        if 'unresolved problems' in error_msg:
            flash("❌ Cannot book this room because it has unresolved issues.")
        elif '5 or more active bookings' in error_msg:
            flash("❌ You already have 5 or more active bookings.")
        else:
            flash(f"❌ Booking failed: {e}")
        return redirect(url_for('customer.search_rooms'))


@bp_customer.route('/customer/cancel-booking', methods=['POST'])
def cancel_booking():
    if 'user_type' not in session or session['user_type'] != 'customer':
        flash("You must be logged in to cancel a booking.")
        return redirect(url_for('customer.login'))

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
        error_msg = str(e).lower()
        if 'cannot cancel' in error_msg:
            flash("❌ You cannot cancel a booking on the day of check-in.")
        else:
            flash(f"❌ Failed to cancel booking: {e}")

    return redirect(url_for('customer.my_bookings'))

@bp_customer.route('/customer/rentings')
def my_rentings():
    if 'user_type' not in session or session['user_type'] != 'customer':
        return redirect(url_for('auth.login'))

    customer_id = session['user_id']
    rentings = db.session.execute(text("""
        SELECT r.*, h.HotelName, h.Address
        FROM Rental r
        JOIN Hotel h ON r.HotelID = h.HotelID
        WHERE r.CustomerID = :cid
        ORDER BY r.CheckInDate DESC
    """), {'cid': customer_id}).fetchall()

    return render_template("customer/my_rentings.html", rentings=rentings)


@bp_customer.route('/customer/hotels')
def view_all_hotels():
    if 'user_type' not in session or session['user_type'] != 'customer':
        return redirect(url_for('auth.login'))

    sort = request.args.get('sort', 'rating_desc')

    sort_map = {
        'name_asc': 'h.HotelName ASC',
        'name_desc': 'h.HotelName DESC',
        'rating_asc': 'h.Rating ASC',
        'rating_desc': 'h.Rating DESC',
        'chain': 'hc.ChainName ASC',
        'category': 'h.Category ASC'
    }

    order_by = sort_map.get(sort, 'h.Rating DESC')

    query = text(f"""
        SELECT h.HotelID, h.HotelName, h.Address, h.Category, h.Rating, hc.ChainName
        FROM Hotel h
        JOIN HotelChain hc ON h.HotelChainID = hc.HotelChainID
        ORDER BY {order_by}
    """)
    hotels = db.session.execute(query).fetchall()

    return render_template('customer/view_hotels.html', hotels=hotels, sort=sort)

