-- 1. 创建数据库并使用
CREATE DATABASE IF NOT EXISTS nav_site DEFAULT CHARSET utf8mb4;
USE nav_site;

-- 2. 创建分类表
CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);

-- 3. 创建网站表
CREATE TABLE websites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT,
    name VARCHAR(100) NOT NULL,
    url VARCHAR(255) NOT NULL,
    logo_url VARCHAR(255),
    click_count INT DEFAULT 0,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- 4. 插入测试分类
INSERT INTO categories (name) VALUES ('常用'), ('学习'), ('工具'), ('AI');

-- 5. 插入测试网站数据
INSERT INTO websites (category_id, name, url, logo_url, click_count) VALUES 
(1, '哔哩哔哩', 'https://www.bilibili.com', 'https://www.bilibili.com/favicon.ico', 150),
(2, 'LeetCode', 'https://leetcode.cn', 'https://leetcode.cn/favicon.ico', 80),
(3, 'GitHub', 'https://github.com', 'https://github.githubassets.com/favicons/favicon.png', 200),
(4, 'ChatGPT', 'https://chat.openai.com', 'https://chat.openai.com/favicon.ico', 500);