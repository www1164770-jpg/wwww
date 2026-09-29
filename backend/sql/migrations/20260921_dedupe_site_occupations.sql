-- Each website may be associated with a detailed career only once.
DELETE duplicate_relation
FROM site_occupations AS duplicate_relation
JOIN site_occupations AS retained_relation
  ON retained_relation.site_id = duplicate_relation.site_id
 AND retained_relation.occupation = duplicate_relation.occupation
 AND retained_relation.id < duplicate_relation.id;

ALTER TABLE site_occupations
  ADD UNIQUE KEY uniq_site_occupation (site_id, occupation);
