CREATE DATABASE IF NOT EXISTS pro_nav_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE pro_nav_db;

-- 1. 用户与云端配置表 (User Preferences)
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    github_id VARCHAR(100) UNIQUE, -- 记录 GitHub 登录的唯一标识
    avatar_url VARCHAR(255),
    dark_mode BOOLEAN DEFAULT FALSE,
    custom_wallpaper VARCHAR(500), -- 专属壁纸的 URL
    current_engine VARCHAR(20) DEFAULT 'bing',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 导航分类表 (Categories)
CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    profession_type VARCHAR(20) DEFAULT 'general', -- 对应 'frontend', 'designer' 等
    sort_order INT DEFAULT 0
);

-- 3. 网站资源表 (Websites)
CREATE TABLE websites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    url VARCHAR(500) NOT NULL,
    logo_url VARCHAR(500),
    clicks INT DEFAULT 0, -- 用于生成真实排行榜
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);