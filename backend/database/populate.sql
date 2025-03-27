-- Populate HotelChain with realistic names and addresses
INSERT INTO HotelChain (ChainName, CentralOfficeAddress, Num_Hotels)
VALUES 
    ('Luxury Collection', '123 Fifth Avenue, New York, NY 10001', 8),
    ('Comfort Suites', '456 Michigan Ave, Chicago, IL 60601', 8),
    ('Premier Inn', '789 Market Street, San Francisco, CA 94105', 8),
    ('Grand Resorts', '321 Collins Avenue, Miami, FL 33139', 8),
    ('Metropolitan Hotels', '654 Pike Street, Seattle, WA 98101', 8);

-- Populate Chain Contact Information using arrays and loops
DO $$
DECLARE
    chain_id INTEGER;
    domains TEXT[] := ARRAY['hotels.com', 'resorts.com', 'stays.net', 'lodging.com', 'hospitality.com'];
BEGIN
    FOR chain_id IN 1..5 LOOP
        -- Multiple emails per chain
        INSERT INTO HCEmailAddresses (HotelChainID, ChainEmail) VALUES
            (chain_id, 'info' || chain_id || '@' || domains[chain_id]),
            (chain_id, 'reservations' || chain_id || '@' || domains[chain_id]),
            (chain_id, 'support' || chain_id || '@' || domains[chain_id]);

        -- Multiple phone numbers per chain
        INSERT INTO HCPhoneNumbers (HotelChainID, ChainPhoneNumber) VALUES
            (chain_id, '1' || LPAD(chain_id::TEXT, 2, '0') || '5550100'),
            (chain_id, '1' || LPAD(chain_id::TEXT, 2, '0') || '5550200');
    END LOOP;
END $$;

DO $$
DECLARE
    chain_id INTEGER;
    hotel_id INTEGER := 1;

    city_map TEXT[][][] := ARRAY[
        -- Chain 1: Repeat New York
        ARRAY[['New York','NY'], ['New York','NY'], ['San Francisco','CA'], ['Miami','FL'], ['Los Angeles','CA'], ['Boston','MA'], ['Seattle','WA'], ['Las Vegas','NV']],
        -- Chain 2: Repeat San Francisco
        ARRAY[['San Francisco','CA'], ['San Francisco','CA'], ['Miami','FL'], ['Los Angeles','CA'], ['Boston','MA'], ['Seattle','WA'], ['Las Vegas','NV'], ['New York','NY']],
        -- Chain 3: Repeat Miami
        ARRAY[['Miami','FL'], ['Miami','FL'], ['Los Angeles','CA'], ['Boston','MA'], ['Seattle','WA'], ['Las Vegas','NV'], ['New York','NY'], ['Chicago','IL']],
        -- Chain 4: Repeat Los Angeles
        ARRAY[['Los Angeles','CA'], ['Los Angeles','CA'], ['Boston','MA'], ['Seattle','WA'], ['Las Vegas','NV'], ['New York','NY'], ['Chicago','IL'], ['San Francisco','CA']],
        -- Chain 5: Repeat Chicago
        ARRAY[['Chicago','IL'], ['Chicago','IL'], ['Seattle','WA'], ['Las Vegas','NV'], ['New York','NY'], ['San Francisco','CA'], ['Miami','FL'], ['Boston','MA']]
    ];

    descriptors TEXT[][] := ARRAY[
        ['Velvet Vista', 'Crystal Bay', 'Twilight Manor', 'Golden Horizon', 'Summit Suites', 'Emerald Breeze', 'Oceanfront Retreat', 'Royal Serenity'],
        ['Tranquil Bloom', 'Silver Cove', 'Cozy Nest', 'Maple Grove', 'Serene Hillside', 'Blossom View', 'Sunny Vale', 'Moonlight Escape'],
        ['Dreamy Harbor', 'Whispering Pines', 'Azure Palace', 'Peaceful Haven', 'Sunrise Garden', 'Quiet Mirage', 'Rosewood Lodge', 'Harmony Stay'],
        ['Radiant Oasis', 'Blissful Stays', 'Majestic Trails', 'Grand Solace', 'Crescent Lodge', 'Tranquil Path', 'Golden Escape', 'Wanderer’s Rest'],
        ['Urban Bloom', 'Metro Luxe', 'Skyline Inn', 'Elegant Dwell', 'Urban Solstice', 'Quiet Metro', 'Luxe District', 'Harbor Light']
    ];

    categories TEXT[] := ARRAY['Luxury', 'Resort', 'Boutique'];
    current_city TEXT;
    current_state TEXT;
    chain_prefix TEXT;
