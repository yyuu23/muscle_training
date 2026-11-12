-- Bootstrap database roles and permissions (plan §9.3)
-- Runs once on first container init (docker-entrypoint-initdb.d).
-- Idempotent and database-name agnostic: grants target CURRENT_DATABASE().

-- ---------------------------------------------------------------- app_runtime
-- Normal API role: non-superuser, not table owner, NOBYPASSRLS.
CREATE ROLE app_runtime WITH
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS
    CONNECTION LIMIT 20;
ALTER ROLE app_runtime WITH PASSWORD 'app_runtime_dev_password';

-- ---------------------------------------------------------------- migration_role
-- Runs alembic migrations only.
CREATE ROLE migration_role WITH
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    CONNECTION LIMIT 5;
ALTER ROLE migration_role WITH PASSWORD 'migration_dev_password';

-- ---------------------------------------------------------------- job_dispatcher
-- Worker: claims job metadata; re-scopes to owners for private data.
CREATE ROLE job_dispatcher WITH
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    CONNECTION LIMIT 10;
ALTER ROLE job_dispatcher WITH PASSWORD 'job_dispatcher_dev_password';

-- ---------------------------------------------------------------- backup_role
-- Read-only backup access; used only by the backup service.
CREATE ROLE backup_role WITH
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    CONNECTION LIMIT 5;
ALTER ROLE backup_role WITH PASSWORD 'backup_dev_password';

-- ---------------------------------------------------------------- grants
-- Database-level CONNECT on whatever database this script initializes
-- (muscle_training_dev in compose; the production DB in deployment).
DO $$
BEGIN
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO app_runtime', current_database());
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO migration_role', current_database());
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO job_dispatcher', current_database());
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO backup_role', current_database());
END $$;

-- Schema privileges (public schema already exists; entrypoint user owns it)
GRANT USAGE, CREATE ON SCHEMA public TO app_runtime;
GRANT USAGE, CREATE ON SCHEMA public TO migration_role;
GRANT USAGE ON SCHEMA public TO job_dispatcher;
GRANT USAGE ON SCHEMA public TO backup_role;

-- pgvector extension (applications create it via migrations with IF NOT EXISTS;
-- pre-creating here lets non-superuser roles use its functions immediately)
CREATE EXTENSION IF NOT EXISTS vector;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO app_runtime;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO job_dispatcher;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO backup_role;

-- Default privileges for future objects created by the entrypoint owner
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_runtime;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO job_dispatcher;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO migration_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO backup_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO app_runtime;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO job_dispatcher;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO migration_role;

-- NOTE: alembic_version is owned and created by alembic itself; do not
-- pre-create it here (a wrong column spec breaks upgrade detection).
