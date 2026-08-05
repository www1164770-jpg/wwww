CREATE TABLE IF NOT EXISTS analysis_results (
    id BIGINT NOT NULL AUTO_INCREMENT,
    analysis_uid VARCHAR(64) NOT NULL,
    fetch_result_id BIGINT NOT NULL,
    candidate_uid VARCHAR(72) NOT NULL,
    analysis_version VARCHAR(128) NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    original_language VARCHAR(64) NULL,
    detected_language VARCHAR(16) NOT NULL,
    language_confidence DOUBLE NOT NULL,
    category VARCHAR(64) NOT NULL,
    category_confidence DOUBLE NOT NULL,
    quality_score DOUBLE NOT NULL,
    title_original VARCHAR(500) NULL,
    summary_zh TEXT NOT NULL,
    summary_method VARCHAR(32) NOT NULL,
    tags_json JSON NOT NULL,
    rule_version VARCHAR(128) NOT NULL,
    model_name VARCHAR(255) NULL,
    model_status VARCHAR(32) NOT NULL,
    model_error_code VARCHAR(64) NULL,
    evidence_hashes_json JSON NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    CONSTRAINT uq_analysis_results_uid UNIQUE (analysis_uid),
    CONSTRAINT uq_analysis_results_fetch_version
        UNIQUE (fetch_result_id, analysis_version),
    CONSTRAINT fk_analysis_results_fetch
        FOREIGN KEY (fetch_result_id) REFERENCES fetch_results (id),
    INDEX ix_analysis_results_candidate_created (candidate_uid, created_at),
    INDEX ix_analysis_results_category_confidence (category, category_confidence)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS risk_decisions (
    id BIGINT NOT NULL AUTO_INCREMENT,
    decision_uid VARCHAR(64) NOT NULL,
    analysis_result_id BIGINT NOT NULL,
    decision_version VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL,
    risk_score DOUBLE NOT NULL,
    confidence DOUBLE NOT NULL,
    hard_reject BOOLEAN NOT NULL,
    rule_codes_json JSON NOT NULL,
    evidence_hashes_json JSON NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    CONSTRAINT uq_risk_decisions_uid UNIQUE (decision_uid),
    CONSTRAINT uq_risk_decisions_analysis_version
        UNIQUE (analysis_result_id, decision_version),
    CONSTRAINT fk_risk_decisions_analysis
        FOREIGN KEY (analysis_result_id) REFERENCES analysis_results (id),
    INDEX ix_risk_decisions_status_created (status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS icon_assets (
    id BIGINT NOT NULL AUTO_INCREMENT,
    asset_uid VARCHAR(64) NOT NULL,
    fetch_result_id BIGINT NOT NULL,
    source_url TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    mime_type VARCHAR(64) NOT NULL,
    width INT NOT NULL,
    height INT NOT NULL,
    byte_size INT NOT NULL,
    relative_path VARCHAR(500) NOT NULL,
    fetched_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_icon_assets_uid UNIQUE (asset_uid),
    CONSTRAINT uq_icon_assets_content_hash UNIQUE (content_hash),
    CONSTRAINT fk_icon_assets_fetch
        FOREIGN KEY (fetch_result_id) REFERENCES fetch_results (id),
    INDEX ix_icon_assets_fetch_result (fetch_result_id, fetched_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
