
USE NexusMartDW;
GO

-- 1. Add required calendar attributes if absent.
IF COL_LENGTH('dw.DimDate', 'WeekNumber') IS NULL
    ALTER TABLE dw.DimDate ADD WeekNumber TINYINT NULL;
GO

IF COL_LENGTH('dw.DimDate', 'IsHoliday') IS NULL
    ALTER TABLE dw.DimDate ADD IsHoliday BIT NOT NULL
        CONSTRAINT DF_DimDate_IsHoliday DEFAULT (0) WITH VALUES;
GO

IF COL_LENGTH('dw.DimDate', 'EventName') IS NULL
    ALTER TABLE dw.DimDate ADD EventName VARCHAR(50) NULL;
GO

-- 2. Populate week number and reset event flags.
UPDATE dw.DimDate
SET
    WeekNumber = DATEPART(ISO_WEEK, FullDate),
    IsHoliday = 0,
    EventName = NULL;
GO

-- 3. Ramadan: 2024 and 2025.
UPDATE dw.DimDate
SET EventName = 'Ramadan'
WHERE FullDate BETWEEN '2024-03-11' AND '2024-04-09'
   OR FullDate BETWEEN '2025-03-01' AND '2025-03-30';
GO

-- 4. Eid-ul-Fitr.
UPDATE dw.DimDate
SET EventName = 'Eid-ul-Fitr'
WHERE FullDate BETWEEN '2024-04-10' AND '2024-04-12'
   OR FullDate BETWEEN '2025-03-31' AND '2025-04-02';
GO

-- 5. Eid-ul-Adha.
UPDATE dw.DimDate
SET EventName = 'Eid-ul-Adha'
WHERE FullDate BETWEEN '2024-06-17' AND '2024-06-19'
   OR FullDate BETWEEN '2025-06-07' AND '2025-06-09';
GO

-- 6. Independence Day.
UPDATE dw.DimDate
SET EventName = 'Independence Day'
WHERE MONTH(FullDate) = 8
  AND DAY(FullDate) = 14;
GO

-- 7. Singles Day (11.11).
UPDATE dw.DimDate
SET EventName = 'Singles Day'
WHERE MONTH(FullDate) = 11
  AND DAY(FullDate) = 11;
GO

-- 8. Black Friday: specified date in the brief.
UPDATE dw.DimDate
SET EventName = 'Black Friday'
WHERE FullDate = '2024-11-29';
GO

-- Mark event dates as holidays/event days.
UPDATE dw.DimDate
SET IsHoliday = CASE WHEN EventName IS NOT NULL THEN 1 ELSE 0 END;
GO

-- 9. Verify event dates and calendar coverage.
SELECT
    EventName,
    MIN(FullDate) AS FirstEventDate,
    MAX(FullDate) AS LastEventDate,
    COUNT(*) AS EventDays
FROM dw.DimDate
WHERE EventName IS NOT NULL
GROUP BY EventName
ORDER BY EventName;
GO

SELECT
    MIN(FullDate) AS CalendarStart,
    MAX(FullDate) AS CalendarEnd,
    COUNT(*) AS CalendarDays,
    SUM(CASE WHEN IsHoliday = 1 THEN 1 ELSE 0 END) AS EventDays
FROM dw.DimDate;
GO
