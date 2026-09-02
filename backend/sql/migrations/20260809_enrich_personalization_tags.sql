-- Seed a stable, fine-grained tag vocabulary for questionnaire V2 signals.
-- Every relationship insert is guarded so this migration can be rerun safely.

INSERT INTO tags (name, type, created_at) VALUES
  ('developer', 'recommendation', CURRENT_TIMESTAMP),
  ('frontend', 'recommendation', CURRENT_TIMESTAMP),
  ('backend', 'recommendation', CURRENT_TIMESTAMP),
  ('api', 'recommendation', CURRENT_TIMESTAMP),
  ('api_debugging', 'recommendation', CURRENT_TIMESTAMP),
  ('database', 'recommendation', CURRENT_TIMESTAMP),
  ('devops', 'recommendation', CURRENT_TIMESTAMP),
  ('ai', 'recommendation', CURRENT_TIMESTAMP),
  ('ai_ml', 'recommendation', CURRENT_TIMESTAMP),
  ('ai_coding', 'recommendation', CURRENT_TIMESTAMP),
  ('code_generation', 'recommendation', CURRENT_TIMESTAMP),
  ('ui_ux', 'recommendation', CURRENT_TIMESTAMP),
  ('ui_generation', 'recommendation', CURRENT_TIMESTAMP),
  ('prototype', 'recommendation', CURRENT_TIMESTAMP),
  ('git_project_management', 'recommendation', CURRENT_TIMESTAMP),
  ('documentation', 'recommendation', CURRENT_TIMESTAMP),
  ('data', 'recommendation', CURRENT_TIMESTAMP),
  ('efficiency', 'recommendation', CURRENT_TIMESTAMP),
  ('free_value', 'recommendation', CURRENT_TIMESTAMP),
  ('professional', 'recommendation', CURRENT_TIMESTAMP)
ON DUPLICATE KEY UPDATE type=VALUES(type);

-- Development and direction tags.
INSERT INTO site_tags (site_id, tag_id)
SELECT w.id, t.id FROM websites w JOIN tags t ON t.name='developer'
WHERE LOWER(CONCAT_WS(' ', w.name, w.url, w.summary, w.description)) REGEXP 'github|gitlab|gitee|bitbucket|cursor|copilot|codeium|windsurf|postman|insomnia|swagger|hoppscotch|apifox|docker|kubernetes|redis|mysql|postgres|mongodb|python|django|flask|fastapi|node|vue|react|angular|svelte|next\\.js|nuxt|vercel|netlify|mdn|tailwind|bootstrap|webpack|vite'
  AND NOT EXISTS (SELECT 1 FROM site_tags st WHERE st.site_id=w.id AND st.tag_id=t.id);

INSERT INTO site_tags (site_id, tag_id)
SELECT w.id, t.id FROM websites w JOIN tags t ON t.name='frontend'
WHERE LOWER(CONCAT_WS(' ', w.name, w.url, w.summary, w.description)) REGEXP 'frontend|vue|react|angular|svelte|next\\.js|nuxt|vercel|netlify|codepen|mdn|tailwind|bootstrap|css|webpack|vite|storybook|figma|framer|v0|lovable|bolt'
  AND NOT EXISTS (SELECT 1 FROM site_tags st WHERE st.site_id=w.id AND st.tag_id=t.id);

INSERT INTO site_tags (site_id, tag_id)
SELECT w.id, t.id FROM websites w JOIN tags t ON t.name='backend'
WHERE LOWER(CONCAT_WS(' ', w.name, w.url, w.summary, w.description)) REGEXP 'backend|postman|insomnia|swagger|hoppscotch|apifox|fastapi|flask|django|express|node|redis|mysql|postgres|mongodb|server|docker|kubernetes'
  AND NOT EXISTS (SELECT 1 FROM site_tags st WHERE st.site_id=w.id AND st.tag_id=t.id);

