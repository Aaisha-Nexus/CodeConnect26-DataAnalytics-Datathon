
USE NexusMartDW;
GO

SET XACT_ABORT ON;
GO

BEGIN TRY
    BEGIN TRANSACTION;

    ;WITH ShippingByOrder AS
    (
        SELECT
            order_id,
            MAX(TRY_CONVERT(DECIMAL(18,2), shipping_fee)) AS ShippingFee,
            MIN(TRY_CONVERT(DATE, shipped_date, 103)) AS ShippedDate,
            MAX(TRY_CONVERT(DATE, delivered_date, 103)) AS DeliveredDate
        FROM stg.Shipping
        GROUP BY order_id
    ),
    LineCounts AS
    (
        SELECT order_id, COUNT_BIG(*) AS LineCount
        FROM stg.OrderItems
        GROUP BY order_id
    ),
    ReturnByLine AS
    (
        SELECT
            order_item_id,
            SUM(
                CASE
                    WHEN UPPER(LTRIM(RTRIM(return_status))) <> 'REJECTED'
                    THEN COALESCE(
                        TRY_CONVERT(DECIMAL(18,2), refund_amount), 0
                    )
                    ELSE 0
                END
            ) AS ValidRefundAmount,
            MAX(
                CASE
                    WHEN UPPER(LTRIM(RTRIM(return_status))) <> 'REJECTED'
                    THEN 1 ELSE 0
                END
            ) AS HasValidReturn
        FROM stg.Returns
        GROUP BY order_item_id
    ),
    LatestReturn AS
    (
        SELECT
            order_item_id,
            return_status,
            return_reason,
            TRY_CONVERT(DATE, return_date, 103) AS ReturnDate,
            ROW_NUMBER() OVER
            (
                PARTITION BY order_item_id
                ORDER BY TRY_CONVERT(DATE, return_date, 103) DESC,
                         return_id DESC
            ) AS rn
        FROM stg.Returns
    ),
    PaymentByOrder AS
    (
        SELECT
            order_id,
            payment_method,
            ROW_NUMBER() OVER
            (
                PARTITION BY order_id
                ORDER BY TRY_CONVERT(DATE, payment_date, 103) DESC,
                         payment_id DESC
            ) AS rn
        FROM stg.Payments
    )
    UPDATE f
    SET
        f.IsCancelled =
            CASE WHEN UPPER(LTRIM(RTRIM(o.order_status))) LIKE '%CANCEL%'
                 THEN 1 ELSE 0 END,

        f.IsReturned = COALESCE(r.HasValidReturn, 0),
        f.OrderStatus = o.order_status,
        f.Channel = o.channel,
        f.PaymentMethod = p.payment_method,

        f.ShippingDays =
            CASE
                WHEN s.ShippedDate IS NOT NULL
                 AND s.DeliveredDate IS NOT NULL
                THEN DATEDIFF(DAY, s.ShippedDate, s.DeliveredDate)
                ELSE NULL
            END,

        f.ReturnedAmount = COALESCE(r.ValidRefundAmount, 0),
        f.RefundAmount = COALESCE(r.ValidRefundAmount, 0),
        f.ReturnStatus = lr.return_status,
        f.ReturnReason = lr.return_reason,
        f.ReturnDateKey = COALESCE(dd.DateKey, 0),

        f.AllocatedShippingFee =
            CASE
                WHEN lc.LineCount > 0 AND s.ShippingFee IS NOT NULL
                THEN s.ShippingFee /
                     CAST(lc.LineCount AS DECIMAL(18,2))
                ELSE 0
            END

    FROM dw.FactSales AS f
    INNER JOIN stg.Orders AS o
        ON o.order_id = f.OrderID
    LEFT JOIN ShippingByOrder AS s
        ON s.order_id = o.order_id
    LEFT JOIN LineCounts AS lc
        ON lc.order_id = o.order_id
    LEFT JOIN PaymentByOrder AS p
        ON p.order_id = o.order_id AND p.rn = 1
    LEFT JOIN ReturnByLine AS r
        ON r.order_item_id = f.OrderItemID
    LEFT JOIN LatestReturn AS lr
        ON lr.order_item_id = f.OrderItemID AND lr.rn = 1
    LEFT JOIN dw.DimDate AS dd
        ON dd.FullDate = lr.ReturnDate;

    COMMIT TRANSACTION;
    PRINT 'FactSales update completed successfully.';

END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;
    THROW;
END CATCH;
GO

SELECT
    COUNT_BIG(*) AS FactRows,
    SUM(CASE WHEN IsCancelled = 1 THEN 1 ELSE 0 END) AS CancelledLines,
    SUM(CASE WHEN IsReturned = 1 THEN 1 ELSE 0 END) AS ReturnedLines,
    SUM(RefundAmount) AS TotalRefundAmount,
    SUM(AllocatedShippingFee) AS AllocatedShippingTotal
FROM dw.FactSales;
GO
