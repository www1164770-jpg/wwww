-- Improve per-user favorite ordering and prevent duplicate favorite rows.
-- This migration intentionally does not delete duplicate data. Resolve any
-- duplicates before applying it if the preflight query finds any.

SET @has_favorite_unique = (
  SELECT COUNT(*)
  FROM (
    SELECT index_name
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = 'favorites'
      AND non_unique = 0
      AND index_name <> 'PRIMARY'
    GROUP BY index_name
    HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index) IN (
      'user_id,site_id',
      'site_id,user_id'
    )
  ) AS matching_favorite_unique
);
SET @add_favorite_unique = IF(
  @has_favorite_unique = 0,
  'ALTER TABLE favorites ADD UNIQUE KEY uq_favorites_user_site (user_id, site_id)',
  'SELECT 1'
);
PREPARE add_favorite_unique_stmt FROM @add_favorite_unique;
EXECUTE add_favorite_unique_stmt;
DEALLOCATE PREPARE add_favorite_unique_stmt;

SET @has_favorite_user_index = (
  SELECT COUNT(*)
  FROM (
    SELECT index_name
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = 'favorites'
    GROUP BY index_name
    HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index) = 'user_id'
  ) AS matching_favorite_user_index
);
SET @add_favorite_user_index = IF(
  @has_favorite_user_index = 0,
  'ALTER TABLE favorites ADD INDEX idx_favorites_user_id (user_id)',
  'SELECT 1'
);
PREPARE add_favorite_user_index_stmt FROM @add_favorite_user_index;
EXECUTE add_favorite_user_index_stmt;
DEALLOCATE PREPARE add_favorite_user_index_stmt;

SET @has_favorite_site_index = (
  SELECT COUNT(*)
  FROM (
    SELECT index_name
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = 'favorites'
    GROUP BY index_name
    HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index) = 'site_id'
  ) AS matching_favorite_site_index
);
SET @add_favorite_site_index = IF(
  @has_favorite_site_index = 0,
  'ALTER TABLE favorites ADD INDEX idx_favorites_site_id (site_id)',
  'SELECT 1'
);
PREPARE add_favorite_site_index_stmt FROM @add_favorite_site_index;
EXECUTE add_favorite_site_index_stmt;
DEALLOCATE PREPARE add_favorite_site_index_stmt;

SET @has_favorite_order_index = (
  SELECT COUNT(*)
  FROM (
    SELECT index_name
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = 'favorites'
    GROUP BY index_name
    HAVING GROUP_CONCAT(column_name ORDER BY seq_in_index) = 'user_id,created_at'
  ) AS matching_favorite_order_index
);
SET @add_favorite_order_index = IF(
  @has_favorite_order_index = 0,
  'ALTER TABLE favorites ADD INDEX idx_favorites_user_created (user_id, created_at)',
  'SELECT 1'
);
PREPARE add_favorite_order_index_stmt FROM @add_favorite_order_index;
EXECUTE add_favorite_order_index_stmt;
DEALLOCATE PREPARE add_favorite_order_index_stmt;
