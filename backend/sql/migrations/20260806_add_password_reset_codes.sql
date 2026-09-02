-- Persistent password reset codes and JWT session invalidation support.
-- All timestamps are written as UTC by the application.
-- The table creation is idempotent and preserves all existing user data.

CREATE TABLE IF NOT EXISTS password_reset_codes (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id INT NULL,
  email VARCHAR(120) NOT NULL,
  code_hash CHAR(64) NOT NULL,
  expires_at DATETIME(6) NOT NULL,
  used_at DATETIME(6) NULL,
  attempt_count TINYINT UNSIGNED NOT NULL DEFAULT 0,
  request_ip VARCHAR(64) NULL,
  created_at DATETIME(6) NOT NULL,
  PRIMARY KEY (id),
  KEY idx_password_reset_email (email),
  KEY idx_password_reset_user_id (user_id),
  KEY idx_password_reset_expires_at (expires_at),
  KEY idx_password_reset_email_created (email, created_at),
  CONSTRAINT fk_password_reset_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET @password_reset_session_version_exists := (
  SELECT COUNT(*)
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'users'
    AND COLUMN_NAME = 'session_version'
);
SET @password_reset_session_version_sql := IF(
  @password_reset_session_version_exists = 0,
  'ALTER TABLE users ADD COLUMN session_version INT UNSIGNED NOT NULL DEFAULT 0',
  'SELECT 1'
);
PREPARE password_reset_session_version_statement
  FROM @password_reset_session_version_sql;
EXECUTE password_reset_session_version_statement;
DEALLOCATE PREPARE password_reset_session_version_statement;
