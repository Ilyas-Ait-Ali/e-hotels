-- Trigger 1: Prevent booking a room with unresolved problems
DROP TRIGGER IF EXISTS trg_prevent_problematic_booking ON Booking;
DROP FUNCTION IF EXISTS prevent_problematic_booking CASCADE;

CREATE OR REPLACE FUNCTION prevent_problematic_booking() RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM RoomProblems
        WHERE HotelID = NEW.HotelID
          AND RoomID = NEW.RoomID
          AND Resolved = FALSE
    ) THEN
        RAISE EXCEPTION 'Cannot book room with unresolved problems.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_problematic_booking
BEFORE INSERT ON Booking
FOR EACH ROW
EXECUTE FUNCTION prevent_problematic_booking();

-- Trigger 2: Enforce max 5 active bookings per customer
DROP TRIGGER IF EXISTS trg_limit_active_bookings ON Booking;
DROP FUNCTION IF EXISTS limit_active_bookings CASCADE;

CREATE OR REPLACE FUNCTION limit_active_bookings() RETURNS TRIGGER AS $$
DECLARE
    active_bookings_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO active_bookings_count
    FROM Booking
    WHERE CustomerID = NEW.CustomerID
      AND Status IN ('Pending', 'Confirmed');

    IF active_bookings_count >= 5 THEN
        RAISE EXCEPTION 'Customer already has 5 or more active bookings.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_limit_active_bookings
BEFORE INSERT ON Booking
FOR EACH ROW
EXECUTE FUNCTION limit_active_bookings();

-- Trigger 3: Prevent cancellation within 24 hours of check-in
DROP TRIGGER IF EXISTS trg_prevent_late_cancellation ON Booking;
DROP FUNCTION IF EXISTS prevent_late_cancellation CASCADE;

CREATE OR REPLACE FUNCTION prevent_late_cancellation() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.Status = 'Cancelled' AND OLD.Status != 'Cancelled' AND
       NEW.CheckInDate - CURRENT_DATE <= 1 THEN
        RAISE EXCEPTION 'Cannot cancel a booking within 24 hours of check-in.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_late_cancellation
BEFORE UPDATE ON Booking
FOR EACH ROW
EXECUTE FUNCTION prevent_late_cancellation();

-- Trigger 4: Archive booking before deletion
DROP TRIGGER IF EXISTS trg_archive_booking ON Booking;
DROP FUNCTION IF EXISTS archive_booking CASCADE;

CREATE OR REPLACE FUNCTION archive_booking() RETURNS TRIGGER AS $$
DECLARE
    hotel_name TEXT;
    room_code TEXT;
BEGIN
    SELECT HotelName INTO hotel_name
    FROM Hotel WHERE HotelID = OLD.HotelID;

    room_code := 'Room ' || OLD.RoomID;

    INSERT INTO BookingArchive (
        BookingID, CustomerName, HotelName, RoomIdentifier, 
        BookingDate, CheckInDate, CheckOutDate, Status
    )
    SELECT
        OLD.BookingID,
        c.FullName,
        hotel_name,
        room_code,
        OLD.BookingDate,
        OLD.CheckInDate,
        OLD.CheckOutDate,
        OLD.Status
    FROM Customer c
    WHERE c.CustomerID = OLD.CustomerID;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_archive_booking
BEFORE DELETE ON Booking
FOR EACH ROW
EXECUTE FUNCTION archive_booking();

-- Trigger 5: Archive rental before deletion
DROP TRIGGER IF EXISTS trg_archive_rental ON Rental;
DROP FUNCTION IF EXISTS archive_rental CASCADE;

CREATE OR REPLACE FUNCTION archive_rental() RETURNS TRIGGER AS $$
DECLARE
    hotel_name TEXT;
    employee_name TEXT;
    customer_name TEXT;
    room_code TEXT;
BEGIN
    SELECT HotelName INTO hotel_name
    FROM Hotel WHERE HotelID = OLD.HotelID;

    SELECT FullName INTO employee_name
    FROM Employee WHERE EmployeeID = OLD.EmployeeID;

    SELECT FullName INTO customer_name
    FROM Customer WHERE CustomerID = OLD.CustomerID;

    room_code := 'Room ' || OLD.RoomID;

    INSERT INTO RentalArchive (
        RentalID, CustomerName, HotelName, RoomIdentifier, 
        EmployeeName, BookingID, CheckInDate, CheckOutDate, 
        Status, PaymentAmount, PaymentDate, PaymentMethod
    )
    VALUES (
        OLD.RentalID,
        customer_name,
        hotel_name,
        room_code,
        employee_name,
        OLD.BookingID,
        OLD.CheckInDate,
        OLD.CheckOutDate,
        OLD.Status,
        OLD.PaymentAmount,
        OLD.PaymentDate,
        OLD.PaymentMethod
    );

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_archive_rental
BEFORE DELETE ON Rental
FOR EACH ROW
EXECUTE FUNCTION archive_rental();

-- Trigger 6: Adjust room status based on booking updates (Confirmed → Occupied, Cancelled → Available)
DROP TRIGGER IF EXISTS trg_update_room_status_booking ON Booking;
DROP FUNCTION IF EXISTS update_room_status_booking CASCADE;

CREATE OR REPLACE FUNCTION update_room_status_booking() RETURNS TRIGGER AS $$
BEGIN
    -- If booking is confirmed, assume the room will be used → mark as 'Occupied'
    IF NEW.Status = 'Confirmed' AND OLD.Status != 'Confirmed' THEN
        UPDATE Room
        SET Status = 'Occupied'
        WHERE RoomID = NEW.RoomID AND HotelID = NEW.HotelID;

    -- If booking is cancelled, and it was previously confirmed or pending → make room 'Available'
    ELSIF NEW.Status = 'Cancelled' AND OLD.Status != 'Cancelled' THEN
        UPDATE Room
        SET Status = 'Available'
        WHERE RoomID = NEW.RoomID AND HotelID = NEW.HotelID;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_room_status_booking
AFTER UPDATE ON Booking
FOR EACH ROW
EXECUTE FUNCTION update_room_status_booking();

-- Trigger 7: Adjust room status based on rental progress
DROP TRIGGER IF EXISTS trg_update_room_status_rental ON Rental;
DROP FUNCTION IF EXISTS update_room_status_rental CASCADE;

CREATE OR REPLACE FUNCTION update_room_status_rental() RETURNS TRIGGER AS $$
BEGIN
    -- When rental becomes Ongoing
    IF NEW.Status = 'Ongoing' AND (TG_OP = 'INSERT' OR OLD.Status != 'Ongoing') THEN
        UPDATE Room
        SET Status = 'Occupied'
        WHERE RoomID = NEW.RoomID AND HotelID = NEW.HotelID;

    -- When rental is Completed
    ELSIF NEW.Status = 'Completed' AND (OLD.Status IS DISTINCT FROM 'Completed') THEN
        UPDATE Room
        SET Status = 'Available'
        WHERE RoomID = NEW.RoomID AND HotelID = NEW.HotelID;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_room_status_rental
AFTER INSERT OR UPDATE ON Rental
FOR EACH ROW
EXECUTE FUNCTION update_room_status_rental();

