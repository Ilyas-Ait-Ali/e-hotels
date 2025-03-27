-- Hotel Chain Table
CREATE TABLE HotelChain (
    HotelChainID SERIAL PRIMARY KEY,
    ChainName VARCHAR(255) NOT NULL,
    CentralOfficeAddress VARCHAR(255) NOT NULL,
    Num_Hotels INTEGER NOT NULL
);

-- Hotel Chain Email Addresses (multivalued attribute)
CREATE TABLE HCEmailAddresses (
    HotelChainID INTEGER NOT NULL,
    ChainEmail VARCHAR(100) NOT NULL UNIQUE,
    PRIMARY KEY (HotelChainID, ChainEmail),
    FOREIGN KEY (HotelChainID) REFERENCES HotelChain(HotelChainID) ON DELETE CASCADE
);

-- Hotel Chain Phone Numbers (multivalued attribute)
CREATE TABLE HCPhoneNumbers (
    HotelChainID INTEGER NOT NULL,
    ChainPhoneNumber VARCHAR(15) NOT NULL UNIQUE,
    PRIMARY KEY (HotelChainID, ChainPhoneNumber),
    FOREIGN KEY (HotelChainID) REFERENCES HotelChain(HotelChainID) ON DELETE CASCADE
);

-- Hotel Table
CREATE TABLE Hotel (
    HotelID SERIAL PRIMARY KEY,
    HotelChainID INTEGER NOT NULL,
    HotelName VARCHAR(255) NOT NULL,
    Rating INTEGER NOT NULL,
    Address VARCHAR(255) NOT NULL,
    Category VARCHAR(50) NOT NULL,
    Num_Rooms INTEGER NOT NULL,
    ManagerID INTEGER,
    FOREIGN KEY (HotelChainID) REFERENCES HotelChain(HotelChainID) ON DELETE CASCADE
);

-- Hotel Email Addresses (multivalued attribute)
CREATE TABLE HEmailAddresses (
    HotelID INTEGER NOT NULL,
    HotelEmail VARCHAR(100) UNIQUE NOT NULL,
    PRIMARY KEY (HotelID, HotelEmail),
    FOREIGN KEY (HotelID) REFERENCES Hotel(HotelID) ON DELETE CASCADE
);

-- Hotel Phone Numbers (multivalued attribute)
CREATE TABLE HPhoneNumbers (
    HotelID INTEGER NOT NULL,
    HotelPhoneNumber VARCHAR(15) NOT NULL UNIQUE,
    PRIMARY KEY (HotelID, HotelPhoneNumber),
    FOREIGN KEY (HotelID) REFERENCES Hotel(HotelID) ON DELETE CASCADE
);

-- Employee Table
CREATE TABLE Employee (
    EmployeeID SERIAL PRIMARY KEY,
    HotelID INTEGER,
    FullName VARCHAR(100) NOT NULL,
    Address VARCHAR(255) NOT NULL,
    SSN VARCHAR(20) NOT NULL UNIQUE,
    Position VARCHAR(50) NOT NULL,
    FOREIGN KEY (HotelID) REFERENCES Hotel(HotelID) ON DELETE SET NULL
);

-- Add ManagerID foreign key (after Employee exists)
ALTER TABLE Hotel ADD CONSTRAINT FK_Hotel_Manager 
    FOREIGN KEY (ManagerID) REFERENCES Employee(EmployeeID);

-- Room Table
CREATE TABLE Room (
    RoomID INTEGER NOT NULL,
    HotelID INTEGER NOT NULL,
    Price DECIMAL(10, 2) NOT NULL,
    Capacity VARCHAR(20) NOT NULL,
    ViewType VARCHAR(20) NOT NULL,
    Extendable BOOLEAN NOT NULL,
    Status VARCHAR(20) NOT NULL,
    PRIMARY KEY (HotelID, RoomID),
    FOREIGN KEY (HotelID) REFERENCES Hotel(HotelID) ON DELETE CASCADE
);

