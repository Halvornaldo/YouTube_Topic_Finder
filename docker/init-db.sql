-- Initialize YouTube Topic Finder database
-- This script runs on first container startup

-- Create database (already created by POSTGRES_DB env var, but included for reference)
-- CREATE DATABASE youtube_topic_finder;

-- Set timezone
SET timezone = 'UTC';

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE youtube_topic_finder TO postgres;

-- Log initialization
DO $$
BEGIN
  RAISE NOTICE 'YouTube Topic Finder database initialized successfully';
END $$;
