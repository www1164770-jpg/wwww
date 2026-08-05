CREATE TABLE IF NOT EXISTS crawl_runs (
    id BIGINT NOT NULL AUTO_INCREMENT,
    run_uid VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    scheduled_for DATETIME(6) NOT NULL,
    started_at DATETIME(6) NULL,
    stop_requested_at DATETIME(6) NULL,
    finished_at DATETIME(6) NULL,
    target_count INT NOT NULL DEFAULT 0,
    leased_count INT NOT NULL DEFAULT 0,
    completed_count INT NOT NULL DEFAULT 0,
    failed_count INT NOT NULL DEFAULT 0,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    CONSTRAINT uq_crawl_runs_run_uid UNIQUE (run_uid),
    INDEX ix_crawl_runs_status_scheduled (status, scheduled_for)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS crawl_tasks (
    id BIGINT NOT NULL AUTO_INCREMENT,
    task_uid VARCHAR(64) NOT NULL,
    run_id BIGINT NULL,
    task_type VARCHAR(64) NOT NULL,
    target TEXT NOT NULL,
    target_hash VARCHAR(64) NOT NULL,
    dedupe_key VARCHAR(64) NOT NULL,
    active_dedupe_key VARCHAR(64) NULL,
    payload_json JSON NULL,
    priority INT NOT NULL DEFAULT 100,
    status VARCHAR(32) NOT NULL,
    attempt_count INT NOT NULL DEFAULT 0,
    max_attempts INT NOT NULL DEFAULT 3,
    available_at DATETIME(6) NOT NULL,
    leased_at DATETIME(6) NULL,
    leased_until DATETIME(6) NULL,
    worker_id VARCHAR(128) NULL,
    last_error_code VARCHAR(64) NULL,
    last_error_message VARCHAR(1000) NULL,
    completed_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    CONSTRAINT uq_crawl_tasks_task_uid UNIQUE (task_uid),
    CONSTRAINT uq_crawl_tasks_active_dedupe
        UNIQUE (task_type, active_dedupe_key),
    CONSTRAINT fk_crawl_tasks_run
        FOREIGN KEY (run_id) REFERENCES crawl_runs (id) ON DELETE SET NULL,
    INDEX ix_crawl_tasks_lease_candidates
        (status, available_at, priority, created_at),
    INDEX ix_crawl_tasks_expired_leases (status, leased_until),
    INDEX ix_crawl_tasks_run_status (run_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS worker_heartbeats (
    id BIGINT NOT NULL AUTO_INCREMENT,
    worker_id VARCHAR(128) NOT NULL,
    worker_type VARCHAR(64) NOT NULL,
    process_id INT NOT NULL,
    hostname VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL,
    current_task_uid VARCHAR(64) NULL,
    started_at DATETIME(6) NOT NULL,
    last_seen_at DATETIME(6) NOT NULL,
    metadata_json JSON NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_worker_heartbeats_worker_id UNIQUE (worker_id),
    INDEX ix_worker_heartbeats_status_seen (status, last_seen_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS crawler_settings (
    setting_key VARCHAR(128) NOT NULL,
    setting_value TEXT NOT NULL,
    value_type VARCHAR(32) NOT NULL,
    updated_by VARCHAR(128) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (setting_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS outbox_events (
    id BIGINT NOT NULL AUTO_INCREMENT,
    event_uid VARCHAR(64) NOT NULL,
    aggregate_type VARCHAR(64) NOT NULL,
    aggregate_uid VARCHAR(64) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    payload_json JSON NOT NULL,
    status VARCHAR(32) NOT NULL,
    attempt_count INT NOT NULL DEFAULT 0,
    max_attempts INT NOT NULL DEFAULT 3,
    available_at DATETIME(6) NOT NULL,
    leased_at DATETIME(6) NULL,
    leased_until DATETIME(6) NULL,
    worker_id VARCHAR(128) NULL,
    last_error VARCHAR(1000) NULL,
    processed_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
        ON UPDATE CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    CONSTRAINT uq_outbox_events_event_uid UNIQUE (event_uid),
    INDEX ix_outbox_events_lease_candidates
        (status, available_at, created_at),
    INDEX ix_outbox_events_expired_leases (status, leased_until)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
