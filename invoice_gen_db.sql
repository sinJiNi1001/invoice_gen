-- =====================================================
-- 1. RESET DATABASE (CLEAN SLATE)
-- =====================================================
DROP DATABASE IF EXISTS invoice_generator;
CREATE DATABASE invoice_generator;
USE invoice_generator;

-- =====================================================
-- 2. CREATE TABLES (ALL MODULES)
-- =====================================================

-- 2.1 USERS & ROLES
CREATE TABLE roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100),
    email VARCHAR(100) UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role_id INT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- 2.2 CUSTOMERS (With GST, Address, & Contact fields)
CREATE TABLE customers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(150) NOT NULL,
    
    -- Contact Details
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    deal_owner VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20),
    
    -- Address & Tax
    address VARCHAR(150),
    city VARCHAR(50),
    state VARCHAR(50),
    country VARCHAR(50),
    
    -- GST / Tax Info
    gst_number VARCHAR(50), 
    gst_status ENUM('Registered', 'No_Forex', 'No_SEZ') DEFAULT 'Registered',
    gst_type ENUM('CGST_SGST', 'IGST') DEFAULT NULL,
    currency VARCHAR(10) DEFAULT 'INR',
    
    -- Metadata
    joined_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2.3 SERVICES (With Service ID & Description)
CREATE TABLE services (
    id INT AUTO_INCREMENT PRIMARY KEY,
    service_id VARCHAR(50),      
    service_name VARCHAR(150) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

-- 2.4 PROJECTS (Legacy Module)
CREATE TABLE projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT,
    project_name VARCHAR(150) NOT NULL,
    total_value DECIMAL(12, 2),
    payment_type VARCHAR(30),
    status ENUM('Active', 'Completed', 'On Hold', 'Cancelled') DEFAULT 'Active',
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

CREATE TABLE payment_slabs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT,
    slab_name VARCHAR(100),
    percentage DECIMAL(5, 2),
    amount DECIMAL(12, 2),
    due_condition VARCHAR(50) DEFAULT 'Immediate',
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- 2.5 CONTRACTS (New Module)
CREATE TABLE contracts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    contract_name VARCHAR(150) NOT NULL,
    po_reference VARCHAR(255),
    total_value DECIMAL(15, 2) NOT NULL,
    start_date DATE,
    end_date DATE,
    status ENUM('Draft', 'Active', 'On Hold', 'Completed', 'Terminated') DEFAULT 'Draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

CREATE TABLE contract_slabs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    contract_id INT NOT NULL,
    slab_name VARCHAR(100),
    amount DECIMAL(15, 2),
    due_date DATE,
    status ENUM('Pending', 'Invoiced', 'Paid') DEFAULT 'Pending',
    due_condition VARCHAR(50) DEFAULT 'Immediate',
    FOREIGN KEY (contract_id) REFERENCES contracts(id) ON DELETE CASCADE
);

-- 2.6 INVOICES (Linked to EVERYTHING)
CREATE TABLE invoices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    customer_id INT,
    
    -- Links (Supports both Projects and Contracts)
    project_id INT,
    contract_id INT,
    contract_slab_id INT,
    
    -- Invoice Details
    invoice_date DATE,
    due_date DATE,
    invoice_amount DECIMAL(12, 2),
    tax_type VARCHAR(20),
    tax_amount DECIMAL(12, 2),
    total_amount DECIMAL(12, 2),
    
    -- Payment Tracking
    amount_received DECIMAL(12, 2) DEFAULT 0.00,
    received_date DATE,
    billing_type VARCHAR(20) DEFAULT 'Full Payment',
    
    status ENUM('Draft', 'Raised', 'Unpaid', 'Partially Paid', 'Paid', 'Cancelled', 'Overdue') DEFAULT 'Draft',
    pdf_path TEXT,
    excel_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (contract_id) REFERENCES contracts(id)
);

-- =====================================================
-- 3. POPULATE DATA
-- =====================================================

-- 3.1 Roles & Admin User
INSERT INTO roles (role_name) VALUES ('Admin'), ('Employee');
INSERT INTO users (full_name, email, password, role_id) 
VALUES ('Admin User', 'admin@valency.com', 'admin123', 1);

