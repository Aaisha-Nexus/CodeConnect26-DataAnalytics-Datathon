NexusMart Datathon - raw data package (Jan 2024 - Jun 2025)
Files: customers, products, sellers, locations, orders, order_items, payments, shipping, returns (CSV, UTF-8, header row).
Notes for participants:
 - All files are raw exports. Expect dirty data; profiling it is part of the task.
 - order_total / unit_price / amount / refund_amount are in PKR. order_total is merchandise value after discounts.
 - shipping.shipping_fee is the courier charge billed to NexusMart (customers get free shipping).
 - discount_code values encode the order-level discount percentage (e.g. SAVE20 = 20%).
 - returns.return_status: only non-Rejected returns are real returns.
 - A later data drop (Hour 6) will use the same schema, but do not assume it is identical.
