DROP DATABASE IF EXISTS invoice_app;

-- Delete the new database (if you created it partially and want to reset)
DROP DATABASE IF EXISTS invoice_generator;

-- Now, you are ready to run the new "invoice_generator.sql" script.
CREATE DATABASE invoice_generator;

-- 1. Roles Table
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL
);

INSERT INTO roles (role_name) VALUES 
('Admin'), 
('Employee'), 
('CA');

SELECT * FROM roles;


CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(100),
    email VARCHAR(100) UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role_id INT REFERENCES roles(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (full_name, email, password, role_id) VALUES
('Admin User', 'admin@gmail.com', 'admin123', 1);
SELECT * FROM users;

CREATE TABLE country_currency (
    country_name VARCHAR(100) PRIMARY KEY,
    currency_code VARCHAR(10) NOT NULL,
    tax_label VARCHAR(20) DEFAULT 'Tax ID' -- e.g., GST for India, VAT for UK
);
INSERT INTO country_currency (country_name, currency_code, tax_label) VALUES 
('India', 'INR', 'GSTIN'),
('USA', 'USD', 'Tax ID'),
('UK', 'GBP', 'VAT No');
select *from country_currency;

CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(150) NOT NULL,
    country VARCHAR(50),
    email VARCHAR(100),
    phone VARCHAR(20),
    address TEXT,
    tax_id VARCHAR(50),
    currency VARCHAR(10),
    created_by INT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Maharashtra (Local GST test)
INSERT INTO customers (company_name, country, tax_id, currency, email, address) 
VALUES ('Pune CyberPark Pvt Ltd', 'India', '27AAACP1234A1Z1', 'INR', 'finance@cyberpark.in', 'Magarpatta City, Pune, MH');

-- Karnataka (IGST test)
INSERT INTO customers (company_name, country, tax_id, currency, email, address) 
VALUES ('Bangalore Tech Hub', 'India', '29BBBCS5678B2Z2', 'INR', 'accounts@bth.com', 'Electronic City, Bangalore, KA');

-- USA (Zero Tax / Export test)
INSERT INTO customers (company_name, country, tax_id, currency, email, address) 
VALUES ('Global Shield Inc', 'USA', 'US-99887766', 'USD', 'billing@globalshield.com', '101 Silicon Valley, CA, USA');
Select *from customers;


CREATE TABLE services (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE
);
INSERT INTO services (service_name, description) 
VALUES ('VAPT', 'Vulnerability Assessment and Penetration Testing');

INSERT INTO services (service_name, description) 
VALUES ('Cloud VAPT', 'Advanced Cloud Vulnerability Assessment');
select *from services;



CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(id) ON DELETE CASCADE,
    service_id INT REFERENCES services(id),
    project_name VARCHAR(150) NOT NULL,
    project_description TEXT,
    start_date DATE,
    total_value NUMERIC(12,2) NOT NULL,
    currency VARCHAR(10),
    payment_type VARCHAR(30) CHECK (payment_type IN ('FULL', 'MILESTONE')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Project for Customer 1 (Cloud Migration)
INSERT INTO projects (customer_id, service_id, project_name, total_value, currency, payment_type) 
VALUES (1, 1, 'Project Alpha: Cloud Security', 500000.00, 'INR', 'MILESTONE');

-- Project for Customer 3 (Web Security)
INSERT INTO projects (customer_id, service_id, project_name, total_value, currency, payment_type) 
VALUES (3, 1, 'Global Web Audit', 5000.00, 'USD', 'FULL');

select *from projects;


CREATE TABLE payment_slabs (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES projects(id) ON DELETE CASCADE,
    slab_name VARCHAR(100),
    percentage NUMERIC(5,2),
    amount NUMERIC(12,2),
    due_condition VARCHAR(50), 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Slabs for Project 1
INSERT INTO payment_slabs (project_id, slab_name, percentage, amount, due_condition) VALUES 
(1, 'Advance Milestone (20%)', 20.00, 100000.00, 'Kickoff'),
(1, 'Interim Report Milestone (40%)', 40.00, 200000.00, 'On Interim Report'),
(1, 'Final Certificate Milestone (40%)', 40.00, 200000.00, 'Completion');
SELECT * FROM payment_slabs;

CREATE TABLE invoices (
    id SERIAL PRIMARY KEY,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    customer_id INT REFERENCES customers(id),
    project_id INT REFERENCES projects(id),
    slab_id INT REFERENCES payment_slabs(id),
    invoice_date DATE,
    due_date DATE,
    invoice_amount NUMERIC(12,2),
    tax_type VARCHAR(20), -- GST / IGST / NONE
    tax_amount NUMERIC(12,2),
    total_amount NUMERIC(12,2),
    status VARCHAR(30) CHECK (
        status IN ('Draft','Raised','Unpaid','Partially Paid','Paid','Overdue')
    ),
    pdf_path TEXT,
    excel_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- A Paid Invoice
INSERT INTO invoices (invoice_number, customer_id, project_id, slab_id, invoice_date, due_date, invoice_amount, tax_type, tax_amount, total_amount, status) 
VALUES ('VAL/2026/001', 1, 1, 1, '2026-01-01', '2026-01-15', 100000.00, 'GST', 18000.00, 118000.00, 'Paid');

-- An Unpaid/Raised Invoice
INSERT INTO invoices (invoice_number, customer_id, project_id, slab_id, invoice_date, due_date, invoice_amount, tax_type, tax_amount, total_amount, status) 
VALUES ('VAL/2026/002', 2, 2, NULL, '2026-01-20', '2026-02-05', 15000.00, 'IGST', 2700.00, 17700.00, 'Raised');

INSERT INTO invoices (invoice_number, customer_id, project_id, slab_id, invoice_date, due_date, invoice_amount, tax_type, tax_amount, total_amount, status) 
VALUES ('VAL/2026/INT-01', 3, 3, NULL, '2025-12-01', '2025-12-15', 5000.00, 'NONE', 0.00, 5000.00, 'Overdue');
SELECT * FROM invoices;



USE invoice_generator;

CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL
);

INSERT INTO roles (role_name) VALUES 
('Admin'), 
('Employee'), 
('CA');

SELECT * FROM roles;


CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(100),
    email VARCHAR(100) UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role_id INT REFERENCES roles(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (full_name, email, password, role_id) VALUES
('Admin User', 'admin@gmail.com', 'admin123', 1);
SELECT * FROM users;

CREATE TABLE country_currency (
    country_name VARCHAR(100) PRIMARY KEY,
    currency_code VARCHAR(10) NOT NULL,
    tax_label VARCHAR(20) DEFAULT 'Tax ID' -- e.g., GST for India, VAT for UK
);
INSERT INTO country_currency (country_name, currency_code, tax_label) VALUES 
('India', 'INR', 'GSTIN'),
('USA', 'USD', 'Tax ID'),
('UK', 'GBP', 'VAT No');
select *from country_currency;

CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(150) NOT NULL,
    country VARCHAR(50),
    email VARCHAR(100),
    phone VARCHAR(20),
    address TEXT,
    tax_id VARCHAR(50),
    currency VARCHAR(10),
    created_by INT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Maharashtra (Local GST test)
INSERT INTO customers (company_name, country, tax_id, currency, email, address) 
VALUES ('Pune CyberPark Pvt Ltd', 'India', '27AAACP1234A1Z1', 'INR', 'finance@cyberpark.in', 'Magarpatta City, Pune, MH');

-- Karnataka (IGST test)
INSERT INTO customers (company_name, country, tax_id, currency, email, address) 
VALUES ('Bangalore Tech Hub', 'India', '29BBBCS5678B2Z2', 'INR', 'accounts@bth.com', 'Electronic City, Bangalore, KA');

-- USA (Zero Tax / Export test)
INSERT INTO customers (company_name, country, tax_id, currency, email, address) 
VALUES ('Global Shield Inc', 'USA', 'US-99887766', 'USD', 'billing@globalshield.com', '101 Silicon Valley, CA, USA');
Select *from customers;


CREATE TABLE services (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE
);
INSERT INTO services (service_name, description) 
VALUES ('VAPT', 'Vulnerability Assessment and Penetration Testing');

INSERT INTO services (service_name, description) 
VALUES ('Cloud VAPT', 'Advanced Cloud Vulnerability Assessment');
select *from services;



CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(id) ON DELETE CASCADE,
    service_id INT REFERENCES services(id),
    project_name VARCHAR(150) NOT NULL,
    project_description TEXT,
    start_date DATE,
    total_value NUMERIC(12,2) NOT NULL,
    currency VARCHAR(10),
    payment_type VARCHAR(30) CHECK (payment_type IN ('FULL', 'MILESTONE')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Project for Customer 1 (Cloud Migration)
INSERT INTO projects (customer_id, service_id, project_name, total_value, currency, payment_type) 
VALUES (1, 1, 'Project Alpha: Cloud Security', 500000.00, 'INR', 'MILESTONE');

-- Project for Customer 3 (Web Security)
INSERT INTO projects (customer_id, service_id, project_name, total_value, currency, payment_type) 
VALUES (3, 1, 'Global Web Audit', 5000.00, 'USD', 'FULL');

select *from projects;


CREATE TABLE payment_slabs (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES projects(id) ON DELETE CASCADE,
    slab_name VARCHAR(100),
    percentage NUMERIC(5,2),
    amount NUMERIC(12,2),
    due_condition VARCHAR(50), 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- Slabs for Project 1
INSERT INTO payment_slabs (project_id, slab_name, percentage, amount, due_condition) VALUES 
(1, 'Advance Milestone (20%)', 20.00, 100000.00, 'Kickoff'),
(1, 'Interim Report Milestone (40%)', 40.00, 200000.00, 'On Interim Report'),
(1, 'Final Certificate Milestone (40%)', 40.00, 200000.00, 'Completion');
SELECT * FROM payment_slabs;

CREATE TABLE invoices (
    id SERIAL PRIMARY KEY,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    customer_id INT REFERENCES customers(id),
    project_id INT REFERENCES projects(id),
    slab_id INT REFERENCES payment_slabs(id),
    invoice_date DATE,
    due_date DATE,
    invoice_amount NUMERIC(12,2),
    tax_type VARCHAR(20), -- GST / IGST / NONE
    tax_amount NUMERIC(12,2),
    total_amount NUMERIC(12,2),
    status VARCHAR(30) CHECK (
        status IN ('Draft','Raised','Unpaid','Partially Paid','Paid','Overdue')
    ),
    pdf_path TEXT,
    excel_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- A Paid Invoice
INSERT INTO invoices (invoice_number, customer_id, project_id, slab_id, invoice_date, due_date, invoice_amount, tax_type, tax_amount, total_amount, status) 
VALUES ('VAL/2026/001', 1, 1, 1, '2026-01-01', '2026-01-15', 100000.00, 'GST', 18000.00, 118000.00, 'Paid');

-- An Unpaid/Raised Invoice
INSERT INTO invoices (invoice_number, customer_id, project_id, slab_id, invoice_date, due_date, invoice_amount, tax_type, tax_amount, total_amount, status) 
VALUES ('VAL/2026/002', 2, 2, NULL, '2026-01-20', '2026-02-05', 15000.00, 'IGST', 2700.00, 17700.00, 'Raised');

INSERT INTO invoices (invoice_number, customer_id, project_id, slab_id, invoice_date, due_date, invoice_amount, tax_type, tax_amount, total_amount, status) 
VALUES ('VAL/2026/INT-01', 3, 3, NULL, '2025-12-01', '2025-12-15', 5000.00, 'NONE', 0.00, 5000.00, 'Overdue');
SELECT * FROM invoices;

USE invoice_generator;

-- Ensure Slabs have the 'due_condition' field
ALTER TABLE payment_slabs ADD COLUMN IF NOT EXISTS due_condition VARCHAR(50) DEFAULT 'Immediate';

-- Update Invoice Status ENUM to match requirements
ALTER TABLE invoices MODIFY COLUMN status ENUM('Draft', 'Raised', 'Paid', 'Partially Paid', 'Unpaid') DEFAULT 'Draft';

USE invoice_generator;

-- 1. Add the due_condition column (removed 'IF NOT EXISTS')
ALTER TABLE payment_slabs ADD COLUMN due_condition VARCHAR(50) DEFAULT 'Immediate';

-- 2. Update the Status options for Invoices
ALTER TABLE invoices MODIFY COLUMN status ENUM('Draft', 'Raised', 'Paid', 'Partially Paid', 'Unpaid') DEFAULT 'Draft';
SELECT * FROM invoices;

USE invoice_generator;

CREATE TABLE IF NOT EXISTS customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(150) NOT NULL,
    country VARCHAR(50) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20),
    address TEXT,
    tax_id VARCHAR(50),
    currency VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

USE invoice_generator;

CREATE TABLE IF NOT EXISTS projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    project_name VARCHAR(150) NOT NULL,
    total_value DECIMAL(15,2) DEFAULT 0.00,
    status ENUM('Active', 'Completed', 'On Hold') DEFAULT 'Active',
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);
USE invoice_generator;

ALTER TABLE projects
ADD COLUMN status ENUM('Active', 'Completed', 'On Hold') DEFAULT 'Active';

USE invoice_generator;

-- 1. Rename 'tax_id' to 'gst_number'
ALTER TABLE customers CHANGE COLUMN tax_id gst_number VARCHAR(50);

-- 2. Add the 'deal_owner' column
ALTER TABLE customers ADD COLUMN deal_owner VARCHAR(100) AFTER company_name;

-- 3. Add the 'gst_type' dropdown logic
ALTER TABLE customers ADD COLUMN gst_type ENUM('Yes', 'No_Forex', 'No_SEZ') DEFAULT 'Yes' AFTER deal_owner;

USE invoice_generator;

-- Update the status options to include 'Duped', 'Cancel', etc.
ALTER TABLE projects MODIFY COLUMN status ENUM('Active', 'Duped', 'Cancel', 'On Hold', 'Complete') DEFAULT 'Active';

USE invoice_generator;

-- 1. Create the Customers table FIRST
CREATE TABLE IF NOT EXISTS customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(150) NOT NULL,
    deal_owner VARCHAR(100),
    gst_type ENUM('Yes', 'No_Forex', 'No_SEZ') DEFAULT 'Yes',
    gst_number VARCHAR(50),
    country VARCHAR(50),
    currency VARCHAR(10) DEFAULT 'INR',
    email VARCHAR(100),
    phone VARCHAR(20),
    address TEXT
);

-- 2. NOW create the Projects table
CREATE TABLE IF NOT EXISTS projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    project_name VARCHAR(150) NOT NULL,
    total_value DECIMAL(15,2) DEFAULT 0.00,
    status ENUM('Active', 'Duped', 'Cancel', 'On Hold', 'Complete') DEFAULT 'Active',
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

SHOW TABLES;
DESCRIBE projects;

DESCRIBE customers;

SELECT * FROM customers;

SELECT * FROM invoice_generator.customers;

USE invoice_generator;

-- 1. Insert Test Customers (with new columns like deal_owner, gst_type)
INSERT INTO customers (company_name, deal_owner, gst_type, gst_number, country, currency, email, phone, address) 
VALUES 
('Pune CyberPark Pvt Ltd', 'xxx', 'Yes', '27AAACP1234A1Z1', 'India', 'INR', 'finance@cyberpark.in', '9876543210', 'Magarpatta City, Pune, MH'),
('Global Shield Inc', 'Rahul', 'No_Forex', NULL, 'USA', 'USD', 'billing@globalshield.com', '+1-555-0199', '101 Silicon Valley, CA, USA'),
('Bangalore Tech Hub', 'qrt', 'Yes', '29BBBCS5678B2Z2', 'India', 'INR', 'accounts@bth.com', '9988776655', 'Electronic City, Bangalore, KA');

-- 2. Insert Test Projects (with new status options)
-- Get IDs dynamically to avoid errors if IDs aren't 1, 2, 3
INSERT INTO projects (customer_id, project_name, total_value, status) 
VALUES 
((SELECT id FROM customers WHERE company_name='Pune CyberPark Pvt Ltd'), 'Cloud Security Audit', 500000.00, 'Active'),
((SELECT id FROM customers WHERE company_name='Pune CyberPark Pvt Ltd'), 'Annual VAPT', 250000.00, 'On Hold'),
((SELECT id FROM customers WHERE company_name='Global Shield Inc'), 'Web App Pentest', 5000.00, 'Complete'),
((SELECT id FROM customers WHERE company_name='Bangalore Tech Hub'), 'Network Hardening', 150000.00, 'Duped');

SELECT * FROM customers;

USE invoice_generator;

-- Add the new date column (Defaults to today if left empty)
ALTER TABLE customers ADD COLUMN joined_date DATE DEFAULT (CURRENT_DATE);

-- Optional: Update existing dummy data to have a date so they don't look broken
UPDATE customers SET joined_date = '2025-01-15' WHERE id > 0;

USE invoice_generator;

-- Add PO/Reference Number column
ALTER TABLE customers ADD COLUMN po_ref VARCHAR(100);

-- Add Notes column
ALTER TABLE customers ADD COLUMN notes TEXT;