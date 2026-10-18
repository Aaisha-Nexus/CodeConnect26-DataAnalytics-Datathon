
USE NexusMartDW;
GO

-- 1. Confirm row counts after loading
SELECT 'Customers' AS TableName, COUNT_BIG(*) AS RowCount FROM stg.Customers
UNION ALL SELECT 'Locations', COUNT_BIG(*) FROM stg.Locations
UNION ALL SELECT 'Orders', COUNT_BIG(*) FROM stg.Orders
UNION ALL SELECT 'OrderItems', COUNT_BIG(*) FROM stg.OrderItems
UNION ALL SELECT 'Payments', COUNT_BIG(*) FROM stg.Payments
UNION ALL SELECT 'Products', COUNT_BIG(*) FROM stg.Products
UNION ALL SELECT 'Returns', COUNT_BIG(*) FROM stg.Returns
UNION ALL SELECT 'Sellers', COUNT_BIG(*) FROM stg.Sellers
UNION ALL SELECT 'Shipping', COUNT_BIG(*) FROM stg.Shipping
ORDER BY TableName;
GO

-- 2. Check primary-key fields for blanks
SELECT 'Customers' AS TableName, COUNT_BIG(*) AS BlankKeyRows
FROM stg.Customers WHERE NULLIF(LTRIM(RTRIM(customer_id)), '') IS NULL
UNION ALL SELECT 'Locations', COUNT_BIG(*) FROM stg.Locations
WHERE NULLIF(LTRIM(RTRIM(city_id)), '') IS NULL
UNION ALL SELECT 'Orders', COUNT_BIG(*) FROM stg.Orders
WHERE NULLIF(LTRIM(RTRIM(order_id)), '') IS NULL
UNION ALL SELECT 'OrderItems', COUNT_BIG(*) FROM stg.OrderItems
WHERE NULLIF(LTRIM(RTRIM(order_item_id)), '') IS NULL
UNION ALL SELECT 'Payments', COUNT_BIG(*) FROM stg.Payments
WHERE NULLIF(LTRIM(RTRIM(payment_id)), '') IS NULL
UNION ALL SELECT 'Products', COUNT_BIG(*) FROM stg.Products
WHERE NULLIF(LTRIM(RTRIM(product_id)), '') IS NULL
UNION ALL SELECT 'Returns', COUNT_BIG(*) FROM stg.Returns
WHERE NULLIF(LTRIM(RTRIM(return_id)), '') IS NULL
UNION ALL SELECT 'Sellers', COUNT_BIG(*) FROM stg.Sellers
WHERE NULLIF(LTRIM(RTRIM(seller_id)), '') IS NULL
UNION ALL SELECT 'Shipping', COUNT_BIG(*) FROM stg.Shipping
WHERE NULLIF(LTRIM(RTRIM(shipment_id)), '') IS NULL
ORDER BY TableName;
GO
