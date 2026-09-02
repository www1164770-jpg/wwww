-- Optional search metadata and repeatable indexes for database-backed site search.
SET @has_websites_aliases_column = (
  SELECT COUNT(*) FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'websites' AND column_name = 'aliases'
);
SET @add_websites_aliases_column = IF(
  @has_websites_aliases_column = 0,
  'ALTER TABLE websites ADD COLUMN aliases TEXT NULL AFTER description',
  'SELECT 1'
);
PREPARE add_websites_aliases_column_stmt FROM @add_websites_aliases_column;
EXECUTE add_websites_aliases_column_stmt;
DEALLOCATE PREPARE add_websites_aliases_column_stmt;

SET @has_websites_use_cases_column = (
  SELECT COUNT(*) FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'websites' AND column_name = 'use_cases'
);
SET @add_websites_use_cases_column = IF(
  @has_websites_use_cases_column = 0,
  'ALTER TABLE websites ADD COLUMN use_cases TEXT NULL AFTER aliases',
  'SELECT 1'
);
PREPARE add_websites_use_cases_column_stmt FROM @add_websites_use_cases_column;
EXECUTE add_websites_use_cases_column_stmt;
DEALLOCATE PREPARE add_websites_use_cases_column_stmt;

SET @has_websites_enabled_column = (
  SELECT COUNT(*) FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'websites' AND column_name = 'enabled'
);
SET @add_websites_enabled_column = IF(
  @has_websites_enabled_column = 0,
  'ALTER TABLE websites ADD COLUMN enabled TINYINT(1) NOT NULL DEFAULT 1 AFTER use_cases',
  'SELECT 1'
);
PREPARE add_websites_enabled_column_stmt FROM @add_websites_enabled_column;
EXECUTE add_websites_enabled_column_stmt;
DEALLOCATE PREPARE add_websites_enabled_column_stmt;

SET @has_websites_name_index = (
  SELECT COUNT(*)
  FROM information_schema.statistics
  WHERE table_schema = DATABASE()
    AND table_name = 'websites'
    AND seq_in_index = 1
    AND column_name = 'name'
);
SET @add_websites_name_index = IF(
  @has_websites_name_index = 0,
  'ALTER TABLE websites ADD INDEX idx_websites_name (name)',
  'SELECT 1'
);
PREPARE add_websites_name_index_stmt FROM @add_websites_name_index;
EXECUTE add_websites_name_index_stmt;
DEALLOCATE PREPARE add_websites_name_index_stmt;

SET @has_websites_status_index = (
  SELECT COUNT(*)
  FROM information_schema.statistics
  WHERE table_schema = DATABASE()
    AND table_name = 'websites'
    AND seq_in_index = 1
    AND column_name = 'status'
);
SET @add_websites_status_index = IF(
  @has_websites_status_index = 0,
  'ALTER TABLE websites ADD INDEX idx_websites_status (status)',
  'SELECT 1'
);
PREPARE add_websites_status_index_stmt FROM @add_websites_status_index;
EXECUTE add_websites_status_index_stmt;
DEALLOCATE PREPARE add_websites_status_index_stmt;

SET @has_websites_enabled_index = (
  SELECT COUNT(*)
  FROM information_schema.statistics
  WHERE table_schema = DATABASE()
    AND table_name = 'websites'
    AND seq_in_index = 1
    AND column_name = 'enabled'
);
SET @has_websites_enabled_column = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = DATABASE()
    AND table_name = 'websites'
    AND column_name = 'enabled'
);
SET @add_websites_enabled_index = IF(
  @has_websites_enabled_column > 0 AND @has_websites_enabled_index = 0,
  'ALTER TABLE websites ADD INDEX idx_websites_enabled (enabled)',
  'SELECT 1'
);
PREPARE add_websites_enabled_index_stmt FROM @add_websites_enabled_index;
EXECUTE add_websites_enabled_index_stmt;
DEALLOCATE PREPARE add_websites_enabled_index_stmt;

