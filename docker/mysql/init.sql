-- MySQL init script for stock_data database
-- Executed on first container startup

CREATE DATABASE IF NOT EXISTS stock_data
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- Create application user (matches .env credentials)
CREATE USER IF NOT EXISTS 'admin'@'%' IDENTIFIED BY 'ZggDLAXkkHXFwQVM';
GRANT ALL PRIVILEGES ON stock_data.* TO 'admin'@'%';
FLUSH PRIVILEGES;
