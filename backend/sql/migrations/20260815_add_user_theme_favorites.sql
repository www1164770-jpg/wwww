-- migration-target-tables: user_theme_favorites
-- Apply only to the main navigation database (never zhihui_crawler).
CREATE TABLE IF NOT EXISTS user_theme_favorites (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id INT NOT NULL,
  theme_key VARCHAR(64) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_user_theme_favorites_user_theme (user_id, theme_key),
  KEY idx_user_theme_favorites_user_created (user_id, created_at),
  CONSTRAINT fk_user_theme_favorites_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Preserve legacy account favorites stored in settings_json.  INSERT IGNORE
-- makes the backfill repeat-safe and lets the unique key enforce de-duplication.
INSERT IGNORE INTO user_theme_favorites (user_id, theme_key)
SELECT settings.user_id, LEFT(items.theme_key, 64)
FROM user_personalization_settings AS settings
JOIN JSON_TABLE(
  JSON_EXTRACT(settings.settings_json, '$.favorites'),
  '$[*]' COLUMNS (theme_key VARCHAR(255) PATH '$')
) AS items
WHERE JSON_TYPE(JSON_EXTRACT(settings.settings_json, '$.favorites')) = 'ARRAY'
  AND TRIM(items.theme_key) <> '';
