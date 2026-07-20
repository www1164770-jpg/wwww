-- migration-target-tables: occupations,questionnaire_definitions,questionnaire_versions,questionnaire_questions,questionnaire_options,questionnaire_conditions
CREATE TABLE occupations (
    id INT NOT NULL AUTO_INCREMENT,
    occupation_code VARCHAR(64) NOT NULL,
    name VARCHAR(120) NOT NULL,
    category VARCHAR(120) NULL,
    sort_order INT NOT NULL DEFAULT 0,
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    new_occupation_policy VARCHAR(32) NOT NULL DEFAULT 'use_general',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT uq_occupations_occupation_code UNIQUE (occupation_code),
    CONSTRAINT uq_occupations_name UNIQUE (name),
    KEY idx_occupations_enabled_sort_order (enabled, sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE questionnaire_definitions (
    id INT NOT NULL AUTO_INCREMENT,
    definition_code VARCHAR(96) NOT NULL,
    name VARCHAR(160) NOT NULL,
    description TEXT NULL,
    scope_type VARCHAR(32) NOT NULL,
    scope_key VARCHAR(192) NOT NULL,
    occupation_id INT NULL,
    user_type VARCHAR(32) NULL,
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    created_by_user_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT uq_questionnaire_definitions_definition_code UNIQUE (definition_code),
    CONSTRAINT uq_questionnaire_definitions_scope_key UNIQUE (scope_key),
    KEY idx_questionnaire_definitions_occupation_id (occupation_id),
    KEY idx_questionnaire_definitions_created_by_user_id (created_by_user_id),
    CONSTRAINT fk_questionnaire_definitions_occupation
        FOREIGN KEY (occupation_id) REFERENCES occupations(id) ON DELETE RESTRICT,
    CONSTRAINT fk_questionnaire_definitions_created_by_user
        FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE questionnaire_versions (
    id INT NOT NULL AUTO_INCREMENT,
    definition_id INT NOT NULL,
    version_number INT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    current_effective_scope_key VARCHAR(192) NULL,
    source_version_id INT NULL,
    version_description TEXT NULL,
    created_by_user_id INT NOT NULL,
    published_by_user_id INT NULL,
    published_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT uq_questionnaire_versions_number UNIQUE (definition_id, version_number),
    CONSTRAINT uq_questionnaire_versions_current_scope UNIQUE (current_effective_scope_key),
    KEY idx_questionnaire_versions_source_version_id (source_version_id),
    KEY idx_questionnaire_versions_created_by_user_id (created_by_user_id),
    KEY idx_questionnaire_versions_published_by_user_id (published_by_user_id),
    CONSTRAINT fk_questionnaire_versions_definition
        FOREIGN KEY (definition_id) REFERENCES questionnaire_definitions(id) ON DELETE RESTRICT,
    CONSTRAINT fk_questionnaire_versions_source_version
        FOREIGN KEY (source_version_id) REFERENCES questionnaire_versions(id) ON DELETE RESTRICT,
    CONSTRAINT fk_questionnaire_versions_created_by_user
        FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE RESTRICT,
    CONSTRAINT fk_questionnaire_versions_published_by_user
        FOREIGN KEY (published_by_user_id) REFERENCES users(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE questionnaire_questions (
    id INT NOT NULL AUTO_INCREMENT,
    version_id INT NOT NULL,
    question_code VARCHAR(96) NOT NULL,
    title VARCHAR(300) NOT NULL,
    description TEXT NULL,
    question_type VARCHAR(32) NOT NULL,
    required TINYINT(1) NOT NULL DEFAULT 0,
    sort_order INT NOT NULL,
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    is_general TINYINT(1) NOT NULL DEFAULT 0,
    min_selections INT NULL,
    max_selections INT NULL,
    max_length INT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT uq_questionnaire_questions_code UNIQUE (version_id, question_code),
    KEY idx_questionnaire_questions_version_sort_order (version_id, sort_order),
    CONSTRAINT fk_questionnaire_questions_version
        FOREIGN KEY (version_id) REFERENCES questionnaire_versions(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE questionnaire_options (
    id INT NOT NULL AUTO_INCREMENT,
    question_id INT NOT NULL,
    option_value VARCHAR(96) NOT NULL,
    label VARCHAR(300) NOT NULL,
    sort_order INT NOT NULL,
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT uq_questionnaire_options_value UNIQUE (question_id, option_value),
    KEY idx_questionnaire_options_question_sort_order (question_id, sort_order),
    CONSTRAINT fk_questionnaire_options_question
        FOREIGN KEY (question_id) REFERENCES questionnaire_questions(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE questionnaire_conditions (
    id INT NOT NULL AUTO_INCREMENT,
    version_id INT NOT NULL,
    source_question_id INT NOT NULL,
    target_question_id INT NOT NULL,
    expected_option_id INT NOT NULL,
    operator VARCHAR(16) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT uq_questionnaire_conditions_target UNIQUE (target_question_id),
    KEY idx_questionnaire_conditions_version_id (version_id),
    KEY idx_questionnaire_conditions_source_question_id (source_question_id),
    KEY idx_questionnaire_conditions_expected_option_id (expected_option_id),
    CONSTRAINT fk_questionnaire_conditions_version
        FOREIGN KEY (version_id) REFERENCES questionnaire_versions(id) ON DELETE RESTRICT,
    CONSTRAINT fk_questionnaire_conditions_source_question
        FOREIGN KEY (source_question_id) REFERENCES questionnaire_questions(id) ON DELETE RESTRICT,
    CONSTRAINT fk_questionnaire_conditions_target_question
        FOREIGN KEY (target_question_id) REFERENCES questionnaire_questions(id) ON DELETE RESTRICT,
    CONSTRAINT fk_questionnaire_conditions_expected_option
        FOREIGN KEY (expected_option_id) REFERENCES questionnaire_options(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
