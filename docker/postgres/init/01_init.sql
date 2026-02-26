-- ============================================
-- Cameroon House Immatriculation System
-- Database Initialization Script
-- ============================================

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create application schema
CREATE SCHEMA IF NOT EXISTS immatriculation;

-- Set default search path
ALTER DATABASE immatriculation SET search_path TO immatriculation, public;

-- Grant permissions
GRANT ALL ON SCHEMA immatriculation TO immat_user;
GRANT USAGE ON SCHEMA public TO immat_user;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Database initialized: PostGIS enabled, schema created';
END $$;
