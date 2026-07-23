-- migration-target-tables: user_backgrounds,user_background_settings
CREATE TABLE user_backgrounds (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL,
    storage_path VARCHAR(255) NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    mime_type VARCHAR(32) NOT NULL DEFAULT 'image/webp',
    file_size INT UNSIGNED NOT NULL,
    width SMALLINT UNSIGNED NOT NULL,
    height SMALLINT UNSIGNED NOT NULL,
    status ENUM('active', 'deleted') NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_user_backgrounds_user_status_created (user_id, status, created_at),
    UNIQUE KEY uq_user_backgrounds_storage_path (storage_path),
    CONSTRAINT fk_user_backgrounds_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_user_backgrounds_size CHECK (file_size > 0 AND file_size <= 10485760),
    CONSTRAINT chk_user_backgrounds_dimensions CHECK (width > 0 AND height > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE user_background_settings (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL,
    page_type ENUM('global', 'home', 'category', 'favorites', 'ai_assistant', 'profile') NOT NULL,
    background_id BIGINT UNSIGNED NULL,
    overlay_opacity DECIMAL(3,2) NOT NULL DEFAULT 0.36,
    blur_px TINYINT UNSIGNED NOT NULL DEFAULT 0,
    position_x TINYINT UNSIGNED NOT NULL DEFAULT 50,
    position_y TINYINT UNSIGNED NOT NULL DEFAULT 50,
    size_mode ENUM('cover', 'contain', 'auto') NOT NULL DEFAULT 'cover',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_user_background_settings_page (user_id, page_type),
    KEY idx_user_background_settings_background (background_id),
    CONSTRAINT fk_user_background_settings_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_user_background_settings_background
        FOREIGN KEY (background_id) REFERENCES user_backgrounds(id) ON DELETE SET NULL,
    CONSTRAINT chk_user_background_settings_overlay CHECK (overlay_opacity >= 0.00 AND overlay_opacity <= 0.70),
    CONSTRAINT chk_user_background_settings_blur CHECK (blur_px <= 20),
    CONSTRAINT chk_user_background_settings_x CHECK (position_x <= 100),
    CONSTRAINT chk_user_background_settings_y CHECK (position_y <= 100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
