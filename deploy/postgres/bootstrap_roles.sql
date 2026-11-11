-- Bootstrap database roles and permissions

-- Create application runtime role (non-superuser)
CREATE ROLE app_runtime WITH
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    CONNECTION LIMIT 20;

-- Set password (will be overridden by environment in production)
ALTER ROLE app_runtime WITH PASSWORD 'changeme';

-- Grant necessary privileges
GRANT CONNECT ON DATABASE muscle_training TO app_runtime;

-- Create schema and set ownership
CREATE SCHEMA IF NOT EXISTS public;
GRANT USAGE, CREATE ON SCHEMA public TO app_runtime;

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant execute on vector functions
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO app_runtime;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_runtime;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO app_runtime;

-- Create migration tracking table if it doesn't exist
-- (Alembic will manage this, but we ensure basic structure)
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

GRANT SELECT, INSERT, UPDATE, DELETE ON alembic_version TO app_runtime;
