
USE NexusMartDW;
GO

IF SCHEMA_ID('stg') IS NULL
    EXEC('CREATE SCHEMA stg');
GO

CREATE TABLE stg.Customers (
    customer_id VARCHAR(50),
    full_name VARCHAR(200),
    email VARCHAR(320),
    phone VARCHAR(50),
    gender VARCHAR(30),
    registration_date VARCHAR(50),
    city_id VARCHAR(50),
    birth_year VARCHAR(20)
);

CREATE TABLE stg.Locations (
    city_id VARCHAR(50),
    city VARCHAR(100),
    province VARCHAR(100),
    region VARCHAR(100),
    latitude VARCHAR(50),
    longitude VARCHAR(50),
    population_tier VARCHAR(50)
);

CREATE TABLE stg.Orders (
    order_id VARCHAR(50),
    customer_id VARCHAR(50),
    order_date VARCHAR(50),
    order_status VARCHAR(50),
    ship_city_id VARCHAR(50),
    order_total VARCHAR(50),
    discount_code VARCHAR(100),
    channel VARCHAR(50)
);

CREATE TABLE stg.OrderItems (
    order_item_id VARCHAR(50),
    order_id VARCHAR(50),
    product_id VARCHAR(50),
    seller_id VARCHAR(50),
    quantity VARCHAR(30),
    unit_price VARCHAR(50),
    discount_amount VARCHAR(50)
);

CREATE TABLE stg.Payments (
    payment_id VARCHAR(50),
    order_id VARCHAR(50),
    payment_method VARCHAR(50),
    payment_status VARCHAR(50),
    amount VARCHAR(50),
    payment_date VARCHAR(50)
);

CREATE TABLE stg.Products (
    product_id VARCHAR(50),
    product_name VARCHAR(200),
    category VARCHAR(100),
    sub_category VARCHAR(100),
    brand VARCHAR(100),
    list_price VARCHAR(50),
    cost_price VARCHAR(50),
    weight_kg VARCHAR(50),
    seller_id VARCHAR(50)
);

CREATE TABLE stg.Returns (
    return_id VARCHAR(50),
    order_item_id VARCHAR(50),
    return_date VARCHAR(50),
    return_reason VARCHAR(200),
    return_status VARCHAR(50),
    refund_amount VARCHAR(50)
);

CREATE TABLE stg.Sellers (
    seller_id VARCHAR(50),
    seller_name VARCHAR(200),
    join_date VARCHAR(50),
    seller_tier VARCHAR(50),
    city_id VARCHAR(50),
    rating VARCHAR(30)
);

CREATE TABLE stg.Shipping (
    shipment_id VARCHAR(50),
    order_id VARCHAR(50),
    courier VARCHAR(100),
    shipped_date VARCHAR(50),
    delivered_date VARCHAR(50),
    shipping_fee VARCHAR(50),
    delivery_status VARCHAR(50)
);
GO

SELECT TABLE_SCHEMA, TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'stg'
ORDER BY TABLE_NAME;
GO
