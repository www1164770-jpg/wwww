-- migration-target-tables: user_personalization_settings
-- Apply with: python backend/scripts/run_sql_migration.py backend/sql/migrations/20260815_add_personalization_settings.sql
CREATE TABLE IF NOT EXISTS user_personalization_settings (
  user_id INT NOT NULL,
  settings_json JSON NOT NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id),
  CONSTRAINT fk_user_personalization_settings_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