INSERT INTO site_tags (site_id, tag_id)
SELECT w.id, t.id FROM websites w JOIN tags t ON t.name='api'
WHERE LOWER(w.name) REGEXP 'postman|insomnia|swagger|hoppscotch|apifox|bruno'
  AND NOT EXISTS (SELECT 1 FROM site_tags st WHERE st.site_id=w.id AND st.tag_id=t.id);

INSERT INTO site_tags (site_id, tag_id)
SELECT w.id, t.id FROM websites w JOIN tags t ON t.name='api_debugging'
WHERE LOWER(CONCAT_WS(' ', w.name, w.url, w.summary, w.description)) REGEXP 'postman|insomnia|swagger|hoppscotch|apifox|bruno|api debug|api test|http client'
  AND NOT EXISTS (SELECT 1 FROM site_tags st WHERE st.site_id=w.id AND st.tag_id=t.id);

INSERT INTO site_tags (site_id, tag_id)
SELECT w.id, t.id FROM websites w JOIN tags t ON t.name='database'
WHERE LOWER(CONCAT_WS(' ', w.name, w.url, w.summary, w.description)) REGEXP 'mysql|postgres|mongodb|redis|sqlite|supabase|database|db'
  AND NOT EXISTS (SELECT 1 FROM site_tags st WHERE st.site_id=w.id AND st.tag_id=t.id);

INSERT INTO site_tags (site_id, tag_id)
SELECT w.id, t.id FROM websites w JOIN tags t ON t.name='devops'
WHERE LOWER(CONCAT_WS(' ', w.name, w.url, w.summary, w.description)) REGEXP 'docker|kubernetes|jenkins|grafana|prometheus|vercel|netlify|cloudflare|deployment|devops|monitoring'
  AND NOT EXISTS (SELECT 1 FROM site_tags st WHERE st.site_id=w.id AND st.tag_id=t.id);

-- AI development and code-generation tags.
INSERT INTO site_tags (site_id, tag_id)
SELECT w.id, t.id FROM websites w JOIN tags t ON t.name='ai'
WHERE LOWER(CONCAT_WS(' ', w.name, w.url, w.summary, w.description)) REGEXP 'chatgpt|claude|gemini|cursor|copilot|codeium|windsurf|hugging ?face|kaggle|jupyter|tensorflow|pytorch|midjourney|stable diffusion|ai '
  AND NOT EXISTS (SELECT 1 FROM site_tags st WHERE st.site_id=w.id AND st.tag_id=t.id);

INSERT INTO site_tags (site_id, tag_id)
SELECT w.id, t.id FROM websites w JOIN tags t ON t.name='ai_ml'
WHERE LOWER(CONCAT_WS(' ', w.name, w.url, w.summary, w.description)) REGEXP 'hugging ?face|kaggle|jupyter|colab|tensorflow|pytorch|machine learning|deep learning|llm|large language|model'
  AND NOT EXISTS (SELECT 1 FROM site_tags st WHERE st.site_id=w.id AND st.tag_id=t.id);

INSERT INTO site_tags (site_id, tag_id)
SELECT w.id, t.id FROM websites w JOIN tags t ON t.name='ai_coding'
WHERE LOWER(CONCAT_WS(' ', w.name, w.url, w.summary, w.description)) REGEXP 'cursor|copilot|codeium|windsurf|tabnine|claude code|replit|bolt|v0'
  AND NOT EXISTS (SELECT 1 FROM site_tags st WHERE st.site_id=w.id AND st.tag_id=t.id);

INSERT INTO site_tags (site_id, tag_id)
SELECT w.id, t.id FROM websites w JOIN tags t ON t.name='code_generation'
WHERE LOWER(CONCAT_WS(' ', w.name, w.url, w.summary, w.description)) REGEXP 'cursor|copilot|codeium|windsurf|tabnine|claude code|replit|bolt|v0|chatgpt'
  AND NOT EXISTS (SELECT 1 FROM site_tags st WHERE st.site_id=w.id AND st.tag_id=t.id);