-- Fill the academic-search gap with public, database-backed resources.
INSERT INTO websites (
  category_id, name, url, summary, description, is_free, need_login, region,
  quality_score, recommend_level, status, source, aliases, use_cases, enabled
)
SELECT 405, 'Google Scholar', 'https://scholar.google.com/',
       '学术论文、作者与引用关系检索服务。',
       'Google 提供的免费学术搜索引擎，可检索论文、作者、期刊与引用信息。',
       1, 0, 'international', 92, 9, 'approved', 'search_seed',
       '谷歌学术, scholar, 学术搜索, 文献检索', '论文写作, 文献调研, 引用检索', 1
WHERE NOT EXISTS (
  SELECT 1 FROM websites
  WHERE LOWER(TRIM(TRAILING '/' FROM url)) = 'https://scholar.google.com'
);
UPDATE websites
SET summary='学术论文、作者与引用关系检索服务。',
    description='Google 提供的免费学术搜索引擎，可检索论文、作者、期刊与引用信息。',
    aliases='谷歌学术, scholar, 学术搜索, 文献检索',
    use_cases='论文写作, 文献调研, 引用检索', enabled=1
WHERE LOWER(TRIM(TRAILING '/' FROM url)) = 'https://scholar.google.com';

INSERT INTO websites (
  category_id, name, url, summary, description, is_free, need_login, region,
  quality_score, recommend_level, status, source, aliases, use_cases, enabled
)
SELECT 405, 'Semantic Scholar', 'https://www.semanticscholar.org/',
       'AI 辅助的科学文献检索与论文发现平台。',
       'Allen Institute for AI 提供的学术搜索服务，支持论文、作者、引用和相关研究发现。',
       1, 0, 'international', 90, 9, 'approved', 'search_seed',
       '语义学术, academic search, 文献检索', '论文写作, 学术搜索, 相关论文发现', 1
WHERE NOT EXISTS (
  SELECT 1 FROM websites
  WHERE LOWER(TRIM(TRAILING '/' FROM url)) = 'https://www.semanticscholar.org'
);
UPDATE websites
SET summary='AI 辅助的科学文献检索与论文发现平台。',
    description='Allen Institute for AI 提供的学术搜索服务，支持论文、作者、引用和相关研究发现。',
    aliases='语义学术, academic search, 文献检索',
    use_cases='论文写作, 学术搜索, 相关论文发现', enabled=1
WHERE LOWER(TRIM(TRAILING '/' FROM url)) = 'https://www.semanticscholar.org';

INSERT INTO websites (
  category_id, name, url, summary, description, is_free, need_login, region,
  quality_score, recommend_level, status, source, aliases, use_cases, enabled
)
SELECT 405, 'Connected Papers', 'https://www.connectedpapers.com/',
       '通过可视化关系图发现相关学术论文。',
       '输入一篇种子论文后生成关联论文图谱，适合文献综述与研究脉络梳理。',
       1, 0, 'international', 88, 8, 'approved', 'search_seed',
       '论文图谱, related papers, 文献综述', '论文写作, 文献调研, 研究脉络', 1
WHERE NOT EXISTS (
  SELECT 1 FROM websites
  WHERE LOWER(TRIM(TRAILING '/' FROM url)) = 'https://www.connectedpapers.com'
);
UPDATE websites
SET summary='通过可视化关系图发现相关学术论文。',
    description='输入一篇种子论文后生成关联论文图谱，适合文献综述与研究脉络梳理。',
    aliases='论文图谱, related papers, 文献综述',
    use_cases='论文写作, 文献调研, 研究脉络', enabled=1
WHERE LOWER(TRIM(TRAILING '/' FROM url)) = 'https://www.connectedpapers.com';

INSERT INTO websites (
  category_id, name, url, summary, description, is_free, need_login, region,
  quality_score, recommend_level, status, source, aliases, use_cases, enabled
)
SELECT 405, 'Zotero', 'https://www.zotero.org/',
       '开源的文献收集、管理、引用与协作工具。',
       '支持浏览器采集、文献分类、PDF 管理和论文引用格式生成。',
       1, 0, 'international', 94, 9, 'approved', 'search_seed',
       '文献管理, 引用管理, bibliography, citation manager', '论文写作, 文献管理, 引用格式', 1