-- 3.2 Full Service Catalog
INSERT INTO services (service_name, description) VALUES 
('Web Application VAPT', 'Vulnerability Assessment and Penetration Testing'),
('Cloud Application VAPT', 'Security assessment for cloud infrastructure'),
('Mobile Application VAPT', 'Android and iOS security testing'),
('API VAPT', 'REST and SOAP API security testing'),
('Network VAPT', 'Internal and External Network Security'),
('Network Audit', 'Configuration and architecture review'),
('Firewall Configuration Audit', 'Rule base and compliance review'),
('IOT Device VAPT', 'Internet of Things security assessment'),
('OT Security Audit', 'Operational Technology security review'),
('ISO27001 Internal Audit', 'Compliance audit'),
('ISO27001 Consultancy', 'Implementation support'),
('ISA 62443 4-1 & 4-2 Assessment', 'Industrial automation control system security'),
('PCI DSS Consultancy', 'Payment card industry security standards'),
('TISAX Implementation', 'Automotive information security'),
('HIPAA Compliance Consultancy', 'Healthcare data protection'),
('GDPR Implementation Consultancy', 'Data privacy compliance'),
('Phishing Simulation', 'Social engineering testing'),
('vCISO Service', 'Virtual Chief Information Security Officer'),
('Red Teaming', 'Adversary simulation');

-- 3.3 PREVIOUS CLIENTS (Pune CyberPark, Global Shield, Bangalore Tech Hub)
INSERT INTO customers (company_name, deal_owner, gst_status, gst_type, gst_number, country, currency, email, phone, address, city, state) 
VALUES 
-- 1. Pune CyberPark (Local MH Client -> CGST_SGST)
('Pune CyberPark Pvt Ltd', 'xxx', 'Registered', 'CGST_SGST', '27AAACP1234A1Z1', 'India', 'INR', 'finance@cyberpark.in', '9876543210', 'Magarpatta City', 'Pune', 'Maharashtra'),

-- 2. Global Shield (USA Client -> No_Forex)
('Global Shield Inc', 'Rahul', 'No_Forex', NULL, NULL, 'USA', 'USD', 'billing@globalshield.com', '+1-555-0199', '101 Silicon Valley', 'California', 'CA'),

-- 3. Bangalore Tech Hub (Karnataka Client -> IGST)
('Bangalore Tech Hub', 'qrt', 'Registered', 'IGST', '29BBBCS5678B2Z2', 'India', 'INR', 'accounts@bth.com', '9988776655', 'Electronic City', 'Bangalore', 'Karnataka');

-- 3.4 Dummy Project
INSERT INTO projects (customer_id, project_name, total_value) 
VALUES (1, 'Cloud Security Audit', 500000.00);

USE invoice_generator;

-- 1. Unlock Safe Mode
SET SQL_SAFE_UPDATES = 0;

-- 2. Run the Updates
UPDATE services SET service_id = 'VAPT-WEB' WHERE service_name = 'Web Application VAPT';
UPDATE services SET service_id = 'VAPT-CLOUD' WHERE service_name = 'Cloud Application VAPT';
UPDATE services SET service_id = 'VAPT-MOB' WHERE service_name = 'Mobile Application VAPT';
UPDATE services SET service_id = 'VAPT-API' WHERE service_name = 'API VAPT';
UPDATE services SET service_id = 'VAPT-NET' WHERE service_name = 'Network VAPT';
UPDATE services SET service_id = 'VAPT-IOT' WHERE service_name = 'IOT Device VAPT';
UPDATE services SET service_id = 'AUDIT-NET' WHERE service_name = 'Network Audit';
UPDATE services SET service_id = 'AUDIT-FW' WHERE service_name = 'Firewall Configuration Audit';

UPDATE services SET service_id = 'OT-SEC' WHERE service_name = 'OT Security Audit';
UPDATE services SET service_id = 'ISA-62443' WHERE service_name = 'ISA 62443 4-1 & 4-2 Assessment';

UPDATE services SET service_id = 'GRC-ISO-IA' WHERE service_name = 'ISO27001 Internal Audit';
UPDATE services SET service_id = 'GRC-ISO-IM' WHERE service_name = 'ISO27001 Consultancy';
UPDATE services SET service_id = 'GRC-PCI' WHERE service_name = 'PCI DSS Consultancy';
UPDATE services SET service_id = 'GRC-TISAX' WHERE service_name = 'TISAX Implementation';
UPDATE services SET service_id = 'GRC-HIPAA' WHERE service_name = 'HIPAA Compliance Consultancy';
UPDATE services SET service_id = 'GRC-GDPR' WHERE service_name = 'GDPR Implementation Consultancy';

UPDATE services SET service_id = 'SEC-PHISH' WHERE service_name = 'Phishing Simulation';
UPDATE services SET service_id = 'SEC-VCISO' WHERE service_name = 'vCISO Service';
UPDATE services SET service_id = 'SEC-RED' WHERE service_name = 'Red Teaming';

-- 3. Lock Safe Mode again (Good practice)
SET SQL_SAFE_UPDATES = 1;