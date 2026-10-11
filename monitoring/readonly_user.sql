-- Read-only database login for Metabase / ad-hoc analysis. It can read project data but cannot change anything.
-- Run once as the database owner. Replace the password. Schema "pms" is the one this app uses on Render.
CREATE ROLE pms_readonly LOGIN PASSWORD 'replace-with-a-long-random-password';
GRANT CONNECT ON DATABASE postgres TO pms_readonly;   -- use your real database name instead of "postgres"
GRANT USAGE ON SCHEMA pms TO pms_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA pms TO pms_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA pms GRANT SELECT ON TABLES TO pms_readonly;
-- Hide password hashes and login data from this role:
REVOKE SELECT ON pms.accounts_user, pms.accounts_historicaluser FROM pms_readonly;
GRANT SELECT (id, username, first_name, last_name, email, role, is_active, weekly_capacity_hours, date_joined)
  ON pms.accounts_user TO pms_readonly;
-- Point the role at the app schema by default
ALTER ROLE pms_readonly SET search_path = pms;
