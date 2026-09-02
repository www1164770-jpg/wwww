-- Correct early API tagging rules that treated every https URL as an API hit.
-- Only remove the broad generated API association; retain explicit API tools.

DELETE st
FROM site_tags st
JOIN tags t ON t.id=st.tag_id
JOIN websites w ON w.id=st.site_id
WHERE t.name='api'
  AND LOWER(w.name) NOT REGEXP 'postman|insomnia|swagger|hoppscotch|apifox|bruno';
