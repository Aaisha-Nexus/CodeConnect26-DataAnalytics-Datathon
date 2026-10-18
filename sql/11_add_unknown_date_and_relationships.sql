
USE NexusMartDW;
GO

SET XACT_ABORT ON;
GO

BEGIN TRY
    BEGIN TRANSACTION;

    -- 1. Add the Unknown date member if missing.
    IF NOT EXISTS (
        SELECT 1 FROM dw.DimDate WHERE DateKey = 0
    )
    BEGIN
        INSERT INTO dw.DimDate
        (
            DateKey, FullDate, CalendarYear, CalendarQuarter,
            MonthNumber, MonthName, DayOfMonth, DayOfWeekName,
            IsWeekend, WeekNumber, IsHoliday, EventName
        )
        VALUES
        (
            0, NULL, 0, 0,
            0, 'Unknown', 0, 'Unknown',
            0, 0, 0, 'Unknown'
        );
    END;

    -- 2. Add fact-to-dimension foreign keys if missing.
    IF NOT EXISTS (
        SELECT 1 FROM sys.foreign_keys
        WHERE name = 'FK_FactSales_DimDate'
    )
        ALTER TABLE dw.FactSales WITH CHECK
        ADD CONSTRAINT FK_FactSales_DimDate
        FOREIGN KEY (DateKey) REFERENCES dw.DimDate(DateKey);

    IF NOT EXISTS (
        SELECT 1 FROM sys.foreign_keys
        WHERE name = 'FK_FactSales_DimCustomer'
    )
        ALTER TABLE dw.FactSales WITH CHECK
        ADD CONSTRAINT FK_FactSales_DimCustomer
        FOREIGN KEY (CustomerKey) REFERENCES dw.DimCustomer(CustomerKey);

    IF NOT EXISTS (
        SELECT 1 FROM sys.foreign_keys
        WHERE name = 'FK_FactSales_DimProduct'
    )
        ALTER TABLE dw.FactSales WITH CHECK
        ADD CONSTRAINT FK_FactSales_DimProduct
        FOREIGN KEY (ProductKey) REFERENCES dw.DimProduct(ProductKey);

    IF NOT EXISTS (
        SELECT 1 FROM sys.foreign_keys
        WHERE name = 'FK_FactSales_DimSeller'
    )
        ALTER TABLE dw.FactSales WITH CHECK
        ADD CONSTRAINT FK_FactSales_DimSeller
        FOREIGN KEY (SellerKey) REFERENCES dw.DimSeller(SellerKey);

    IF NOT EXISTS (
        SELECT 1 FROM sys.foreign_keys
        WHERE name = 'FK_FactSales_DimLocation'
    )
        ALTER TABLE dw.FactSales WITH CHECK
        ADD CONSTRAINT FK_FactSales_DimLocation
        FOREIGN KEY (LocationKey) REFERENCES dw.DimLocation(LocationKey);

    COMMIT TRANSACTION;
    PRINT 'Unknown date and fact-to-dimension relationships created.';
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO

-- Verify Unknown date member.
SELECT *
FROM dw.DimDate
WHERE DateKey = 0;
GO

-- Verify relationships.
SELECT
    OBJECT_NAME(parent_object_id) AS FromTable,
    name AS ForeignKeyName,
    OBJECT_NAME(referenced_object_id) AS ToTable,
    is_disabled,
    is_not_trusted
FROM sys.foreign_keys
WHERE parent_object_id = OBJECT_ID('dw.FactSales')
ORDER BY name;
GO