WHERE NOT EXISTS (
  SELECT 1 FROM websites
  WHERE LOWER(TRIM(TRAILING '/' FROM url)) = 'https://www.zotero.org'
);
UPDATE websites
SET summary='开源的文献收集、管理、引用与协作工具。',
    description='支持浏览器采集、文献分类、PDF 管理和论文引用格式生成。',
    aliases='文献管理, 引用管理, bibliography, citation manager',
    use_cases='论文写作, 文献管理, 引用格式', enabled=1
WHERE LOWER(TRIM(TRAILING '/' FROM url)) = 'https://www.zotero.org';

INSERT INTO websites (
  category_id, name, url, summary, description, is_free, need_login, region,
  quality_score, recommend_level, status, source, aliases, use_cases, enabled
)
SELECT 405, 'Overleaf', 'https://www.overleaf.com/',
       '在线 LaTeX 论文写作与多人协作平台。',
       '提供 LaTeX 在线编辑、期刊模板、实时协作和版本历史，适合科技论文排版。',
       1, 1, 'international', 92, 9, 'approved', 'search_seed',
       'latex, 在线论文编辑, 学术写作', '论文写作, LaTeX 排版, 多人协作', 1
WHERE NOT EXISTS (
  SELECT 1 FROM websites
  WHERE LOWER(TRIM(TRAILING '/' FROM url)) = 'https://www.overleaf.com'
);
UPDATE websites
SET summary='在线 LaTeX 论文写作与多人协作平台。',
    description='提供 LaTeX 在线编辑、期刊模板、实时协作和版本历史，适合科技论文排版。',
    aliases='latex, 在线论文编辑, 学术写作',
    use_cases='论文写作, LaTeX 排版, 多人协作', enabled=1
WHERE LOWER(TRIM(TRAILING '/' FROM url)) = 'https://www.overleaf.com';

INSERT INTO websites (
  category_id, name, url, summary, description, is_free, need_login, region,
  quality_score, recommend_level, status, source, aliases, use_cases, enabled
)
SELECT 405, 'ResearchGate', 'https://www.researchgate.net/',
       '面向研究人员的论文发现与学术交流社区。',
       '可检索研究成果、关注作者并参与学术问答，部分全文需由作者授权。',
       1, 1, 'international', 86, 8, 'approved', 'search_seed',
       '科研社区, 论文检索, researchers', '论文写作, 作者检索, 学术交流', 1
WHERE NOT EXISTS (
  SELECT 1 FROM websites
  WHERE LOWER(TRIM(TRAILING '/' FROM url)) = 'https://www.researchgate.net'
);
UPDATE websites
SET summary='面向研究人员的论文发现与学术交流社区。',
    description='可检索研究成果、关注作者并参与学术问答，部分全文需由作者授权。',
    aliases='科研社区, 论文检索, researchers',
    use_cases='论文写作, 作者检索, 学术交流', enabled=1
WHERE LOWER(TRIM(TRAILING '/' FROM url)) = 'https://www.researchgate.net';

INSERT INTO websites (
  category_id, name, url, summary, description, is_free, need_login, region,
  quality_score, recommend_level, status, source, aliases, use_cases, enabled
)
SELECT 5, 'Windsurf', 'https://windsurf.com/',
       '面向开发者的 AI 编程 IDE，原 Codeium。',
       '提供代码补全、对话式编程、代码库理解和多文件智能编辑能力。',
       1, 1, 'international', 90, 9, 'approved', 'search_seed',
       'Codeium, AI代码助手, AI编程', 'AI编程, 代码生成, 代码补全', 1
WHERE NOT EXISTS (
  SELECT 1 FROM websites
  WHERE LOWER(TRIM(TRAILING '/' FROM url)) = 'https://windsurf.com'
);
UPDATE websites
SET summary='面向开发者的 AI 编程 IDE，原 Codeium。',
    description='提供代码补全、对话式编程、代码库理解和多文件智能编辑能力。',
    aliases='Codeium, AI代码助手, AI编程',
    use_cases='AI编程, 代码生成, 代码补全', enabled=1
WHERE LOWER(TRIM(TRAILING '/' FROM url)) = 'https://windsurf.com';
