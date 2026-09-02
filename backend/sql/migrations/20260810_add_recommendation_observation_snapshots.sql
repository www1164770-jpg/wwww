-- Phase 2.2-D: immutable aggregate snapshots for recommendation observation.
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