-- Room Amenities (multivalued attribute)
CREATE TABLE RoomAmenities (
    HotelID INTEGER NOT NULL,
    RoomID INTEGER NOT NULL,
    Amenity VARCHAR(100) NOT NULL,
    PRIMARY KEY (HotelID, RoomID, Amenity),
    FOREIGN KEY (HotelID, RoomID) REFERENCES Room(HotelID, RoomID) ON DELETE CASCADE
);

-- Room Problems (multivalued attribute)
CREATE TABLE RoomProblems (
    HotelID INTEGER NOT NULL,
    RoomID INTEGER NOT NULL,
    Problem VARCHAR(255) NOT NULL,
    ReportDate DATE NOT NULL,
    Resolved BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (HotelID, RoomID, Problem),
    FOREIGN KEY (HotelID, RoomID) REFERENCES Room(HotelID, RoomID) ON DELETE CASCADE
);

-- Customer Table
CREATE TABLE Customer (
    CustomerID SERIAL PRIMARY KEY,
    FullName VARCHAR(100) NOT NULL,
    Address VARCHAR(255) NOT NULL,
    IDType VARCHAR(50) NOT NULL,
    IDNumber VARCHAR(50) NOT NULL UNIQUE,
    RegistrationDate DATE NOT NULL
);

-- Booking Table
CREATE TABLE Booking (
    BookingID SERIAL PRIMARY KEY,
    CustomerID INTEGER NOT NULL,
    HotelID INTEGER NOT NULL,
    RoomID INTEGER NOT NULL,
    BookingDate DATE NOT NULL,
    CheckInDate DATE NOT NULL,
    CheckOutDate DATE NOT NULL,
    Status VARCHAR(20) NOT NULL,
    FOREIGN KEY (CustomerID) REFERENCES Customer(CustomerID) ON DELETE CASCADE,
    FOREIGN KEY (HotelID, RoomID) REFERENCES Room(HotelID, RoomID) ON DELETE CASCADE
);

-- Rental Table
CREATE TABLE Rental (
    RentalID SERIAL PRIMARY KEY,
    CustomerID INTEGER NOT NULL,
    HotelID INTEGER NOT NULL,
    RoomID INTEGER NOT NULL,
    EmployeeID INTEGER NOT NULL,
    BookingID INTEGER,
    CheckInDate DATE NOT NULL,
    CheckOutDate DATE NOT NULL,
    Status VARCHAR(20) NOT NULL,
    PaymentAmount DECIMAL(10, 2) NOT NULL,
    PaymentDate DATE,
    PaymentMethod VARCHAR(50),
    FOREIGN KEY (CustomerID) REFERENCES Customer(CustomerID) ON DELETE CASCADE,
    FOREIGN KEY (HotelID, RoomID) REFERENCES Room(HotelID, RoomID) ON DELETE CASCADE,
    FOREIGN KEY (EmployeeID) REFERENCES Employee(EmployeeID) ON DELETE SET NULL,
    FOREIGN KEY (BookingID) REFERENCES Booking(BookingID) ON DELETE CASCADE
);

-- Booking Archive Table
CREATE TABLE BookingArchive (
    BookingID INTEGER PRIMARY KEY,
    CustomerName VARCHAR(100) NOT NULL,
    HotelName VARCHAR(100) NOT NULL,
    RoomIdentifier VARCHAR(20) NOT NULL,
    BookingDate DATE NOT NULL,
    CheckInDate DATE NOT NULL,
    CheckOutDate DATE NOT NULL,
    Status VARCHAR(20) NOT NULL,
    ArchiveDate DATE NOT NULL DEFAULT CURRENT_DATE
);

-- Rental Archive Table
CREATE TABLE RentalArchive (
    RentalID INTEGER PRIMARY KEY,
    CustomerName VARCHAR(100) NOT NULL,
    HotelName VARCHAR(100) NOT NULL,
    RoomIdentifier VARCHAR(20) NOT NULL,
    EmployeeName VARCHAR(100),
    BookingID INTEGER,
    CheckInDate DATE NOT NULL,
    CheckOutDate DATE NOT NULL,
    Status VARCHAR(20) NOT NULL,
    PaymentAmount DECIMAL(10, 2) NOT NULL,
    PaymentDate DATE,
    PaymentMethod VARCHAR(50),
    ArchiveDate DATE NOT NULL DEFAULT CURRENT_DATE
);
