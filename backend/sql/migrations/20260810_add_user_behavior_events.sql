-- Phase 2.1 unified recommendation behavior events.
-- Safe to run repeatedly on MySQL 8.0+.
CREATE TABLE IF NOT EXISTS user_behavior_events (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NULL,
  website_id INT NOT NULL,
  event_type VARCHAR(32) NOT NULL,
  source VARCHAR(64) NOT NULL DEFAULT 'other',
  recommendation_batch_id VARCHAR(128) NULL,
  questionnaire_version VARCHAR(64) NULL,
  profile_version VARCHAR(64) NULL,
  session_id VARCHAR(128) NULL,
  metadata_json JSON NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_behavior_events_user_created (user_id, created_at),
  INDEX idx_behavior_events_user_site_created (user_id, website_id, created_at),
  INDEX idx_behavior_events_type_created (event_type, created_at),
  INDEX idx_behavior_events_site_type (website_id, event_type),
  INDEX idx_behavior_events_batch (recommendation_batch_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
