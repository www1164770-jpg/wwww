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