BEGIN
    FOR chain_id IN 1..5 LOOP
        -- Get prefix (first word of the chain name)
        SELECT SPLIT_PART(ChainName, ' ', 1) INTO chain_prefix
        FROM HotelChain WHERE HotelChainID = chain_id;

        FOR i IN 1..8 LOOP
            -- Get city/state from preplanned city map
            current_city := city_map[chain_id][i][1];
            current_state := city_map[chain_id][i][2];

            -- Insert the hotel
            INSERT INTO Hotel (
                HotelChainID, HotelName, Rating, Address, Category, Num_Rooms
            ) VALUES (
                chain_id,
                chain_prefix || ' ' || descriptors[chain_id][i],
                GREATEST(3, LEAST(5, 3 + (chain_id + i) % 3)),
                (100 + i)::TEXT || ' ' || current_city || ' Street, ' || current_city || ', ' || current_state,
                categories[(i - 1) % 3 + 1],
                5
            );

            -- Insert contact info
            INSERT INTO HEmailAddresses (HotelID, HotelEmail)
            VALUES (hotel_id, LOWER('hotel' || hotel_id || '@' || REPLACE(current_city, ' ', '-') || '.example.com'));

            INSERT INTO HPhoneNumbers (HotelID, HotelPhoneNumber)
            VALUES (hotel_id, '1' || LPAD(hotel_id::TEXT, 2, '0') || '5551234');

            hotel_id := hotel_id + 1;
        END LOOP;
    END LOOP;
END $$;

-- Populate Customers
INSERT INTO Customer (FullName, Address, IDType, IDNumber, RegistrationDate)
VALUES
    ('John Doe', '123 Elm Street, Springfield, IL 62704', 'Passport', 'A12345678', '2025-01-15'),
    ('Jane Smith', '456 Oak Avenue, Denver, CO 80203', 'Driving License', 'D98765432', '2025-02-10'),
    ('Alice Johnson', '789 Pine Road, Austin, TX 73301', 'SSN', '123-45-6789', '2025-03-01'),
    ('Bob Brown', '321 Maple Lane, Seattle, WA 98101', 'SIN', '987-65-4321', '2025-03-15'),
    ('Charlie Davis', '654 Cedar Street, Miami, FL 33139', 'Passport', 'B87654321', '2025-03-20');

-- Populate Employees for All Hotels
DO $$
DECLARE
    hotel_rec RECORD;
    emp_count INTEGER := 0;
    roles TEXT[] := ARRAY['Manager', 'Receptionist', 'Housekeeper'];
    first_names TEXT[] := ARRAY[
        'Alice', 'Bob', 'Cathy', 'Daniel', 'Eva', 'Frank', 'Grace', 'Hank', 'Ivy',
        'Jack', 'Karen', 'Leo', 'Mona', 'Nina', 'Oscar', 'Paul', 'Quinn', 'Rachel',
        'Steve', 'Tina', 'Uma', 'Victor', 'Wendy', 'Xander', 'Yasmin', 'Zane', 'Abby'
    ];
    last_names TEXT[] := ARRAY[
        'Smith', 'Johnson', 'Brown', 'Taylor', 'Anderson', 'Lee', 'Martin', 'Clark',
        'Hall', 'Lewis', 'Young', 'Walker', 'Scott', 'Green', 'Adams', 'Baker', 'Gray',
        'Cox', 'Diaz', 'Hughes', 'Morris', 'Flores', 'Price', 'Reed', 'Bell', 'Ward'
    ];
BEGIN
    FOR hotel_rec IN SELECT HotelID, Address FROM Hotel LOOP
        FOR i IN 1..3 LOOP
            emp_count := emp_count + 1;

            INSERT INTO Employee (HotelID, FullName, Address, SSN, Position)
            VALUES (
                hotel_rec.HotelID,
                first_names[(emp_count % array_length(first_names, 1)) + 1] || ' ' || last_names[(emp_count % array_length(last_names, 1)) + 1],
                'Apt ' || (10 + i) || ', ' || hotel_rec.Address,
                LPAD(emp_count::TEXT, 3, '0') || '-' || LPAD((emp_count * 2)::TEXT, 2, '0') || '-' || LPAD((emp_count * 3)::TEXT, 4, '0'),
                roles[i]
            );
        END LOOP;
    END LOOP;
