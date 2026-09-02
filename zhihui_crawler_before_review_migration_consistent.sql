-- MySQL dump 10.13  Distrib 9.7.1, for Win64 (x86_64)
--
-- Host: localhost    Database: zhihui_crawler
-- ------------------------------------------------------
-- Server version	9.7.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
SET @MYSQLDUMP_TEMP_LOG_BIN = @@SESSION.SQL_LOG_BIN;
SET @@SESSION.SQL_LOG_BIN= 0;

--
-- GTID state at the beginning of the backup 
--

SET @@GLOBAL.GTID_PURGED=/*!80000 '+'*/ '108dd2b1-8833-11f1-b1b3-b082e26f1874:1-2231';

--
-- Table structure for table `analysis_results`
--

DROP TABLE IF EXISTS `analysis_results`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `analysis_results` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `analysis_uid` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `fetch_result_id` bigint NOT NULL,
  `candidate_uid` varchar(72) COLLATE utf8mb4_unicode_ci NOT NULL,
  `analysis_version` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_hash` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `original_language` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `detected_language` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL,
  `language_confidence` double NOT NULL,
  `category` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `category_confidence` double NOT NULL,
  `quality_score` double NOT NULL,
  `title_original` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `summary_zh` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `summary_method` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `tags_json` json NOT NULL,
  `rule_version` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `model_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `model_status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `model_error_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `evidence_hashes_json` json NOT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_analysis_results_uid` (`analysis_uid`),
  UNIQUE KEY `uq_analysis_results_fetch_version` (`fetch_result_id`,`analysis_version`),
  KEY `ix_analysis_results_candidate_created` (`candidate_uid`,`created_at`),
  KEY `ix_analysis_results_category_confidence` (`category`,`category_confidence`),
  CONSTRAINT `fk_analysis_results_fetch` FOREIGN KEY (`fetch_result_id`) REFERENCES `fetch_results` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `analysis_results`
--

LOCK TABLES `analysis_results` WRITE;
/*!40000 ALTER TABLE `analysis_results` DISABLE KEYS */;
/*!40000 ALTER TABLE `analysis_results` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `crawl_runs`
--

DROP TABLE IF EXISTS `crawl_runs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `crawl_runs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `run_uid` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `scheduled_for` datetime(6) NOT NULL,
  `started_at` datetime(6) DEFAULT NULL,
  `stop_requested_at` datetime(6) DEFAULT NULL,
  `finished_at` datetime(6) DEFAULT NULL,
  `target_count` int NOT NULL DEFAULT '0',
  `leased_count` int NOT NULL DEFAULT '0',
  `completed_count` int NOT NULL DEFAULT '0',
  `failed_count` int NOT NULL DEFAULT '0',
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_crawl_runs_run_uid` (`run_uid`),
  KEY `ix_crawl_runs_status_scheduled` (`status`,`scheduled_for`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `crawl_runs`
--

LOCK TABLES `crawl_runs` WRITE;
/*!40000 ALTER TABLE `crawl_runs` DISABLE KEYS */;
/*!40000 ALTER TABLE `crawl_runs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `crawl_tasks`
--

DROP TABLE IF EXISTS `crawl_tasks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `crawl_tasks` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `task_uid` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `run_id` bigint DEFAULT NULL,
  `task_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `target` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `target_hash` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `dedupe_key` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `active_dedupe_key` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `payload_json` json DEFAULT NULL,
  `priority` int NOT NULL DEFAULT '100',
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `attempt_count` int NOT NULL DEFAULT '0',
  `max_attempts` int NOT NULL DEFAULT '3',
  `available_at` datetime(6) NOT NULL,
  `leased_at` datetime(6) DEFAULT NULL,
  `leased_until` datetime(6) DEFAULT NULL,
  `worker_id` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_error_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_error_message` varchar(1000) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `completed_at` datetime(6) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_crawl_tasks_task_uid` (`task_uid`),
  UNIQUE KEY `uq_crawl_tasks_active_dedupe` (`task_type`,`active_dedupe_key`),
  KEY `ix_crawl_tasks_lease_candidates` (`status`,`available_at`,`priority`,`created_at`),
  KEY `ix_crawl_tasks_expired_leases` (`status`,`leased_until`),
  KEY `ix_crawl_tasks_run_status` (`run_id`,`status`),
  CONSTRAINT `fk_crawl_tasks_run` FOREIGN KEY (`run_id`) REFERENCES `crawl_runs` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `crawl_tasks`
--

LOCK TABLES `crawl_tasks` WRITE;
/*!40000 ALTER TABLE `crawl_tasks` DISABLE KEYS */;
/*!40000 ALTER TABLE `crawl_tasks` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `crawler_schema_migrations`
--

DROP TABLE IF EXISTS `crawler_schema_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `crawler_schema_migrations` (
  `version` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `applied_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`version`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `crawler_schema_migrations`
--

LOCK TABLES `crawler_schema_migrations` WRITE;
/*!40000 ALTER TABLE `crawler_schema_migrations` DISABLE KEYS */;
INSERT INTO `crawler_schema_migrations` VALUES ('0001_initial','2026-08-01 13:42:21.553712'),('0002_static_fetch','2026-08-01 15:55:26.208417'),('0003_analysis_risk_assets','2026-08-01 17:09:28.293013');
/*!40000 ALTER TABLE `crawler_schema_migrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `crawler_settings`
--

DROP TABLE IF EXISTS `crawler_settings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `crawler_settings` (
  `setting_key` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `setting_value` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `value_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `updated_by` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`setting_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `crawler_settings`
--

LOCK TABLES `crawler_settings` WRITE;
/*!40000 ALTER TABLE `crawler_settings` DISABLE KEYS */;
/*!40000 ALTER TABLE `crawler_settings` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `discovered_links`
--

DROP TABLE IF EXISTS `discovered_links`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `discovered_links` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `link_uid` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `source_result_id` bigint NOT NULL,
  `source_url` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `discovered_url` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `normalized_url` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `normalized_fingerprint` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `relation_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `discovery_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `depth` int NOT NULL,
  `is_safe` tinyint(1) NOT NULL,
  `is_same_origin` tinyint(1) NOT NULL,
  `enqueue_status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `metadata_json` json DEFAULT NULL,
  `discovered_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_discovered_links_link_uid` (`link_uid`),
  UNIQUE KEY `uq_discovered_links_source_url` (`source_result_id`,`normalized_fingerprint`),
  KEY `ix_discovered_links_normalized` (`normalized_fingerprint`),
  KEY `ix_discovered_links_enqueue` (`enqueue_status`,`discovered_at`),
  CONSTRAINT `fk_discovered_links_result` FOREIGN KEY (`source_result_id`) REFERENCES `fetch_results` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `discovered_links`
--

LOCK TABLES `discovered_links` WRITE;
/*!40000 ALTER TABLE `discovered_links` DISABLE KEYS */;
/*!40000 ALTER TABLE `discovered_links` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `fetch_results`
--

DROP TABLE IF EXISTS `fetch_results`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `fetch_results` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `result_uid` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `task_id` bigint DEFAULT NULL,
  `requested_url` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `normalized_url` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `normalized_fingerprint` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `final_url` text COLLATE utf8mb4_unicode_ci,
  `normalized_final_url` text COLLATE utf8mb4_unicode_ci,
  `normalized_final_fingerprint` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `http_status` int DEFAULT NULL,
  `content_type` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `charset` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bytes_read` bigint DEFAULT NULL,
  `redirect_count` int NOT NULL DEFAULT '0',
  `redirect_chain` json DEFAULT NULL,
  `title` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meta_description` text COLLATE utf8mb4_unicode_ci,
  `canonical_url` text COLLATE utf8mb4_unicode_ci,
  `og_title` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `og_description` text COLLATE utf8mb4_unicode_ci,
  `og_image_url` text COLLATE utf8mb4_unicode_ci,
  `twitter_title` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `twitter_description` text COLLATE utf8mb4_unicode_ci,
  `twitter_image_url` text COLLATE utf8mb4_unicode_ci,
  `favicon_url` text COLLATE utf8mb4_unicode_ci,
  `apple_touch_icon_url` text COLLATE utf8mb4_unicode_ci,
  `language` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `heading` varchar(1000) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `text_excerpt` text COLLATE utf8mb4_unicode_ci,
  `content_hash` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `document_metadata_json` json DEFAULT NULL,
  `robots_allowed` tinyint(1) DEFAULT NULL,
  `robots_status` int DEFAULT NULL,
  `etag` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_modified` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fetched_at` datetime(6) NOT NULL,
  `elapsed_ms` int DEFAULT NULL,
  `error_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `error_message_sanitized` varchar(1000) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_fetch_results_result_uid` (`result_uid`),
  UNIQUE KEY `uq_fetch_results_task_id` (`task_id`),
  UNIQUE KEY `uq_fetch_results_final_content` (`normalized_final_fingerprint`,`content_hash`),
  KEY `ix_fetch_results_status_fetched` (`status`,`fetched_at`),
  KEY `ix_fetch_results_final_fetched` (`normalized_final_fingerprint`,`fetched_at`),
  CONSTRAINT `fk_fetch_results_task` FOREIGN KEY (`task_id`) REFERENCES `crawl_tasks` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `fetch_results`
--

LOCK TABLES `fetch_results` WRITE;
/*!40000 ALTER TABLE `fetch_results` DISABLE KEYS */;
/*!40000 ALTER TABLE `fetch_results` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `icon_assets`
--

DROP TABLE IF EXISTS `icon_assets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `icon_assets` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `asset_uid` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `fetch_result_id` bigint NOT NULL,
  `source_url` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_hash` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `mime_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `width` int NOT NULL,
  `height` int NOT NULL,
  `byte_size` int NOT NULL,
  `relative_path` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `fetched_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_icon_assets_uid` (`asset_uid`),
  UNIQUE KEY `uq_icon_assets_content_hash` (`content_hash`),
  KEY `ix_icon_assets_fetch_result` (`fetch_result_id`,`fetched_at`),
  CONSTRAINT `fk_icon_assets_fetch` FOREIGN KEY (`fetch_result_id`) REFERENCES `fetch_results` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `icon_assets`
--

LOCK TABLES `icon_assets` WRITE;
/*!40000 ALTER TABLE `icon_assets` DISABLE KEYS */;
/*!40000 ALTER TABLE `icon_assets` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `outbox_events`
--

DROP TABLE IF EXISTS `outbox_events`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `outbox_events` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `event_uid` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `aggregate_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `aggregate_uid` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `event_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `payload_json` json NOT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `attempt_count` int NOT NULL DEFAULT '0',
  `max_attempts` int NOT NULL DEFAULT '3',
  `available_at` datetime(6) NOT NULL,
  `leased_at` datetime(6) DEFAULT NULL,
  `leased_until` datetime(6) DEFAULT NULL,
  `worker_id` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_error` varchar(1000) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `processed_at` datetime(6) DEFAULT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_outbox_events_event_uid` (`event_uid`),
  KEY `ix_outbox_events_lease_candidates` (`status`,`available_at`,`created_at`),
  KEY `ix_outbox_events_expired_leases` (`status`,`leased_until`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `outbox_events`
--

LOCK TABLES `outbox_events` WRITE;
/*!40000 ALTER TABLE `outbox_events` DISABLE KEYS */;
/*!40000 ALTER TABLE `outbox_events` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `risk_decisions`
--

DROP TABLE IF EXISTS `risk_decisions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `risk_decisions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `decision_uid` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `analysis_result_id` bigint NOT NULL,
  `decision_version` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `risk_score` double NOT NULL,
  `confidence` double NOT NULL,
  `hard_reject` tinyint(1) NOT NULL,
  `rule_codes_json` json NOT NULL,
  `evidence_hashes_json` json NOT NULL,
  `created_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_risk_decisions_uid` (`decision_uid`),
  UNIQUE KEY `uq_risk_decisions_analysis_version` (`analysis_result_id`,`decision_version`),
  KEY `ix_risk_decisions_status_created` (`status`,`created_at`),
  CONSTRAINT `fk_risk_decisions_analysis` FOREIGN KEY (`analysis_result_id`) REFERENCES `analysis_results` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `risk_decisions`
--

LOCK TABLES `risk_decisions` WRITE;
/*!40000 ALTER TABLE `risk_decisions` DISABLE KEYS */;
/*!40000 ALTER TABLE `risk_decisions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `worker_heartbeats`
--

DROP TABLE IF EXISTS `worker_heartbeats`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `worker_heartbeats` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `worker_id` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `worker_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `process_id` int NOT NULL,
  `hostname` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `current_task_uid` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `started_at` datetime(6) NOT NULL,
  `last_seen_at` datetime(6) NOT NULL,
  `metadata_json` json DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_worker_heartbeats_worker_id` (`worker_id`),
  KEY `ix_worker_heartbeats_status_seen` (`status`,`last_seen_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `worker_heartbeats`
--

LOCK TABLES `worker_heartbeats` WRITE;
/*!40000 ALTER TABLE `worker_heartbeats` DISABLE KEYS */;
/*!40000 ALTER TABLE `worker_heartbeats` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping events for database 'zhihui_crawler'
--

--
-- Dumping routines for database 'zhihui_crawler'
--
SET @@SESSION.SQL_LOG_BIN = @MYSQLDUMP_TEMP_LOG_BIN;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-08-05 23:42:53
