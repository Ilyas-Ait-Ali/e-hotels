-- Aggregation Query 1
-- Find the average room price by room capacity across all hotels
SELECT Capacity, ROUND(AVG(Price), 2) AS AvgPrice
FROM Room
GROUP BY Capacity
ORDER BY AvgPrice DESC;

-- Aggregation Query 2
-- Count rooms by hotel category and view type, with average price
SELECT 
    h.Category, 
    r.ViewType, 
    COUNT(r.RoomID) AS RoomCount,
    ROUND(AVG(r.Price), 2) AS AverageRoomPrice
FROM Hotel h
JOIN Room r ON h.HotelID = r.HotelID
GROUP BY h.Category, r.ViewType
ORDER BY h.Category, RoomCount DESC;

-- Aggregation Query 3 
-- Find the most frequently used payment method
SELECT PaymentMethod, COUNT(*) AS UsageCount
FROM Rental
WHERE PaymentMethod IS NOT NULL
GROUP BY PaymentMethod
ORDER BY UsageCount DESC
LIMIT 1;

-- Nested Query 1
-- List customers who have at least one checked-in booking
SELECT FullName
FROM Customer
WHERE CustomerID IN (
    SELECT DISTINCT CustomerID
    FROM Booking
    WHERE Status = 'Checked-in'
);

-- Nested Query 2
-- Find hotels whose average room price is above the overall average
SELECT 
    h.HotelID, 
    h.HotelName, 
    hc.ChainName,
    ROUND(AVG(r.Price), 2) AS AvgRoomPrice
FROM Hotel h
JOIN HotelChain hc ON h.HotelChainID = hc.HotelChainID
JOIN Room r ON h.HotelID = r.HotelID
GROUP BY h.HotelID, h.HotelName, hc.ChainName
HAVING AVG(r.Price) > (
    SELECT AVG(Price) 
    FROM Room
)
ORDER BY AvgRoomPrice DESC;

-- Nested Query 3 
-- Employees working at hotels that have a suite marked Out-of-Order
SELECT e.FullName, e.Position, h.HotelName
FROM Employee e
JOIN Hotel h ON e.HotelID = h.HotelID
WHERE h.HotelID IN (
    SELECT r.HotelID
    FROM Room r
    WHERE r.Capacity = 'suite' AND r.Status = 'Out-of-Order'
);

-- Join Query 1
-- Show available rooms with sea view and the hotel they belong to
SELECT r.RoomID, h.HotelName, r.Capacity, r.Price
FROM Room r
JOIN Hotel h ON r.HotelID = h.HotelID
WHERE r.ViewType = 'sea_view' AND r.Status = 'Available';

-- Join Query 2
-- Hotel details with manager and hotel chain info
SELECT 
    hc.ChainName, 
    h.HotelName, 
    h.Address, 
    h.Rating, 
    h.Category,
    e.FullName AS ManagerName,
    e.Address AS ManagerAddress
FROM Hotel h
JOIN HotelChain hc ON h.HotelChainID = hc.HotelChainID
LEFT JOIN Employee e ON h.ManagerID = e.EmployeeID
ORDER BY hc.ChainName, h.Rating DESC;

-- Join Query 3
-- Show all room amenities grouped by room
SELECT 
    h.HotelName,
    r.Capacity,
    r.ViewType,
    r.Price,
    STRING_AGG(ra.Amenity, ', ') AS RoomAmenities
FROM Hotel h
JOIN Room r ON h.HotelID = r.HotelID
JOIN RoomAmenities ra ON h.HotelID = ra.HotelID AND r.RoomID = ra.RoomID
GROUP BY h.HotelName, r.Capacity, r.ViewType, r.Price
ORDER BY h.HotelName, r.Price;

-- Filtering Query
-- Unresolved room problems reported in March 2025
SELECT *
FROM RoomProblems
WHERE Resolved = FALSE
  AND ReportDate BETWEEN '2025-03-01' AND '2025-03-31';
