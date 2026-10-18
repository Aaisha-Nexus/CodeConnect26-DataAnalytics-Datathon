
USE NexusMartDW;
GO

-- Keep the existing FactSales table and its data.
-- Add fields required for analysis if they do not already exist.

IF COL_LENGTH('dw.FactSales', 'IsCancelled') IS NULL
    ALTER TABLE dw.FactSales ADD IsCancelled BIT NOT NULL
        CONSTRAINT DF_FactSales_IsCancelled DEFAULT (0) WITH VALUES;
GO

IF COL_LENGTH('dw.FactSales', 'IsReturned') IS NULL
    ALTER TABLE dw.FactSales ADD IsReturned BIT NOT NULL
        CONSTRAINT DF_FactSales_IsReturned DEFAULT (0) WITH VALUES;
GO

IF COL_LENGTH('dw.FactSales', 'OrderStatus') IS NULL
    ALTER TABLE dw.FactSales ADD OrderStatus VARCHAR(50) NULL;
GO

IF COL_LENGTH('dw.FactSales', 'PaymentMethod') IS NULL
    ALTER TABLE dw.FactSales ADD PaymentMethod VARCHAR(50) NULL;
GO

IF COL_LENGTH('dw.FactSales', 'Channel') IS NULL
    ALTER TABLE dw.FactSales ADD Channel VARCHAR(50) NULL;
GO

IF COL_LENGTH('dw.FactSales', 'ShippingDays') IS NULL
    ALTER TABLE dw.FactSales ADD ShippingDays INT NULL;
GO

IF COL_LENGTH('dw.FactSales', 'ReturnedAmount') IS NULL
    ALTER TABLE dw.FactSales ADD ReturnedAmount DECIMAL(18,2) NOT NULL
        CONSTRAINT DF_FactSales_ReturnedAmount DEFAULT (0) WITH VALUES;
GO

IF COL_LENGTH('dw.FactSales', 'ReturnDateKey') IS NULL
    ALTER TABLE dw.FactSales ADD ReturnDateKey INT NULL;
GO

IF COL_LENGTH('dw.FactSales', 'ReturnReason') IS NULL
    ALTER TABLE dw.FactSales ADD ReturnReason VARCHAR(255) NULL;
GO

IF COL_LENGTH('dw.FactSales', 'ReturnStatus') IS NULL
    ALTER TABLE dw.FactSales ADD ReturnStatus VARCHAR(50) NULL;
GO

PRINT 'FactSales schema updated safely.';
GO
