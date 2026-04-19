-- 1. 创建分类表
CREATE TABLE IF NOT EXISTS `categories` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. 创建网站表（注意 logo_url 使用 LONGTEXT）
CREATE TABLE IF NOT EXISTS `websites` (
  `id` int NOT NULL AUTO_INCREMENT,
  `category_id` int DEFAULT NULL,
  `name` varchar(100) NOT NULL,
  `url` varchar(255) NOT NULL,
  `logo_url` LONGTEXT, 
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. 先插入分类数据（防止外键报错）
INSERT IGNORE INTO `categories` (`id`, `name`) VALUES (1, '常用推荐'), 
(2, '开发社区'), (3, '摸鱼娱乐'), (4, '实用工具'), (5, 'AI 神器');