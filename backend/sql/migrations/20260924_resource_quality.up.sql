-- Additive schema only. Apply in an isolated test DB first. Data changes use the journaled CLI.

CREATE TABLE IF NOT EXISTS resource_field_claims (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	site_id INTEGER NOT NULL, 
	field VARCHAR(40) NOT NULL, 
	value TEXT, 
	source_kind VARCHAR(20) NOT NULL, 
	source_ref TEXT NOT NULL, 
	verified_at VARCHAR(40), 
	state VARCHAR(16) NOT NULL, 
	PRIMARY KEY (id)
)ENGINE=InnoDB CHARSET=utf8mb4

;

CREATE TABLE IF NOT EXISTS resource_identity_links (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	source_id INTEGER NOT NULL, 
	target_id INTEGER NOT NULL, 
	evidence TEXT NOT NULL, 
	state VARCHAR(16) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_resource_identity_source UNIQUE (source_id)
)ENGINE=InnoDB CHARSET=utf8mb4

;

CREATE TABLE IF NOT EXISTS resource_quality_changes (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	version VARCHAR(80) NOT NULL, 
	change_key VARCHAR(64) NOT NULL, 
	kind VARCHAR(32) NOT NULL, 
	payload TEXT NOT NULL, 
	state VARCHAR(16) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_resource_quality_change UNIQUE (version, change_key)
)ENGINE=InnoDB CHARSET=utf8mb4

;