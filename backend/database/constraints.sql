-- HotelChain Constraints
ALTER TABLE HotelChain
    ADD CONSTRAINT CHK_HotelChain_NumHotels CHECK (Num_Hotels > 0);

-- Hotel Constraints
ALTER TABLE Hotel
    ADD CONSTRAINT CHK_Hotel_Rating CHECK (Rating BETWEEN 1 AND 5),
    ADD CONSTRAINT CHK_Hotel_NumRooms CHECK (Num_Rooms > 0),
    ADD CONSTRAINT CHK_Hotel_Category CHECK (Category IN ('Luxury', 'Resort', 'Boutique')),
    ADD CONSTRAINT UNQ_Manager_Per_Hotel UNIQUE (HotelID, ManagerID);

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

-- Room Constraints
ALTER TABLE Room
    ADD CONSTRAINT CHK_Room_Price CHECK (Price > 0),
    ADD CONSTRAINT CHK_Room_Capacity CHECK (Capacity IN ('single', 'double', 'triple', 'family', 'suite')),    
    ADD CONSTRAINT CHK_Room_ViewType CHECK (ViewType IN ('sea_view', 'mountain_view', 'both', 'none')),
    ADD CONSTRAINT CHK_Room_Status CHECK (Status IN ('Available', 'Booked', 'Occupied', 'Out-of-Order'));

-- RoomProblems Constraints
ALTER TABLE RoomProblems
    ADD CONSTRAINT CHK_RoomProblem_NotNull CHECK (Problem IS NOT NULL AND LENGTH(TRIM(Problem)) > 0),
    ADD CONSTRAINT CHK_ReportDate_NotFuture CHECK (ReportDate <= CURRENT_DATE),
    ADD CONSTRAINT CHK_Resolved_Logic CHECK (Resolved IN (TRUE, FALSE));
    

-- Customer Constraints
ALTER TABLE Customer
    ADD CONSTRAINT CHK_Customer_IDNumber CHECK (LENGTH(IDNumber) > 5),
    ADD CONSTRAINT CHK_Customer_RegistrationDate CHECK (RegistrationDate <= CURRENT_DATE),
    ADD CONSTRAINT CHK_Customer_IDType CHECK (IDType IN ('SSN', 'SIN', 'Driving License', 'Passport'));

-- Booking Constraints
ALTER TABLE Booking
    ADD CONSTRAINT CHK_Booking_Status CHECK (Status IN ('Pending', 'Checked-in', 'Cancelled')),
    ADD CONSTRAINT CHK_Booking_Dates_If_Rented CHECK ((Status = 'Checked-in' AND CheckInDate IS NOT NULL AND CheckOutDate IS NOT NULL) OR (Status != 'Checked-in')),
    ADD CONSTRAINT CHK_Booking_Date_Order CHECK (CheckOutDate > CheckInDate),
    ADD CONSTRAINT CHK_Booking_BookingDate CHECK (BookingDate <= CheckInDate);

-- Rental Constraints
ALTER TABLE Rental
    ADD CONSTRAINT CHK_Rental_Status CHECK (Status IN ('Ongoing', 'Completed')),
    ADD CONSTRAINT CHK_Rental_Date_Order CHECK (CheckOutDate >= CheckInDate),
    ADD CONSTRAINT CHK_Rental_Payment_If_Completed CHECK ((Status = 'Completed' AND PaymentDate IS NOT NULL AND PaymentMethod IS NOT NULL) OR (Status != 'Completed'));