-- Design, documentation, collaboration, and analytics tags.
INSERT INTO site_tags (site_id, tag_id)
SELECT w.id, t.id FROM websites w JOIN tags t ON t.name='ui_ux'
WHERE LOWER(CONCAT_WS(' ', w.name, w.url, w.summary, w.description)) REGEXP 'figma|sketch|adobe xd|axure|mockplus|protopie|framer|ui/ux|interface design'
  AND NOT EXISTS (SELECT 1 FROM site_tags st WHERE st.site_id=w.id AND st.tag_id=t.id);

INSERT INTO site_tags (site_id, tag_id)
SELECT w.id, t.id FROM websites w JOIN tags t ON t.name='ui_generation'
WHERE LOWER(CONCAT_WS(' ', w.name, w.url, w.summary, w.description)) REGEXP 'figma|framer|v0|lovable|bolt|uizard|galileo|ui generator'
  AND NOT EXISTS (SELECT 1 FROM site_tags st WHERE st.site_id=w.id AND st.tag_id=t.id);

INSERT INTO site_tags (site_id, tag_id)
SELECT w.id, t.id FROM websites w JOIN tags t ON t.name='prototype'
WHERE LOWER(CONCAT_WS(' ', w.name, w.url, w.summary, w.description)) REGEXP 'figma|axure|mockplus|protopie|framer|prototype|wireframe'
  AND NOT EXISTS (SELECT 1 FROM site_tags st WHERE st.site_id=w.id AND st.tag_id=t.id);

INSERT INTO site_tags (site_id, tag_id)
SELECT w.id, t.id FROM websites w JOIN tags t ON t.name='git_project_management'
WHERE LOWER(CONCAT_WS(' ', w.name, w.url, w.summary, w.description)) REGEXP 'github|gitlab|gitee|bitbucket|git |jira|linear|trello|notion|project management'
  AND NOT EXISTS (SELECT 1 FROM site_tags st WHERE st.site_id=w.id AND st.tag_id=t.id);

INSERT INTO site_tags (site_id, tag_id)
SELECT w.id, t.id FROM websites w JOIN tags t ON t.name='documentation'
WHERE LOWER(CONCAT_WS(' ', w.name, w.url, w.summary, w.description)) REGEXP 'mdn|documentation|docs|swagger|readme|developer guide'
  AND NOT EXISTS (SELECT 1 FROM site_tags st WHERE st.site_id=w.id AND st.tag_id=t.id);

INSERT INTO site_tags (site_id, tag_id)
SELECT w.id, t.id FROM websites w JOIN tags t ON t.name='data'
WHERE LOWER(CONCAT_WS(' ', w.name, w.url, w.summary, w.description)) REGEXP 'kaggle|jupyter|colab|tableau|power bi|metabase|superset|echarts|tensorflow|pytorch|data analysis|analytics|visualization'
  AND NOT EXISTS (SELECT 1 FROM site_tags st WHERE st.site_id=w.id AND st.tag_id=t.id);

INSERT INTO site_tags (site_id, tag_id)
SELECT w.id, t.id FROM websites w JOIN tags t ON t.name='efficiency'
WHERE LOWER(CONCAT_WS(' ', w.name, w.url, w.summary, w.description)) REGEXP 'notion|feishu|slack|trello|asana|linear|todoist|office|automation|productivity'
  AND NOT EXISTS (SELECT 1 FROM site_tags st WHERE st.site_id=w.id AND st.tag_id=t.id);

-- Priority tags are intentionally broad and complement, rather than replace,
-- the direction and primary-need signals above.
INSERT INTO site_tags (site_id, tag_id)
SELECT w.id, t.id FROM websites w JOIN tags t ON t.name='free_value'
WHERE COALESCE(w.is_free, 0)=1
  AND NOT EXISTS (SELECT 1 FROM site_tags st WHERE st.site_id=w.id AND st.tag_id=t.id);

INSERT INTO site_tags (site_id, tag_id)
SELECT w.id, t.id FROM websites w JOIN tags t ON t.name='professional'
WHERE (COALESCE(w.quality_score, 0)>=75 OR COALESCE(w.recommend_level, 0)>=8)
  AND NOT EXISTS (SELECT 1 FROM site_tags st WHERE st.site_id=w.id AND st.tag_id=t.id);
