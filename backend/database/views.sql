-- View 1: Number of available rooms per city (area)
DROP VIEW IF EXISTS view_available_rooms_per_city;

CREATE VIEW view_available_rooms_per_city AS
SELECT 
    TRIM(SPLIT_PART(h.Address, ',', 2)) AS City,
    COUNT(*) AS AvailableRooms
FROM Room r
JOIN Hotel h ON r.HotelID = h.HotelID
WHERE r.Status = 'Available'
GROUP BY City
ORDER BY AvailableRooms DESC;


-- View 2: Aggregated capacity of all rooms for each hotel
DROP VIEW IF EXISTS view_total_capacity_per_hotel;

CREATE VIEW view_total_capacity_per_hotel AS
SELECT 
    h.HotelName,
    SUM(
        CASE 
            WHEN r.Capacity = 'single' THEN 1
            WHEN r.Capacity = 'double' THEN 2
            WHEN r.Capacity = 'triple' THEN 3
            WHEN r.Capacity = 'family' THEN 4
            WHEN r.Capacity = 'suite' THEN 5
            ELSE 1
        END
    ) AS TotalCapacity
FROM Hotel h
JOIN Room r ON h.HotelID = r.HotelID
GROUP BY h.HotelName
ORDER BY TotalCapacity DESC;
