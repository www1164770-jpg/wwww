-- Focused migration for the V1 questionnaire fields on users.
-- Each column is checked in information_schema before the only permitted DDL
-- (ALTER TABLE users ADD COLUMN) is executed.

SET @schema_name = DATABASE();

SET @column_exists = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = @schema_name
      AND table_name = 'users'
      AND column_name = 'questionnaire_completed'
);
SET @migration_sql = IF(
    @column_exists = 0,
    'ALTER TABLE `users` ADD COLUMN `questionnaire_completed` TINYINT(1) DEFAULT 0',
    'SELECT ''users.questionnaire_completed already exists'' AS migration_status'
);
PREPARE migration_statement FROM @migration_sql;
EXECUTE migration_statement;
DEALLOCATE PREPARE migration_statement;

SET @column_exists = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = @schema_name
      AND table_name = 'users'
      AND column_name = 'has_survey'
);
SET @migration_sql = IF(
    @column_exists = 0,
    'ALTER TABLE `users` ADD COLUMN `has_survey` TINYINT DEFAULT 0',
    'SELECT ''users.has_survey already exists'' AS migration_status'
);
PREPARE migration_statement FROM @migration_sql;
EXECUTE migration_statement;
DEALLOCATE PREPARE migration_statement;

SET @column_exists = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = @schema_name
      AND table_name = 'users'
      AND column_name = 'user_tags'
);
SET @migration_sql = IF(
    @column_exists = 0,
    'ALTER TABLE `users` ADD COLUMN `user_tags` VARCHAR(500) DEFAULT NULL',
    'SELECT ''users.user_tags already exists'' AS migration_status'
);
PREPARE migration_statement FROM @migration_sql;
EXECUTE migration_statement;
DEALLOCATE PREPARE migration_statement;

SET @column_exists = (
    SELECT COUNT(*)
    FROM information_schema.columns
    WHERE table_schema = @schema_name
      AND table_name = 'users'
      AND column_name = 'interests'
);
SET @migration_sql = IF(
    @column_exists = 0,
    'ALTER TABLE `users` ADD COLUMN `interests` VARCHAR(500) DEFAULT NULL',
    'SELECT ''users.interests already exists'' AS migration_status'
);
PREPARE migration_statement FROM @migration_sql;
EXECUTE migration_statement;
DEALLOCATE PREPARE migration_statement;
