-- ============================================================
-- PROJECT: Agentic AI Revenue Guardian
-- FILE:    1_schema.sql
-- PURPOSE: Define the 3 core tables used in this project
-- AUTHOR:  Durgesh Rakhame
-- ============================================================

-- -------------------------------------------------------
-- TABLE 1: dim_products
-- A "dimension" table — stores product master data.
-- Think of it as the product catalogue.
-- -------------------------------------------------------
CREATE TABLE dim_products (
    product_id      VARCHAR(10)     PRIMARY KEY,        -- Unique product code e.g. 'P001'
    product_name    VARCHAR(100)    NOT NULL,           -- Human-readable name
    category        VARCHAR(50)     NOT NULL,           -- e.g. Electronics, Clothing
    price           DECIMAL(10, 2)  NOT NULL,           -- Listed selling price (INR)
    stock_quantity  INT             DEFAULT 0           -- Units currently in stock
);

-- -------------------------------------------------------
-- TABLE 2: fact_sales
-- A "fact" table — every sales transaction lives here.
-- It references dim_products via product_id (foreign key).
-- -------------------------------------------------------
CREATE TABLE fact_sales (
    sale_id         SERIAL          PRIMARY KEY,        -- Auto-incrementing unique sale ID
    product_id      VARCHAR(10)     NOT NULL,           -- Links to dim_products
    sale_date       DATE            NOT NULL,           -- Date of transaction
    sale_hour       INT             NOT NULL,           -- Hour of day (0–23)
    units_sold      INT             NOT NULL,           -- Number of units in this transaction
    revenue         DECIMAL(10, 2)  NOT NULL,           -- Revenue = units_sold * price
    discount_pct    DECIMAL(5, 2)   DEFAULT 0.00,       -- Discount applied (%)
    FOREIGN KEY (product_id) REFERENCES dim_products(product_id)
);

-- -------------------------------------------------------
-- TABLE 3: fact_web_logs
-- Captures website error logs hour by hour.
-- Used by the agent to correlate revenue drops with
-- technical issues (e.g., 404s, 500s, timeouts).
-- -------------------------------------------------------
CREATE TABLE fact_web_logs (
    log_id          SERIAL          PRIMARY KEY,        -- Auto-incrementing log ID
    log_date        DATE            NOT NULL,           -- Date of the log entry
    log_hour        INT             NOT NULL,           -- Hour bucket (0–23)
    error_type      VARCHAR(50)     NOT NULL,           -- e.g. '404_NOT_FOUND', '500_SERVER_ERROR'
    error_count     INT             NOT NULL,           -- How many errors in that hour
    affected_page   VARCHAR(100)    NOT NULL,           -- Which page/endpoint was affected
    server_id       VARCHAR(20)     NOT NULL            -- Which server threw the error
);

-- -------------------------------------------------------
-- USEFUL QUERIES (run these to explore the data)
-- -------------------------------------------------------

-- Q1: Daily revenue summary per product
-- SELECT
--     s.sale_date,
--     p.product_name,
--     SUM(s.revenue) AS daily_revenue,
--     SUM(s.units_sold) AS daily_units
-- FROM fact_sales s
-- JOIN dim_products p ON s.product_id = p.product_id
-- GROUP BY s.sale_date, p.product_name
-- ORDER BY s.sale_date;

-- Q2: Find error spikes on a specific date/hour
-- SELECT log_date, log_hour, error_type, SUM(error_count) AS total_errors
-- FROM fact_web_logs
-- WHERE log_date = '2024-01-15'
-- GROUP BY log_date, log_hour, error_type
-- ORDER BY log_hour;

-- Q3: Correlate revenue with errors (the key agent query)
-- SELECT
--     s.sale_date,
--     s.sale_hour,
--     SUM(s.revenue) AS hourly_revenue,
--     COALESCE(SUM(w.error_count), 0) AS total_errors
-- FROM fact_sales s
-- LEFT JOIN fact_web_logs w
--     ON s.sale_date = w.log_date AND s.sale_hour = w.log_hour
-- GROUP BY s.sale_date, s.sale_hour
-- ORDER BY s.sale_date, s.sale_hour;
