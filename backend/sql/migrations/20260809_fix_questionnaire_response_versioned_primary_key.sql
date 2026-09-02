-- Upgrade installations created before versioned questionnaire responses could
-- retain history. Run after 20260809_add_questionnaire_v2_responses.sql.
--
-- The independent id primary key permits one user to retain a response for
-- each questionnaire version, while the unique key keeps each version's
-- response idempotent.

SET @questionnaire_schema = DATABASE();

SET @questionnaire_id_exists = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @questionnaire_schema
    AND table_name = 'user_questionnaire_responses'
    AND column_name = 'id'
);

SET @questionnaire_fix_primary_key_sql = IF(
  @questionnaire_id_exists = 0,
  'ALTER TABLE user_questionnaire_responses DROP PRIMARY KEY, ADD COLUMN id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST',
  'SELECT ''user_questionnaire_responses already has an id primary key'' AS migration_status'
);
PREPARE questionnaire_fix_primary_key_statement FROM @questionnaire_fix_primary_key_sql;
EXECUTE questionnaire_fix_primary_key_statement;
DEALLOCATE PREPARE questionnaire_fix_primary_key_statement;

SET @questionnaire_unique_index_exists = (
  SELECT COUNT(*)
  FROM information_schema.statistics
  WHERE table_schema = @questionnaire_schema
    AND table_name = 'user_questionnaire_responses'
    AND index_name = 'uq_user_questionnaire_version'
);

SET @questionnaire_fix_unique_key_sql = IF(
  @questionnaire_unique_index_exists = 0,
  'ALTER TABLE user_questionnaire_responses ADD UNIQUE KEY uq_user_questionnaire_version (user_id, questionnaire_version)',
  'SELECT ''uq_user_questionnaire_version already exists'' AS migration_status'
);
PREPARE questionnaire_fix_unique_key_statement FROM @questionnaire_fix_unique_key_sql;
EXECUTE questionnaire_fix_unique_key_statement;
DEALLOCATE PREPARE questionnaire_fix_unique_key_statement;
