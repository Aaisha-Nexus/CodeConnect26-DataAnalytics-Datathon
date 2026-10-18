
USE NexusMartDW;
GO

-- Create a dedicated warehouse schema.
IF SCHEMA_ID('dw') IS NULL
    EXEC('CREATE SCHEMA dw');
GO

CREATE TABLE dw.DimDate (
    DateKey INT NOT NULL PRIMARY KEY,
    FullDate DATE NULL,
    CalendarYear SMALLINT NULL,
    CalendarQuarter TINYINT NULL,
    MonthNumber TINYINT NULL,
    MonthName VARCHAR(15) NULL,
    DayOfMonth TINYINT NULL,
    DayOfWeekName VARCHAR(15) NULL,
    IsWeekend BIT NULL
);

CREATE TABLE dw.DimCustomer (
    CustomerKey INT IDENTITY(1,1) PRIMARY KEY,
    CustomerID VARCHAR(50) NOT NULL UNIQUE,
    FullName VARCHAR(200) NULL,
    Gender VARCHAR(30) NULL,
    RegistrationDate DATE NULL,
    BirthYear SMALLINT NULL,
    CityID VARCHAR(50) NULL
);

CREATE TABLE dw.DimProduct (
    ProductKey INT IDENTITY(1,1) PRIMARY KEY,
    ProductID VARCHAR(50) NOT NULL UNIQUE,
    ProductName VARCHAR(200) NULL,
    Category VARCHAR(100) NULL,
    SubCategory VARCHAR(100) NULL,
    Brand VARCHAR(100) NULL,
    ListPrice DECIMAL(18,2) NULL,
    CostPrice DECIMAL(18,2) NULL,
    WeightKg DECIMAL(10,3) NULL,
    SellerID VARCHAR(50) NULL
);

CREATE TABLE dw.DimSeller (
    SellerKey INT IDENTITY(1,1) PRIMARY KEY,
    SellerID VARCHAR(50) NOT NULL UNIQUE,
    SellerName VARCHAR(200) NULL,
    JoinDate DATE NULL,
    SellerTier VARCHAR(50) NULL,
    CityID VARCHAR(50) NULL,
    Rating DECIMAL(5,2) NULL
);

CREATE TABLE dw.DimLocation (
    LocationKey INT IDENTITY(1,1) PRIMARY KEY,
    CityID VARCHAR(50) NOT NULL UNIQUE,
    City VARCHAR(100) NULL,
    Province VARCHAR(100) NULL,
    Region VARCHAR(100) NULL,
    Latitude DECIMAL(10,6) NULL,
    Longitude DECIMAL(10,6) NULL,
    PopulationTier VARCHAR(50) NULL
);
GO

-- Unknown member in each dimension; key 0 is reserved.
SET IDENTITY_INSERT dw.DimCustomer ON;
INSERT INTO dw.DimCustomer
    (CustomerKey, CustomerID, FullName)
VALUES (0, 'UNKNOWN', 'Unknown Customer');
SET IDENTITY_INSERT dw.DimCustomer OFF;

SET IDENTITY_INSERT dw.DimProduct ON;
INSERT INTO dw.DimProduct
    (ProductKey, ProductID, ProductName)
VALUES (0, 'UNKNOWN', 'Unknown Product');
SET IDENTITY_INSERT dw.DimProduct OFF;

SET IDENTITY_INSERT dw.DimSeller ON;
INSERT INTO dw.DimSeller
    (SellerKey, SellerID, SellerName)
VALUES (0, 'UNKNOWN', 'Unknown Seller');
SET IDENTITY_INSERT dw.DimSeller OFF;

SET IDENTITY_INSERT dw.DimLocation ON;
INSERT INTO dw.DimLocation
    (LocationKey, CityID, City)
VALUES (0, 'UNKNOWN', 'Unknown Location');
SET IDENTITY_INSERT dw.DimLocation OFF;
GO

