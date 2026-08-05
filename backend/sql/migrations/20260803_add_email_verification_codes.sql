-- Persistent local registration verification codes.
-- Codes are stored as HMAC digests and expire after five minutes.
-- This migration is idempotent and does not alter existing users.

CREATE TABLE IF NOT EXISTS email_verification_codes (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  email VARCHAR(120) NOT NULL,
  purpose VARCHAR(32) NOT NULL,
  code_hash CHAR(64) NOT NULL,
  expires_at DATETIME NOT NULL,
  sent_at DATETIME NOT NULL,
  attempt_count TINYINT UNSIGNED NOT NULL DEFAULT 0,
  used_at DATETIME NULL,
  request_ip VARCHAR(64) NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_email_verification_purpose (email, purpose),
  KEY idx_email_verification_expiry (expires_at),
  KEY idx_email_verification_ip_sent (request_ip, sent_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
