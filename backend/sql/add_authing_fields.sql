-- Authing login integration fields for users.
-- Run this migration manually after backing up the database.
-- It does not alter existing passwords, roles, questionnaire state, or local login data.

ALTER TABLE users
  ADD COLUMN authing_sub VARCHAR(128) NULL UNIQUE,
  ADD COLUMN avatar_url VARCHAR(500) NULL,
  ADD COLUMN login_provider VARCHAR(50) DEFAULT 'local';