-- Populate the date dimension for the permitted order-date period.
;WITH Calendar AS (
    SELECT CAST('2024-01-01' AS DATE) AS CalendarDate
    UNION ALL
    SELECT DATEADD(DAY, 1, CalendarDate)
    FROM Calendar
    WHERE CalendarDate < '2025-06-30'
)
INSERT INTO dw.DimDate (
    DateKey, FullDate, CalendarYear, CalendarQuarter,
    MonthNumber, MonthName, DayOfMonth, DayOfWeekName, IsWeekend
)
SELECT
    YEAR(CalendarDate) * 10000
        + MONTH(CalendarDate) * 100
        + DAY(CalendarDate),
    CalendarDate,
    YEAR(CalendarDate),
    DATEPART(QUARTER, CalendarDate),
    MONTH(CalendarDate),
    DATENAME(MONTH, CalendarDate),
    DAY(CalendarDate),
    DATENAME(WEEKDAY, CalendarDate),
    CASE WHEN DATEDIFF(DAY, '19000101', CalendarDate) % 7 IN (5, 6)
         THEN 1 ELSE 0 END
FROM Calendar
OPTION (MAXRECURSION 0);

-- Populate dimensions using one row per business ID.
INSERT INTO dw.DimLocation
    (CityID, City, Province, Region, Latitude, Longitude, PopulationTier)
SELECT city_id, MAX(city), MAX(province), MAX(region),
       MAX(TRY_CONVERT(DECIMAL(10,6), latitude)),
       MAX(TRY_CONVERT(DECIMAL(10,6), longitude)),
       MAX(population_tier)
FROM stg.Locations
WHERE NULLIF(LTRIM(RTRIM(city_id)), '') IS NOT NULL
  AND city_id <> 'UNKNOWN'
GROUP BY city_id;

INSERT INTO dw.DimCustomer
    (CustomerID, FullName, Gender, RegistrationDate, BirthYear, CityID)
SELECT customer_id, MAX(full_name), MAX(gender),
       MAX(COALESCE(
           TRY_CONVERT(DATE, registration_date, 23),
           TRY_CONVERT(DATE, registration_date, 103)
       )),
       MAX(TRY_CONVERT(SMALLINT, birth_year)),
       MAX(city_id)
FROM stg.Customers
WHERE NULLIF(LTRIM(RTRIM(customer_id)), '') IS NOT NULL
  AND customer_id <> 'UNKNOWN'
GROUP BY customer_id;

INSERT INTO dw.DimProduct
    (ProductID, ProductName, Category, SubCategory, Brand,
     ListPrice, CostPrice, WeightKg, SellerID)
SELECT product_id, MAX(product_name), MAX(category), MAX(sub_category),
       MAX(brand),
       MAX(TRY_CONVERT(DECIMAL(18,2), list_price)),
       MAX(TRY_CONVERT(DECIMAL(18,2), cost_price)),
       MAX(TRY_CONVERT(DECIMAL(10,3), weight_kg)),
       MAX(seller_id)
FROM stg.Products
WHERE NULLIF(LTRIM(RTRIM(product_id)), '') IS NOT NULL
  AND product_id <> 'UNKNOWN'
GROUP BY product_id;

INSERT INTO dw.DimSeller
    (SellerID, SellerName, JoinDate, SellerTier, CityID, Rating)
SELECT seller_id, MAX(seller_name),
       MAX(COALESCE(
           TRY_CONVERT(DATE, join_date, 23),
           TRY_CONVERT(DATE, join_date, 103)
       )),
       MAX(seller_tier), MAX(city_id),
       MAX(TRY_CONVERT(DECIMAL(5,2), rating))
FROM stg.Sellers
WHERE NULLIF(LTRIM(RTRIM(seller_id)), '') IS NOT NULL
  AND seller_id <> 'UNKNOWN'
GROUP BY seller_id;
GO

-- Summary of loaded dimensions
SELECT 'DimDate' AS DimensionName, COUNT_BIG(*) AS TotalRows FROM dw.DimDate
UNION ALL SELECT 'DimCustomer', COUNT_BIG(*) FROM dw.DimCustomer
UNION ALL SELECT 'DimProduct', COUNT_BIG(*) FROM dw.DimProduct
UNION ALL SELECT 'DimSeller', COUNT_BIG(*) FROM dw.DimSeller
UNION ALL SELECT 'DimLocation', COUNT_BIG(*) FROM dw.DimLocation
ORDER BY DimensionName;
GO
