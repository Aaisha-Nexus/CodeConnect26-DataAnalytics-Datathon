
USE NexusMartDW;
GO

-- Add the required measures only if they don't exist.
IF COL_LENGTH('dw.FactSales', 'GrossAmount') IS NULL
    ALTER TABLE dw.FactSales ADD GrossAmount DECIMAL(18,2) NULL;
GO

IF COL_LENGTH('dw.FactSales', 'NetAmount') IS NULL
    ALTER TABLE dw.FactSales ADD NetAmount DECIMAL(18,2) NULL;
GO

IF COL_LENGTH('dw.FactSales', 'CostAmount') IS NULL
    ALTER TABLE dw.FactSales ADD CostAmount DECIMAL(18,2) NULL;
GO

-- Gross = quantity x unit price.
-- Net = gross less line-level discount.
-- Cost = product cost price x quantity.
UPDATE f
SET
    GrossAmount =
        CASE
            WHEN f.Quantity IS NOT NULL AND f.UnitPrice IS NOT NULL
            THEN f.Quantity * f.UnitPrice
            ELSE NULL
        END,

    NetAmount =
        CASE
            WHEN f.Quantity IS NOT NULL AND f.UnitPrice IS NOT NULL
            THEN f.Quantity * f.UnitPrice - COALESCE(f.DiscountAmount, 0)
            ELSE NULL
        END,

    CostAmount =
        CASE
            WHEN f.Quantity IS NOT NULL AND p.CostPrice IS NOT NULL
            THEN f.Quantity * p.CostPrice
            ELSE NULL
        END
FROM dw.FactSales f
LEFT JOIN dw.DimProduct p
    ON p.ProductKey = f.ProductKey;
GO

-- Verify the new measures.
SELECT
    COUNT_BIG(*) AS FactRows,
    SUM(GrossAmount) AS GrossAmount,
    SUM(DiscountAmount) AS DiscountAmount,
    SUM(NetAmount) AS NetAmount,
    SUM(CostAmount) AS CostAmount
FROM dw.FactSales;
GO
