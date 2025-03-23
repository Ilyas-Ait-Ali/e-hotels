-- Hotel Ratings
ALTER TABLE Hotel
    ADD CONSTRAINT CHK_Hotel_Rating CHECK (Rating BETWEEN 1 AND 5),
    ADD CONSTRAINT CHK_Hotel_NumRooms CHECK (Num_Rooms > 0);

-- Room Constraints
ALTER TABLE Room
    ADD CONSTRAINT CHK_Room_Price CHECK (Price > 0),
    ADD CONSTRAINT CHK_Room_Capacity CHECK (Capacity IN ('single', 'double', 'suite', 'family')),
    ADD CONSTRAINT CHK_Room_ViewType CHECK (ViewType IN ('sea_view', 'mountain_view', 'both', 'none'));
    ALTER TABLE Room ADD CONSTRAINT CHK_Room_Status CHECK (Status IN ('Available', 'Booked', 'Occupied', 'Out-of-Order'));

-- HotelChain Constraints
ALTER TABLE HotelChain
    ADD CONSTRAINT CHK_HotelChain_NumHotels CHECK (Num_Hotels > 0);

-- Phone Number Format
ALTER TABLE HCPhoneNumbers
    ADD CONSTRAINT CHK_HC_PhoneNumber CHECK (ChainPhoneNumber ~ '^[0-9]{7,15}$');

ALTER TABLE HPhoneNumbers
    ADD CONSTRAINT CHK_H_PhoneNumber CHECK (HotelPhoneNumber ~ '^[0-9]{7,15}$');

-- Email Format
ALTER TABLE HCEmailAddresses
    ADD CONSTRAINT CHK_HC_Email CHECK (ChainEmail ~ '^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4}$');

ALTER TABLE HEmailAddresses
    ADD CONSTRAINT CHK_H_Email CHECK (HotelEmail ~ '^[A-Za-z0-9._%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4}$');

-- Booking Constraints
ALTER TABLE Booking
    ADD CONSTRAINT CHK_Booking_Status CHECK (Status IN ('Pending', 'Confirmed', 'Cancelled', 'Completed')),
    ADD CONSTRAINT CHK_Booking_Date_Order CHECK (CheckOutDate > CheckInDate),
    ADD CONSTRAINT CHK_Booking_BookingDate CHECK (BookingDate <= CheckInDate);

-- Rental Constraints
ALTER TABLE Rental
    ADD CONSTRAINT CHK_Rental_Status CHECK (Status IN ('Ongoing', 'Completed')),
    ADD CONSTRAINT CHK_Rental_Date_Order CHECK (CheckOutDate >= CheckInDate);

-- Customer Constraints
ALTER TABLE Customer
    ADD CONSTRAINT CHK_Customer_IDNumber CHECK (LENGTH(IDNumber) > 5),
    ADD CONSTRAINT CHK_Customer_RegistrationDate CHECK (RegistrationDate <= CURRENT_DATE),
    ADD CONSTRAINT CHK_Customer_IDType CHECK (IDType IN ('SSN', 'SIN', 'Driving License', 'Passport'));