END $$;

UPDATE Hotel
SET ManagerID = e.EmployeeID
FROM Employee e
WHERE Hotel.HotelID = e.HotelID AND e.Position = 'Manager';

-- Populate Rooms with smart pricing and features
DO $$
DECLARE
    hotel_id INTEGER;
    base_price DECIMAL;
    capacities TEXT[] := ARRAY['single', 'double', 'triple', 'family', 'suite'];
    views TEXT[] := ARRAY['sea_view', 'mountain_view', 'both', 'none'];
    cap TEXT;
    i INTEGER;
    status_order TEXT[][];
BEGIN
    -- Define different rotation patterns for status to alternate per hotel
    status_order := ARRAY[
        ARRAY['Available', 'Booked', 'Occupied', 'Out-of-Order', 'Available'],
        ARRAY['Booked', 'Occupied', 'Out-of-Order', 'Available', 'Booked'],
        ARRAY['Occupied', 'Out-of-Order', 'Available', 'Booked', 'Occupied'],
        ARRAY['Out-of-Order', 'Available', 'Booked', 'Occupied', 'Out-of-Order']
    ];

    FOR hotel_id IN 1..40 LOOP
        -- Get base price from hotel rating
        SELECT CASE Rating 
            WHEN 3 THEN 100
            WHEN 4 THEN 150
            WHEN 5 THEN 200
        END INTO base_price
        FROM Hotel WHERE HotelID = hotel_id;

        FOR i IN 1..5 LOOP
            cap := capacities[i];

            INSERT INTO Room (RoomID, HotelID, Price, Capacity, ViewType, Extendable, Status)
            VALUES (
                100 + i, -- Room IDs: 101 to 105
                hotel_id,
                base_price * (1 + i * 0.2),
                cap,
                views[(hotel_id + i) % 4 + 1],
                CASE WHEN cap = 'single' THEN FALSE ELSE TRUE END,
                status_order[(hotel_id % 4) + 1][i] -- Pick rotating status pattern
            );
        END LOOP;
    END LOOP;
END $$;

-- Populate Room Amenities
DO $$
DECLARE
    hotel_id INTEGER;
    room_id INTEGER;
    capacity TEXT;
    amenities TEXT[];
BEGIN
    FOR hotel_id IN 1..40 LOOP
        FOR room_id IN 101..105 LOOP
            -- Determine room capacity based on room_id
            capacity := CASE room_id % 5
                WHEN 1 THEN 'single'
                WHEN 2 THEN 'double'
                WHEN 3 THEN 'triple'
                WHEN 4 THEN 'family'
                WHEN 0 THEN 'suite'
            END;
            -- Assign amenities based on room capacity
            amenities := CASE capacity
                WHEN 'single' THEN ARRAY['WiFi', 'TV']
                WHEN 'double' THEN ARRAY['WiFi', 'TV', 'Microwave']
                WHEN 'triple' THEN ARRAY['WiFi', 'TV', 'Microwave', 'Coffee Maker']
                WHEN 'family' THEN ARRAY['WiFi', 'TV', 'Microwave', 'Coffee Maker', 'Bath Tub']
                WHEN 'suite' THEN ARRAY['WiFi', 'TV', 'Microwave', 'Coffee Maker', 'Bath Tub', 'Safe']
            END;
            -- Insert amenities for the room
            FOR i IN 1..array_length(amenities, 1) LOOP
                INSERT INTO RoomAmenities (HotelID, RoomID, Amenity)
                VALUES (hotel_id, room_id, amenities[i]);
            END LOOP;
        END LOOP;
    END LOOP;
END $$;

-- Populate Room Problems for Out-of-Order Rooms Only, based on room type and amenities
DO $$
DECLARE
    hotel_id INTEGER;
    room_rec RECORD;
    room_capacity TEXT;
    problem_options TEXT[];
    resolved_flag BOOLEAN := FALSE;
    report_offset INTEGER;
    base_date DATE := DATE '2025-03-01';  -- fixed and deterministic base date
