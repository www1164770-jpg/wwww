-- Requirement V1 schema migration.
-- Review existing column names before running on production MySQL.
-- MySQL 8.0+ supports ADD COLUMN IF NOT EXISTS; older versions need manual checks.

-- User personalization profiles for first-login questionnaire data.
CREATE TABLE IF NOT EXISTS user_profiles (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL UNIQUE,
  occupation VARCHAR(64),
  skill_level VARCHAR(32),
  interests TEXT,
  preferences TEXT,
  purposes TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_user_profiles_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tags shared by sites, search, and recommendation filters.
CREATE TABLE IF NOT EXISTS tags (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(80) NOT NULL UNIQUE,
  type VARCHAR(32) DEFAULT 'general',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Many-to-many relation between sites and tags.
CREATE TABLE IF NOT EXISTS site_tags (
  id INT AUTO_INCREMENT PRIMARY KEY,
  site_id INT NOT NULL,
  tag_id INT NOT NULL,
  UNIQUE KEY uniq_site_tag (site_id, tag_id),
  INDEX idx_site_tags_site_id (site_id),
  INDEX idx_site_tags_tag_id (tag_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Occupation suitability weights for personalized recommendations.
CREATE TABLE IF NOT EXISTS site_occupations (
  id INT AUTO_INCREMENT PRIMARY KEY,
  site_id INT NOT NULL,
  occupation VARCHAR(64) NOT NULL,
  weight FLOAT DEFAULT 1,
  UNIQUE KEY uniq_site_occupation (site_id, occupation),
  INDEX idx_site_occupations_site_id (site_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- User favorite sites and optional notes.
CREATE TABLE IF NOT EXISTS favorites (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  site_id INT NOT NULL,
  note TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_user_site (user_id, site_id),
  INDEX idx_favorites_user_id (user_id),
  INDEX idx_favorites_site_id (site_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Site comments and ratings for future moderation workflows.
CREATE TABLE IF NOT EXISTS comments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  site_id INT NOT NULL,
  content TEXT NOT NULL,
  rating INT,
  status VARCHAR(32) DEFAULT 'visible',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_comments_site_id (site_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- User behavior events used by analytics and recommendations.
CREATE TABLE IF NOT EXISTS user_behaviors (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT,
  site_id INT,
  behavior_type VARCHAR(32) NOT NULL,
  keyword VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_user_behaviors_user_id (user_id),
  INDEX idx_user_behaviors_site_id (site_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Unified, explainable behavior events for recommendation feedback.
-- user_id is nullable so anonymous sessions are never represented by a fake user.
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

-- Immutable aggregate snapshots created by administrators during the Phase 2
-- observation period. They never alter the underlying event fact table.
CREATE TABLE IF NOT EXISTS recommendation_observation_snapshots (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  snapshot_id VARCHAR(64) NOT NULL UNIQUE,
  algorithm_version VARCHAR(64) NOT NULL,
  lookback_days VARCHAR(16) NOT NULL,
  exclude_test_users TINYINT(1) NOT NULL DEFAULT 1,
  captured_by_user_id INT NULL,
  summary_json JSON NOT NULL,
  data_quality_json JSON NOT NULL,
  readiness_json JSON NOT NULL,
  match_score_buckets_json JSON NOT NULL,
  primary_need_metrics_json JSON NOT NULL,
  tag_metrics_json JSON NOT NULL,
  personalization_metrics_json JSON NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_observation_snapshots_created (created_at),
  INDEX idx_observation_snapshots_algorithm_created (algorithm_version, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Recommendation trace logs for explainability and tuning.
CREATE TABLE IF NOT EXISTS recommendation_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  site_id INT NOT NULL,
  score FLOAT DEFAULT 0,
  reason VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_recommendation_logs_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Users table additions.
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS avatar VARCHAR(255);

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS role VARCHAR(32) DEFAULT 'user';

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS questionnaire_completed TINYINT(1) DEFAULT 0;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS status VARCHAR(32) DEFAULT 'active';

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS deleted_at DATETIME NULL;

-- Categories table additions.
ALTER TABLE categories
  ADD COLUMN IF NOT EXISTS parent_id INT NULL;

ALTER TABLE categories
  ADD COLUMN IF NOT EXISTS icon VARCHAR(120);

ALTER TABLE categories
  ADD COLUMN IF NOT EXISTS sort_order INT DEFAULT 0;

ALTER TABLE categories
  ADD COLUMN IF NOT EXISTS status VARCHAR(32) DEFAULT 'active';

ALTER TABLE categories
  ADD COLUMN IF NOT EXISTS created_at DATETIME DEFAULT CURRENT_TIMESTAMP;

-- Websites table additions.
ALTER TABLE websites
  ADD COLUMN IF NOT EXISTS summary VARCHAR(500);

ALTER TABLE websites
  ADD COLUMN IF NOT EXISTS description TEXT;

ALTER TABLE websites
  ADD COLUMN IF NOT EXISTS is_free TINYINT(1) DEFAULT 1;

ALTER TABLE websites
  ADD COLUMN IF NOT EXISTS need_login TINYINT(1) DEFAULT 0;

ALTER TABLE websites
  ADD COLUMN IF NOT EXISTS region VARCHAR(32) DEFAULT 'domestic';

ALTER TABLE websites
  ADD COLUMN IF NOT EXISTS quality_score FLOAT DEFAULT 0;

ALTER TABLE websites
  ADD COLUMN IF NOT EXISTS recommend_level INT DEFAULT 0;

ALTER TABLE websites
  ADD COLUMN IF NOT EXISTS click_count INT DEFAULT 0;

ALTER TABLE websites
  ADD COLUMN IF NOT EXISTS favorite_count INT DEFAULT 0;

ALTER TABLE websites
  ADD COLUMN IF NOT EXISTS rating_avg FLOAT DEFAULT 0;

ALTER TABLE websites
  ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'approved';

ALTER TABLE websites
  ADD COLUMN IF NOT EXISTS created_at DATETIME DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE websites
  ADD COLUMN IF NOT EXISTS updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;
