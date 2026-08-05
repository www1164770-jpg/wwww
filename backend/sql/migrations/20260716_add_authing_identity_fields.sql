-- DEPRECATED: historical Authing identity migration retained for existing databases.
-- The application no longer uses this provider; do not add new runtime dependencies.
-- Back up the target database before executing this file.

SET @schema_name = DATABASE();

SET @authing_sub_exists = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = @schema_name
      AND table_name = 'users'
      AND column_name = 'authing_sub'
);
SET @migration_sql = IF(
    @authing_sub_exists = 0,
    'ALTER TABLE `users` ADD COLUMN `authing_sub` VARCHAR(128) NULL',
    'SELECT ''users.authing_sub already exists'' AS migration_status'
);
PREPARE migration_statement FROM @migration_sql;
EXECUTE migration_statement;
DEALLOCATE PREPARE migration_statement;

SET @login_provider_exists = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = @schema_name
      AND table_name = 'users'
      AND column_name = 'login_provider'
);
SET @migration_sql = IF(
    @login_provider_exists = 0,
    'ALTER TABLE `users` ADD COLUMN `login_provider` VARCHAR(50) DEFAULT ''local''',
    'SELECT ''users.login_provider already exists'' AS migration_status'
);
PREPARE migration_statement FROM @migration_sql;
EXECUTE migration_statement;
DEALLOCATE PREPARE migration_statement;

SET @authing_sub_unique_exists = (
    SELECT COUNT(*)
    FROM information_schema.statistics AS authing_index
    WHERE authing_index.table_schema = @schema_name
      AND authing_index.table_name = 'users'
      AND authing_index.column_name = 'authing_sub'
      AND authing_index.non_unique = 0
      AND (
          SELECT COUNT(*)
          FROM information_schema.statistics AS index_columns
          WHERE index_columns.table_schema = authing_index.table_schema
            AND index_columns.table_name = authing_index.table_name
            AND index_columns.index_name = authing_index.index_name
      ) = 1
);
SET @migration_sql = IF(
    @authing_sub_unique_exists = 0,
    'ALTER TABLE `users` ADD UNIQUE INDEX `uq_users_authing_sub` (`authing_sub`)',
    'SELECT ''users.authing_sub unique index already exists'' AS migration_status'
);
PREPARE migration_statement FROM @migration_sql;
EXECUTE migration_statement;
DEALLOCATE PREPARE migration_statement;
