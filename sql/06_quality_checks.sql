
USE NexusMartDW;
GO

PRINT '1. FACT TABLE GRAIN';
SELECT
    COUNT_BIG(*) AS FactRows,
    COUNT(DISTINCT OrderItemID) AS DistinctOrderItems,
    COUNT(DISTINCT OrderID) AS DistinctOrders
FROM dw.FactSales;
GO

PRINT '2. MISSING DIMENSION KEYS';
SELECT
    SUM(CASE WHEN dd.DateKey IS NULL THEN 1 ELSE 0 END) AS MissingDates,
    SUM(CASE WHEN dc.CustomerKey IS NULL THEN 1 ELSE 0 END) AS MissingCustomers,
    SUM(CASE WHEN dp.ProductKey IS NULL THEN 1 ELSE 0 END) AS MissingProducts,
    SUM(CASE WHEN ds.SellerKey IS NULL THEN 1 ELSE 0 END) AS MissingSellers,
    SUM(CASE WHEN dl.LocationKey IS NULL THEN 1 ELSE 0 END) AS MissingLocations
FROM dw.FactSales f
LEFT JOIN dw.DimDate dd ON f.DateKey = dd.DateKey
LEFT JOIN dw.DimCustomer dc ON f.CustomerKey = dc.CustomerKey
LEFT JOIN dw.DimProduct dp ON f.ProductKey = dp.ProductKey
LEFT JOIN dw.DimSeller ds ON f.SellerKey = ds.SellerKey
LEFT JOIN dw.DimLocation dl ON f.LocationKey = dl.LocationKey;
GO

PRINT '3. UNKNOWN DIMENSION MEMBERS';
SELECT 'DimDate' AS DimensionName, COUNT(*) AS UnknownRows
FROM dw.DimDate WHERE DateKey = 0
UNION ALL
SELECT 'DimCustomer', COUNT(*)
FROM dw.DimCustomer WHERE CustomerKey = 0
UNION ALL
SELECT 'DimProduct', COUNT(*)
FROM dw.DimProduct WHERE ProductKey = 0
UNION ALL
SELECT 'DimSeller', COUNT(*)
FROM dw.DimSeller WHERE SellerKey = 0
UNION ALL
SELECT 'DimLocation', COUNT(*)
FROM dw.DimLocation WHERE LocationKey = 0;
GO

PRINT '4. SOURCE ITEMS NOT LOADED';
SELECT COUNT_BIG(*) AS MissingOrderItems
FROM stg.OrderItems oi
LEFT JOIN dw.FactSales f ON f.OrderItemID = oi.order_item_id
WHERE f.OrderItemID IS NULL;
GO

PRINT '5. SHIPPING RECONCILIATION';
SELECT
    (SELECT SUM(TRY_CONVERT(DECIMAL(18,2), shipping_fee))
     FROM stg.Shipping) AS SourceShippingTotal,
    (SELECT SUM(AllocatedShippingFee)
     FROM dw.FactSales) AS AllocatedShippingTotal;
GO

PRINT '6. RETURN STATUS AUDIT';
SELECT
    ReturnStatus,
    COUNT_BIG(*) AS FactLines,
    SUM(RefundAmount) AS RefundAmount
FROM dw.FactSales
GROUP BY ReturnStatus
ORDER BY ReturnStatus;
GO

PRINT '7. FACT SALES TOTALS';
SELECT
    SUM(MerchandiseSales) AS MerchandiseSales,
    SUM(DiscountAmount) AS DiscountAmount,
    SUM(ReturnedAmount) AS ReturnedAmount,
    SUM(CASE WHEN IsCancelled = 1 THEN 1 ELSE 0 END) AS CancelledLines,
    SUM(CASE WHEN IsReturned = 1 THEN 1 ELSE 0 END) AS ReturnedLines
FROM dw.FactSales;
GO
