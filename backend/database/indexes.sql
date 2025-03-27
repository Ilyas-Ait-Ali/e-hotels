-- Index 1: Quickly find all bookings for a given customer (used in trigger & views)
DROP INDEX IF EXISTS idx_booking_customer;
CREATE INDEX idx_booking_customer ON Booking(CustomerID);

-- Index 2: Speed up room status filtering (e.g., 'Available', 'Occupied') for views & triggers
DROP INDEX IF EXISTS idx_room_status;
CREATE INDEX idx_room_status ON Room(HotelID, Status);

-- Index 3: Optimize booking cancellation trigger (checks proximity to CheckInDate)
DROP INDEX IF EXISTS idx_booking_checkin;
CREATE INDEX idx_booking_checkin ON Booking(CheckInDate);

-- Index 4: Speed up finding unresolved room problems (used in Trigger 1)
DROP INDEX IF EXISTS idx_room_problems;
CREATE INDEX idx_room_problems ON RoomProblems(HotelID, RoomID, Resolved);

-- Index 5: Help with hotel filtering/grouping by address (used in views per area)
DROP INDEX IF EXISTS idx_hotel_address;
CREATE INDEX idx_hotel_address ON Hotel(Address);

-- Index 6: Speed up employee filtering by hotel and position
DROP INDEX IF EXISTS idx_employee_hotel_position;
CREATE INDEX idx_employee_hotel_position ON Employee(HotelID, Position);
