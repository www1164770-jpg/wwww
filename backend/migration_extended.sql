-- =============================================================================
-- 智汇导航 - 扩展数据库迁移脚本
-- 运行环境：MySQL 5.7+ / 8.0+
-- 说明：在已有数据库 nav_site 基础上，新增扩展功能所需的表结构
-- =============================================================================

USE nav_site;

-- =============================================================================
-- 1. 通知中心表 (notifications)
-- 用途：记录用户收到的评论回复、点赞等互动通知
-- =============================================================================
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '接收通知的用户ID',
    type VARCHAR(30) NOT NULL COMMENT '通知类型: like(点赞), comment(评论), reply(回复), system(系统通知)',
    content VARCHAR(500) NOT NULL COMMENT '通知内容摘要',
    related_id INT DEFAULT NULL COMMENT '关联资源ID（被点赞的文章、被回复的评论等）',
    is_read TINYINT DEFAULT 0 COMMENT '是否已读: 0=未读, 1=已读',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '通知创建时间',
    INDEX idx_user_read (user_id, is_read),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户通知表';

-- =============================================================================
-- 2. 文章表 (articles)
-- 用途：存储用户发布的文章/内容
-- =============================================================================
CREATE TABLE IF NOT EXISTS articles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL COMMENT '文章标题',
    content LONGTEXT NOT NULL COMMENT '文章正文（支持 Markdown/HTML）',
    author_id INT NOT NULL COMMENT '作者用户ID',
    cover_url VARCHAR(500) DEFAULT NULL COMMENT '封面图URL',
    summary VARCHAR(500) DEFAULT NULL COMMENT '文章摘要',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '审核状态: pending(待审核), published(已发布), rejected(已拒绝), draft(草稿)',
    review_reason VARCHAR(500) DEFAULT NULL COMMENT '审核拒绝理由',
    views INT DEFAULT 0 COMMENT '浏览量',
    likes INT DEFAULT 0 COMMENT '点赞数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_author_status (author_id, status),
    INDEX idx_created (created_at),
    FULLTEXT INDEX ft_title_content (title, content)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文章内容表';

