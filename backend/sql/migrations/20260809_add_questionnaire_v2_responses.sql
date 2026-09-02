-- Versioned adaptive questionnaire responses. Existing user_profiles remains
-- untouched for backwards-compatible recommendation and admin reads.
CREATE TABLE IF NOT EXISTS user_questionnaire_responses (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  questionnaire_version INT NOT NULL,
  occupation VARCHAR(64) NOT NULL,
  answers_json LONGTEXT NOT NULL,
  profile_json LONGTEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_user_questionnaire_version (user_id, questionnaire_version),
  CONSTRAINT fk_user_questionnaire_responses_user
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
