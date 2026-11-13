-- swingattr 初始结构（MySQL 8.0）
-- 运行时由 SQLAlchemy Base.metadata.create_all 建表；此文件是等价 DDL（DBA 预审索引 / 正式迁移用）。

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(160) NOT NULL, password_hash VARCHAR(255) NOT NULL,
  display_name VARCHAR(80) NOT NULL, role VARCHAR(20) NOT NULL,
  team VARCHAR(60), created_at DATETIME NOT NULL,
  UNIQUE KEY uq_users_email (email), KEY ix_users_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS metric_defs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(40) NOT NULL, name VARCHAR(60) NOT NULL, unit VARCHAR(8) NOT NULL,
  kind VARCHAR(20) NOT NULL, formula_text VARCHAR(200) NOT NULL,
  numerator VARCHAR(40) NULL, denominator VARCHAR(40) NULL,
  owner VARCHAR(60) NOT NULL, higher_is_better TINYINT(1) NOT NULL DEFAULT 1,
  description TEXT, sort_order INT NOT NULL DEFAULT 0, updated_at DATETIME NOT NULL,
  UNIQUE KEY uq_metric_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS dim_tree (
  id INT AUTO_INCREMENT PRIMARY KEY,
  dimension VARCHAR(20) NOT NULL, member_code VARCHAR(40) NOT NULL,
  member_name VARCHAR(60) NOT NULL, parent_code VARCHAR(40) NULL,
  level INT NOT NULL DEFAULT 1, sort_order INT NOT NULL DEFAULT 0, created_at DATETIME NOT NULL,
  UNIQUE KEY uq_dim_member (dimension, member_code), KEY ix_dim_dimension (dimension)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS fact_daily (
  id INT AUTO_INCREMENT PRIMARY KEY,
  stat_date DATE NOT NULL,
  city VARCHAR(40) NOT NULL, category VARCHAR(40) NOT NULL, channel VARCHAR(40) NOT NULL,
  store_code VARCHAR(40) NOT NULL, segment VARCHAR(40) NOT NULL,
  gmv BIGINT NOT NULL DEFAULT 0, orders BIGINT NOT NULL DEFAULT 0,
  new_members BIGINT NOT NULL DEFAULT 0, gross_profit BIGINT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL,
  KEY ix_fact_date (stat_date), KEY ix_fact_date_city (stat_date, city),
  KEY ix_fact_date_combo (stat_date, city, category, channel)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attribution_runs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  metric_code VARCHAR(40) NOT NULL, target_date DATE NOT NULL,
  baseline_kind VARCHAR(24) NOT NULL, baseline_date DATE NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'success', anomaly_level VARCHAR(16) NOT NULL DEFAULT 'normal',
  z_score DOUBLE NOT NULL DEFAULT 0, mad_value DOUBLE NOT NULL DEFAULT 0,
  value_now DOUBLE NOT NULL DEFAULT 0, value_base DOUBLE NOT NULL DEFAULT 0,
  delta_value DOUBLE NOT NULL DEFAULT 0, delta_pct DOUBLE NOT NULL DEFAULT 0,
  explained_pct DOUBLE NOT NULL DEFAULT 0, residual_value DOUBLE NOT NULL DEFAULT 0,
  top_n INT NOT NULL DEFAULT 8, dims JSON, components JSON, conclusion TEXT,
  created_by VARCHAR(120), seed_key VARCHAR(120) NULL, created_at DATETIME NOT NULL,
  UNIQUE KEY uq_run_seed_key (seed_key),
  KEY ix_run_metric (metric_code), KEY ix_run_target (target_date), KEY ix_run_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS swing_factors (
  id INT AUTO_INCREMENT PRIMARY KEY,
  run_id INT NOT NULL, kind VARCHAR(16) NOT NULL, dim_name VARCHAR(40) NOT NULL,
  member_code VARCHAR(80) NOT NULL, member_name VARCHAR(120) NOT NULL,
  path VARCHAR(160), component VARCHAR(20) NULL,
  value_now DOUBLE NOT NULL DEFAULT 0, value_base DOUBLE NOT NULL DEFAULT 0,
  delta_value DOUBLE NOT NULL DEFAULT 0, contribution_pp DOUBLE NOT NULL DEFAULT 0,
  contribution_pct DOUBLE NOT NULL DEFAULT 0, share_pct DOUBLE NOT NULL DEFAULT 0,
  rank INT NOT NULL DEFAULT 0, created_at DATETIME NOT NULL,
  KEY ix_factor_run (run_id), KEY ix_factor_kind (kind)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS report_issues (
  id INT AUTO_INCREMENT PRIMARY KEY,
  report_date DATE NOT NULL, title VARCHAR(200) NOT NULL, metric_code VARCHAR(40) NOT NULL,
  run_id INT NOT NULL, status VARCHAR(16) NOT NULL DEFAULT 'draft',
  conclusion TEXT, markdown LONGTEXT,
  issued_by VARCHAR(120), seed_key VARCHAR(120) NULL,
  created_at DATETIME NOT NULL, published_at DATETIME NULL,
  UNIQUE KEY uq_report_seed_key (seed_key),
  KEY ix_report_date (report_date), KEY ix_report_run (run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 投递任务：一次分发按渠道一路一条；(report_id, channel, target) 唯一保证幂等，
-- 重试只续 status != 'sent' 的任务，全部送达后日报才 published。
CREATE TABLE IF NOT EXISTS report_deliveries (
  id INT AUTO_INCREMENT PRIMARY KEY,
  report_id INT NOT NULL,
  channel VARCHAR(16) NOT NULL, target VARCHAR(120) NOT NULL DEFAULT '',
  status VARCHAR(16) NOT NULL DEFAULT 'pending',
  attempts INT NOT NULL DEFAULT 0, last_error VARCHAR(500) NULL,
  actor VARCHAR(120), seed_key VARCHAR(120) NULL,
  created_at DATETIME NOT NULL, last_attempt_at DATETIME NULL, delivered_at DATETIME NULL,
  UNIQUE KEY uq_delivery_task (report_id, channel, target),
  UNIQUE KEY uq_delivery_seed_key (seed_key),
  KEY ix_delivery_report (report_id),
  CONSTRAINT fk_delivery_report FOREIGN KEY (report_id) REFERENCES report_issues (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS audit_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  actor_email VARCHAR(160) NOT NULL, actor_role VARCHAR(20) NOT NULL,
  action VARCHAR(64) NOT NULL, entity VARCHAR(40) NOT NULL, entity_id VARCHAR(64) NULL,
  detail JSON, layer VARCHAR(16) NOT NULL DEFAULT 'domain', ip VARCHAR(64) NULL,
  seed_key VARCHAR(120) NULL, created_at DATETIME NOT NULL,
  UNIQUE KEY uq_audit_seed_key (seed_key),
  KEY ix_audit_actor (actor_email), KEY ix_audit_action (action), KEY ix_audit_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
