-- migration-target-tables: user_backgrounds
-- Apply only to the main navigation database (never zhihui_crawler).
ALTER TABLE user_backgrounds
  ADD COLUMN privacy ENUM('private','public') NOT NULL DEFAULT 'private' AFTER status,
  ADD COLUMN analysis_json JSON NULL AFTER privacy;