-- =============================================================================
-- 3. 文章评论表 (comments)
-- 用途：存储文章下的评论，支持嵌套回复
-- =============================================================================
CREATE TABLE IF NOT EXISTS comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    article_id INT NOT NULL COMMENT '所属文章ID',
    user_id INT NOT NULL COMMENT '评论者用户ID',
    parent_id INT DEFAULT NULL COMMENT '父评论ID（NULL表示一级评论）',
    content TEXT NOT NULL COMMENT '评论内容',
    likes INT DEFAULT 0 COMMENT '点赞数',
    is_deleted TINYINT DEFAULT 0 COMMENT '软删除标记',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_article (article_id, created_at),
    INDEX idx_user (user_id),
    INDEX idx_parent (parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文章评论表';

-- =============================================================================
-- 4. 待审核站点表 (pending_sites)
-- 用途：存储从 Hacker News 等来源抓取的待审核网站
-- =============================================================================
CREATE TABLE IF NOT EXISTS pending_sites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL COMMENT '站点名称',
    url VARCHAR(500) NOT NULL COMMENT '站点URL',
    description VARCHAR(500) DEFAULT NULL COMMENT '站点描述',
    source VARCHAR(50) DEFAULT 'admin' COMMENT '来源: admin, Hacker News, user_submit',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态: pending, approved, rejected',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='待审核站点表';

-- =============================================================================
-- 5. 点击日志表 (click_logs)
-- 用途：记录每次用户点击网站的详细日志
-- =============================================================================
CREATE TABLE IF NOT EXISTS click_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    website_id INT NOT NULL COMMENT '被点击的网站ID',
    user_id INT DEFAULT NULL COMMENT '点击用户ID（未登录时为NULL）',
    ip_address VARCHAR(45) DEFAULT NULL COMMENT '点击者IP',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_website_time (website_id, created_at),
    INDEX idx_date (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='网站点击日志表';

-- =============================================================================
-- 6. 文章点赞记录表 (article_likes)
-- 用途：记录用户对文章的点赞，防止重复点赞
-- =============================================================================
CREATE TABLE IF NOT EXISTS article_likes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    article_id INT NOT NULL,
    user_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_article_user (article_id, user_id),
    INDEX idx_article (article_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文章点赞记录表';

-- =============================================================================
-- 7. 用户收藏表 (user_favorites)
-- 用途：记录用户收藏的网站
-- =============================================================================
CREATE TABLE IF NOT EXISTS user_favorites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    website_id BIGINT NOT NULL COMMENT '网站ID（使用BIGINT兼容Date.now()生成的临时ID）',
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    UNIQUE KEY uk_user_website (user_id, website_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户收藏表';

-- =============================================================================
-- 8. 扩展 users 表字段（如缺失则添加）
-- =============================================================================
-- 密码哈希字段（兼容 Flask 注册用户）
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255) DEFAULT NULL AFTER username;
-- 邮箱字段
ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(120) UNIQUE DEFAULT NULL AFTER username;
-- 手机号字段
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20) DEFAULT NULL AFTER email;
-- 性别字段
ALTER TABLE users ADD COLUMN IF NOT EXISTS gender VARCHAR(10) DEFAULT '保密' AFTER phone;
-- 生日字段
ALTER TABLE users ADD COLUMN IF NOT EXISTS birthday VARCHAR(20) DEFAULT '未设置' AFTER gender;
-- 个人简介
ALTER TABLE users ADD COLUMN IF NOT EXISTS bio VARCHAR(300) DEFAULT NULL AFTER birthday;
-- 逻辑删除标记（7天冷静期）
ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL DEFAULT NULL AFTER bio;

-- =============================================================================
-- 9. 问卷推荐系统字段 (Survey & Personalization v2)
-- =============================================================================
-- 用户是否已完成兴趣问卷 (0=未完成, 1=已完成)
ALTER TABLE users ADD COLUMN IF NOT EXISTS has_survey TINYINT DEFAULT 0 AFTER deleted_at;
-- v1 兴趣标签（保留向后兼容）
ALTER TABLE users ADD COLUMN IF NOT EXISTS interests VARCHAR(500) DEFAULT NULL AFTER has_survey;
-- v2 多维用户标签，逗号分隔存储 (例如: "frontend,job-hunting,efficiency")
ALTER TABLE users ADD COLUMN IF NOT EXISTS user_tags VARCHAR(500) DEFAULT NULL AFTER interests;

-- 网站标签字段，逗号分隔存储 (使用 v2 标签 key)
ALTER TABLE websites ADD COLUMN IF NOT EXISTS tags VARCHAR(500) DEFAULT NULL AFTER description;

-- 为标签字段建索引加速 LIKE 查询
ALTER TABLE websites ADD INDEX IF NOT EXISTS idx_tags (tags(100));
ALTER TABLE articles ADD COLUMN IF NOT EXISTS tags VARCHAR(500) DEFAULT NULL AFTER summary;
ALTER TABLE articles ADD INDEX IF NOT EXISTS idx_tags (tags(100));

-- =============================================================================
-- 10. 预填网站标签 (v2 标签 key)
-- 对应问卷维度 key: frontend/backend/ai-data/ui-design/iot-hardware/product-pm/
--                    self-learning/job-hunting/efficiency/open-source
-- =============================================================================
UPDATE websites SET tags = 'frontend,self-learning,open-source' WHERE name LIKE '%MDN%' AND tags IS NULL;
UPDATE websites SET tags = 'frontend,backend,self-learning,job-hunting' WHERE name IN ('掘金','SegmentFault','V2EX') AND tags IS NULL;
UPDATE websites SET tags = 'backend,open-source,efficiency' WHERE name IN ('GitHub','GitLab','Gitee') AND tags IS NULL;
UPDATE websites SET tags = 'frontend,backend,efficiency' WHERE name IN ('Vercel','Cloudflare') AND tags IS NULL;
UPDATE websites SET tags = 'ai-data,efficiency,self-learning' WHERE name IN ('ChatGPT','Claude','Gemini','DeepSeek','Kimi','豆包') AND tags IS NULL;
UPDATE websites SET tags = 'ai-data,ui-design' WHERE name IN ('Midjourney','Stable Diffusion','Runway') AND tags IS NULL;
UPDATE websites SET tags = 'ai-data,backend,self-learning' WHERE name IN ('GitHub Copilot','Cursor') AND tags IS NULL;
UPDATE websites SET tags = 'ui-design,efficiency' WHERE name IN ('Unsplash','TinyPNG','Squoosh') AND tags IS NULL;
UPDATE websites SET tags = 'efficiency,product-pm' WHERE name IN ('Notion','飞书','腾讯文档','石墨文档') AND tags IS NULL;
UPDATE websites SET tags = 'ui-design,product-pm,efficiency' WHERE name IN ('ProcessOn','Excalidraw') AND tags IS NULL;
UPDATE websites SET tags = 'backend,self-learning,job-hunting' WHERE name IN ('LeetCode','牛客网') AND tags IS NULL;
UPDATE websites SET tags = 'backend,efficiency' WHERE name IN ('Docker Hub','npm') AND tags IS NULL;
UPDATE websites SET tags = 'frontend,self-learning' WHERE name = 'Can I Use' AND tags IS NULL;
UPDATE websites SET tags = 'ai-data,efficiency,self-learning' WHERE name IN ('百度翻译','DeepL翻译') AND tags IS NULL;
UPDATE websites SET tags = 'efficiency,product-pm' WHERE name IN ('iLovePDF','Convertio') AND tags IS NULL;

-- =============================================================================
-- 完成
-- =============================================================================
SELECT '✅ 数据库扩展迁移完成！' AS result;
