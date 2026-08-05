-- Phase 4 integrity hardening.  Forward-only and crawler database only.
ALTER TABLE review_cases
    ADD COLUMN source_analysis_uid VARCHAR(64) NULL,
    ADD COLUMN source_analysis_version VARCHAR(128) NULL,
    ADD COLUMN review_content_hash VARCHAR(64) NULL,
    ADD COLUMN selected_tags JSON NULL,
    ADD COLUMN selected_risk_level VARCHAR(16) NULL,
    ADD COLUMN selected_quality_score DOUBLE NULL;

ALTER TABLE review_events
    ADD COLUMN publish_uid VARCHAR(64) NULL,
    ADD COLUMN request_id VARCHAR(64) NULL,
    ADD COLUMN review_version INT NULL,
    ADD COLUMN changed_fields_json JSON NULL;

ALTER TABLE publish_records
    ADD COLUMN review_version INT NULL,
    ADD COLUMN preview_uid VARCHAR(64) NULL,
    ADD COLUMN target_name VARCHAR(64) NULL,
    ADD COLUMN target_record_key VARCHAR(128) NULL,
    ADD COLUMN last_attempt_at DATETIME(6) NULL,
    ADD COLUMN next_retry_at DATETIME(6) NULL,
    ADD COLUMN version INT NOT NULL DEFAULT 1,
    ADD INDEX ix_publish_records_case_status (review_case_id, status),
    ADD INDEX ix_publish_records_preview (preview_uid);

CREATE TABLE IF NOT EXISTS publish_previews (
    id BIGINT NOT NULL AUTO_INCREMENT,
    preview_uid VARCHAR(64) NOT NULL,
    review_case_id BIGINT NOT NULL,
    review_version INT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    result_json JSON NOT NULL,
    generated_by VARCHAR(128) NOT NULL,
    generated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    expires_at DATETIME(6) NULL,
    invalidated_at DATETIME(6) NULL,
    invalidated_reason VARCHAR(64) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    CONSTRAINT uq_publish_previews_uid UNIQUE (preview_uid),
    CONSTRAINT uq_publish_previews_review_version_hash UNIQUE (review_case_id, review_version, content_hash),
    CONSTRAINT fk_publish_previews_case FOREIGN KEY (review_case_id) REFERENCES review_cases (id),
    INDEX ix_publish_previews_review_valid (review_case_id, invalidated_at, expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