BEGIN
    FOR hotel_id IN 1..40 LOOP
        FOR room_rec IN
            SELECT RoomID, Capacity FROM Room
            WHERE HotelID = hotel_id AND Status = 'Out-of-Order'
        LOOP
            room_capacity := room_rec.Capacity;

            -- Problem options based on room capacity (reflecting amenities)
            problem_options := CASE room_capacity
                WHEN 'single' THEN ARRAY[
                    'TV not working',
                    'Remote control missing',
                    'WiFi connectivity intermittent'
                ]
                WHEN 'double' THEN ARRAY[
                    'Smart lock malfunction',
                    'TV not working',
                    'Remote control missing',
                    'WiFi connectivity intermittent'
                ]
                WHEN 'triple' THEN ARRAY[
                    'Smart lock malfunction',
                    'TV not working',
                    'Remote control missing',
                    'Coffee machine not working',
                    'WiFi connectivity intermittent'
                ]
                WHEN 'family' THEN ARRAY[
                    'Smart lock malfunction',
                    'TV not working',
                    'Coffee machine not working',
                    'WiFi connectivity intermittent',
                    'Hot water not working',
                    'Guest amenities not replenished'
                ]
                WHEN 'suite' THEN ARRAY[
                    'Smart lock malfunction',
                    'TV not working',
                    'Coffee machine not working',
                    'WiFi connectivity intermittent',
                    'Hot water not working',
                    'Guest amenities not replenished',
                    'Balcony door not closing properly'
                ]
            END;

            -- Deterministic report date
            report_offset := ((hotel_id * 3 + room_rec.RoomID * 7) % 5);

            -- Insert Room Problem
            INSERT INTO RoomProblems (HotelID, RoomID, Problem, ReportDate, Resolved)
            VALUES (
                hotel_id,
                room_rec.RoomID,
                problem_options[(hotel_id + room_rec.RoomID) % array_length(problem_options, 1) + 1],
                base_date - report_offset,
                resolved_flag
            );

            resolved_flag := NOT resolved_flag;
        END LOOP;
    END LOOP;
END $$;

-- Populate Bookings for Customer 1 Only
DO $$
DECLARE
    booking_id INTEGER := 1;
    hotel_id INTEGER := 1; -- Assign all bookings to Hotel 1 for simplicity
    room_id INTEGER := 101; -- Assign all bookings to Room 1 for simplicity
    booking_date DATE;
    check_in_date DATE;
    check_out_date DATE;
BEGIN
    FOR i IN 1..3 LOOP -- Create 3 bookings for Customer 1
        booking_date := '2025-03-01'::DATE + (i - 1) * INTERVAL '2 days';
        check_in_date := booking_date + INTERVAL '1 day';
        check_out_date := check_in_date + INTERVAL '3 days';

        INSERT INTO Booking (CustomerID, HotelID, RoomID, BookingDate, CheckInDate, CheckOutDate, Status)
        VALUES (
            1, -- Customer 1
            hotel_id,
            room_id,
            booking_date,
            check_in_date,
            check_out_date,
            CASE 
                WHEN booking_id % 2 = 0 THEN 'Confirmed'
                ELSE 'Pending'
            END
        );

        booking_id := booking_id + 1;
    END LOOP;
END $$;

-- Populate Rentals for Customer 1 Only
DO $$
DECLARE
    rental_id INTEGER := 1;
    hotel_id INTEGER := 1; -- Assign all rentals to Hotel 1 for simplicity
    room_id INTEGER := 101; -- Assign all rentals to Room 1 for simplicity
    employee_id INTEGER := 1; -- Assign all rentals to Employee 1 for simplicity
    booking_id INTEGER;
    check_in_date DATE;
    check_out_date DATE;
BEGIN
    FOR i IN 1..3 LOOP -- Create 3 rentals for Customer 1
        booking_id := rental_id; -- Link rental to booking
        check_in_date := '2025-03-01'::DATE + (i - 1) * INTERVAL '3 days';
        check_out_date := check_in_date + INTERVAL '2 days';

        INSERT INTO Rental (CustomerID, HotelID, RoomID, EmployeeID, BookingID, CheckInDate, CheckOutDate, Status, PaymentAmount, PaymentDate, PaymentMethod)
        VALUES (
            1, -- Customer 1
            hotel_id,
            room_id,
            employee_id,
            booking_id,
            check_in_date,
            check_out_date,
            CASE 
                WHEN rental_id % 2 = 0 THEN 'Completed'
                ELSE 'Ongoing'
            END,
            500 + (rental_id * 10), -- Deterministic payment amount
            check_out_date,
            CASE 
                WHEN rental_id % 2 = 0 THEN 'Credit Card'
                ELSE 'Cash'
            END
        );

        rental_id := rental_id + 1;
    END LOOP;
END $$;