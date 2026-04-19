/* 智汇导航项目 - 数据库初始化脚本
   功能：创建表结构，并确保存储 Base64 的字段足够大
*/

-- 1. 如果存在旧表则删除（谨慎：这会清空数据）
DROP TABLE IF EXISTS `websites`;
DROP TABLE IF EXISTS `categories`;

-- 2. 创建分类表
CREATE TABLE `categories` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. 创建网站表
CREATE TABLE `websites` (
  `id` int NOT NULL AUTO_INCREMENT,
  `category_id` int DEFAULT NULL,
  `name` varchar(100) NOT NULL,
  `url` varchar(255) NOT NULL,
  -- ✨ 核心修改：使用 LONGTEXT 确保存储超长的 Base64 图片数据
  `logo_url` LONGTEXT, 
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. 插入基础分类数据
INSERT INTO `categories` (`id`, `name`) VALUES 
(1, '常用推荐'),
(2, '开发社区'),
(3, '摸鱼娱乐'),
(4, '实用工具'),
(5, 'AI 神器');